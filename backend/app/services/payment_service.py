import logging
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core import clock
from app.core.pricing import tuition_fee
from app.core.runtime_config import get_institution_config
from app.models.cash_register import CashRegister
from app.models.enrollment import Enrollment
from app.models.payment import Payment
from app.models.receipt import Receipt
from app.repositories.enrollment_repository import EnrollmentRepository
from app.repositories.payment_repository import PaymentRepository
from app.services import audit_service
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)

CASH = "Efectivo"
# Estados que el sistema recalcula solo según los pagos y las fechas. Una
# matrícula ANULADA ya no cambia.
TRACKED_STATUSES = ("ACTIVA", "PENDIENTE", "FINALIZADA")
ACTIVE_STATUSES = ("ACTIVA", "PENDIENTE")


@dataclass
class InstallmentStatus:
    """Situación de las colegiaturas de una matrícula."""

    total: int                 # cuotas que tiene el diplomado
    paid: int                  # cuotas cobradas (no anuladas)
    next_due: Optional[date]   # vencimiento de la próxima cuota; None si ya pagó todas
    overdue: int               # cuotas vencidas sin pagar

    @property
    def remaining(self) -> int:
        return self.total - self.paid


class PaymentService:

    @staticmethod
    def cycle_days(db: Session) -> int:
        return int(get_institution_config(db).payment_cycle_days)

    @staticmethod
    def late_fee(db: Session) -> Decimal:
        return Decimal(str(get_institution_config(db).late_fee))

    @staticmethod
    def installments_total(enrollment: Enrollment, cycle_days: int) -> int:
        """Cuotas de colegiatura del diplomado: una cada `cycle_days` días
        desde el inicio de clases mientras dure el programa. Ej.: 6 meses
        (182 días) con ciclo de 28 días son 7 cuotas (días 0, 28, ..., 168).
        Antes no había tope y se podía cobrar un diplomado para siempre."""
        days = (enrollment.end_date - enrollment.start_date).days
        return max(1, -(-days // cycle_days))

    @staticmethod
    def due_date(start_date: date, number: int, cycle_days: int) -> date:
        """Vencimiento de la cuota `number` (desde 0). PDF, funcionamiento
        básico: inicio 01/08/2026 → cuota 0 el 01/08/2026, cuota 1 el
        29/08/2026, y así sucesivamente cada 28 días."""
        return start_date + timedelta(days=number * cycle_days)

    @staticmethod
    def installment_status(db: Session, enrollments: list[Enrollment]) -> dict[int, InstallmentStatus]:
        """Situación de cada matrícula con una sola consulta (no una por fila).

        La cuota número k (desde 0) vence el día inicio + k × ciclo (PDF:
        inicio 01/08/2026 → 01/08, 29/08, 26/09...). La próxima por cobrar es
        la siguiente a las ya cobradas: si se anula un cobro, esa cuota
        vuelve a quedar pendiente."""
        ids = [enrollment.id for enrollment in enrollments]
        if not ids:
            return {}
        paid_counts = dict(
            db.query(Payment.enrollment_id, func.count(Payment.id))
            .filter(
                Payment.enrollment_id.in_(ids),
                Payment.kind == "COLEGIATURA",
                Payment.status == "PAGADO",
            )
            .group_by(Payment.enrollment_id)
            .all()
        )
        cycle = PaymentService.cycle_days(db)
        today = clock.today()
        result = {}
        for enrollment in enrollments:
            total = PaymentService.installments_total(enrollment, cycle)
            paid = min(paid_counts.get(enrollment.id, 0), total)
            next_due = None if paid >= total else PaymentService.due_date(enrollment.start_date, paid, cycle)
            overdue = 0
            if next_due is not None and next_due < today:
                overdue = min(total - paid, (today - next_due).days // cycle + 1)
            result[enrollment.id] = InstallmentStatus(total, paid, next_due, overdue)
        return result

    @staticmethod
    def refresh_enrollment_statuses(
        db: Session, enrollments: list[Enrollment] | None = None
    ) -> dict[int, InstallmentStatus]:
        """PDF: el alumno pasa a "PENDIENTE" si se superan los 28 días sin
        registrar un nuevo cobro (su próxima cuota ya venció) y vuelve a
        "ACTIVA" al ponerse al día. Además queda "FINALIZADA" cuando pagó
        todas sus cuotas y ya terminó el diplomado."""
        if enrollments is None:
            enrollments = db.query(Enrollment).filter(Enrollment.status.in_(TRACKED_STATUSES)).all()
        statuses = PaymentService.installment_status(db, enrollments)
        today = clock.today()
        changed = False
        for enrollment in enrollments:
            if enrollment.status not in TRACKED_STATUSES:
                continue
            info = statuses[enrollment.id]
            if info.next_due is not None and info.next_due < today:
                expected = "PENDIENTE"
            elif info.next_due is None and today > enrollment.end_date:
                expected = "FINALIZADA"
            else:
                expected = "ACTIVA"
            if enrollment.status != expected:
                enrollment.status = expected
                changed = True
        if changed:
            db.commit()
        return statuses

    @staticmethod
    def next_due_dates(db: Session, enrollments: list[Enrollment]) -> dict[int, Optional[date]]:
        return {
            enrollment_id: info.next_due
            for enrollment_id, info in PaymentService.refresh_enrollment_statuses(db, enrollments).items()
        }

    @staticmethod
    def _cash_and_change(payment_type: str, cash_received: Optional[Decimal], total: Decimal) -> tuple[Decimal, Decimal]:
        """PDF punto 4: con "Efectivo:" el sistema calcula el "Cambio:". Con
        tarjeta o transferencia se cobra el monto exacto y no hay cambio."""
        if payment_type != CASH:
            return total, Decimal("0.00")
        cash = Decimal(str(cash_received if cash_received is not None else total))
        if cash < total:
            raise HTTPException(status_code=400, detail=f"El efectivo debe ser de al menos ${total:.2f}")
        return cash, cash - total

    @staticmethod
    def collect(db: Session, data, user, register: CashRegister) -> dict:
        # Bloquea la fila de la matrícula hasta el commit: si dos cobros
        # llegan casi al mismo tiempo para la misma matrícula (dos cajeros,
        # o un doble clic que dispara dos peticiones), el segundo espera a
        # que el primero termine en vez de cobrar dos veces la misma cuota.
        locked = db.query(Enrollment.id).filter(Enrollment.id == data.enrollment_id).with_for_update().first()
        if not locked:
            raise HTTPException(status_code=404, detail="La matrícula no existe")

        enrollment = EnrollmentRepository.get_by_id(db, data.enrollment_id)
        if enrollment.status == "ANULADA":
            raise HTTPException(status_code=400, detail="La matrícula está anulada; no se le puede cobrar")
        info = PaymentService.installment_status(db, [enrollment])[enrollment.id]
        if info.remaining <= 0:
            raise HTTPException(
                status_code=400,
                detail=f"El estudiante ya pagó las {info.total} cuotas de su diplomado",
            )
        if not 1 <= data.months <= info.remaining:
            raise HTTPException(
                status_code=400,
                detail=f"Puedes cobrar entre 1 y {min(12, info.remaining)} cuota(s): le quedan {info.remaining}",
            )

        today = clock.today()
        cycle = PaymentService.cycle_days(db)
        # PDF (mejora recomendada): opción de aplicar el recargo si se pasó
        # de la fecha. Un solo recargo por cobro, no uno por cuota atrasada.
        surcharge = (
            PaymentService.late_fee(db)
            if info.next_due < today and data.apply_late_fee
            else Decimal("0.00")
        )
        monthly_amount = tuition_fee(db, enrollment.tuition_plan)
        amount = monthly_amount * data.months
        total = amount + surcharge
        cash, change = PaymentService._cash_and_change(data.payment_type, data.cash_received, total)

        receipt = Receipt(
            enrollment_id=enrollment.id,
            cashier_id=user.id,
            cash_register_id=register.id,
            kind="COLEGIATURA",
            payment_type=data.payment_type,
            total=total,
            cash_received=cash,
            change=change,
            status="EMITIDO",
        )
        db.add(receipt)
        db.flush()

        # Cuotas PENDIENTE que quedaron de versiones anteriores del sistema:
        # se cobran esas primero en vez de crear otras con la misma fecha.
        legacy_pending = (
            db.query(Payment)
            .filter(Payment.enrollment_id == enrollment.id, Payment.status == "PENDIENTE")
            .order_by(Payment.due_date.asc())
            .all()
        )
        created = []
        for index in range(data.months):
            number = info.paid + index  # cuota número `number` (desde 0)
            payment = legacy_pending[index] if index < len(legacy_pending) else Payment(
                enrollment_id=enrollment.id, kind="COLEGIATURA"
            )
            fee = surcharge if index == 0 else Decimal("0.00")
            payment.due_date = PaymentService.due_date(enrollment.start_date, number, cycle)
            payment.receipt_id = receipt.id
            payment.cash_register_id = register.id
            payment.cashier_id = user.id
            payment.payment_date = today
            payment.amount = monthly_amount
            payment.surcharge = fee
            payment.total = monthly_amount + fee
            payment.payment_type = data.payment_type
            payment.status = "PAGADO"
            payment.cash_received = cash if index == 0 else None
            payment.change = change if index == 0 else None
            payment.observations = data.observations or f"Cuota {number + 1} de {info.total}"
            db.add(payment)
            created.append(payment)

        audit_service.record(
            db, user, "COBRO", "receipt", receipt.id,
            f"{receipt.number} · {enrollment.student.full_name} · {data.months} cuota(s) · "
            f"${total:.2f} ({data.payment_type})" + (f" · recargo ${surcharge:.2f}" if surcharge else ""),
        )
        db.commit()

        # Puede seguir PENDIENTE si debía varias cuotas y solo pagó una.
        new_info = PaymentService.refresh_enrollment_statuses(db, [enrollment])[enrollment.id]
        db.refresh(receipt)
        EmailService.send_receipt(receipt, next_payment_date=new_info.next_due)
        return {
            "receipt_id": receipt.id,
            "receipt_number": receipt.number,
            "payment_ids": [payment.id for payment in created],
            "enrollment_id": enrollment.id,
            "months_paid": data.months,
            "amount": amount,
            "surcharge": surcharge,
            "total": total,
            "payment_type": data.payment_type,
            "cash_received": cash,
            "change": change,
            "first_due_date": info.next_due,
            "next_payment_date": new_info.next_due,
            "installments_paid": new_info.paid,
            "installments_total": new_info.total,
            "late": surcharge > 0,
        }

    @staticmethod
    def next_payment_info(db: Session, enrollment_id: int) -> dict:
        enrollment = EnrollmentRepository.get_by_id(db, enrollment_id)
        if not enrollment:
            raise HTTPException(status_code=404, detail="La matrícula no existe")
        info = PaymentService.refresh_enrollment_statuses(db, [enrollment])[enrollment.id]
        today = clock.today()
        is_overdue = info.next_due is not None and info.next_due < today
        monthly_amount = tuition_fee(db, enrollment.tuition_plan)
        late_fee = PaymentService.late_fee(db) if is_overdue else Decimal("0.00")
        return {
            "enrollment_id": enrollment_id,
            "student_name": enrollment.student.full_name,
            "diploma_name": enrollment.diploma.name,
            "tuition_plan": enrollment.tuition_plan,
            "due_date": info.next_due,
            "days_until_due": (info.next_due - today).days if info.next_due else None,
            "monthly_amount": monthly_amount,
            "automatic_surcharge": late_fee,
            "is_overdue": is_overdue,
            "status": enrollment.status,
            "installments_total": info.total,
            "installments_paid": info.paid,
            "installments_remaining": info.remaining,
            "overdue_installments": info.overdue,
            "amount_overdue": monthly_amount * info.overdue + late_fee,
        }

    @staticmethod
    def send_due_reminders(db: Session) -> int:
        """PDF: notificar al estudiante 7 días antes de la fecha de
        vencimiento. Corre cada hora en el hilo del backend, en cada inicio
        de sesión y desde el cron externo (/api/cron/reminders).
        `last_reminder_due_date` evita repetir el mismo aviso."""
        alert_days = int(get_institution_config(db).alert_days_before)
        today = clock.today()
        limit = today + timedelta(days=alert_days)
        enrollments = (
            db.query(Enrollment)
            .options(joinedload(Enrollment.student), joinedload(Enrollment.diploma))
            .filter(Enrollment.status.in_(TRACKED_STATUSES))
            .all()
        )
        # Aprovecha la misma pasada para marcar como PENDIENTE a quien ya
        # se pasó de su fecha.
        statuses = PaymentService.refresh_enrollment_statuses(db, enrollments)
        sent = 0
        for enrollment in enrollments:
            due_date = statuses[enrollment.id].next_due
            if due_date is None or not (today <= due_date <= limit):
                continue
            if enrollment.last_reminder_due_date == due_date:
                continue
            EmailService.send_due_reminder(enrollment, due_date, tuition_fee(db, enrollment.tuition_plan))
            enrollment.last_reminder_due_date = due_date
            sent += 1
        if sent:
            db.commit()
        return sent

    @staticmethod
    def get_by_id(db: Session, payment_id: int):
        payment = PaymentRepository.get_by_id(db, payment_id)
        if not payment:
            raise HTTPException(status_code=404, detail="El pago no existe")
        return payment

    @staticmethod
    def get_all(db: Session):
        return PaymentRepository.get_all(db)

    @staticmethod
    def void(db: Session, payment_id: int, reason: str, user) -> Payment:
        """Anula un cobro (error de digitación, devolución) sin borrarlo:
        queda en el historial con quién, cuándo y por qué, deja de sumar en
        caja y en reportes, y las cuotas vuelven a quedar por cobrar.

        Un comprobante se anula completo: si cubría 3 cuotas, se anulan las
        3. Anular solo una dejaría un ticket impreso que no coincide con lo
        registrado."""
        payment = PaymentService.get_by_id(db, payment_id)
        if payment.status == "ANULADO":
            raise HTTPException(status_code=400, detail="El pago ya está anulado")
        if payment.status != "PAGADO":
            raise HTTPException(status_code=400, detail="Solo se anulan pagos cobrados")
        note = f"ANULADO el {clock.today():%d/%m/%Y} por {user.full_name}: {reason}"
        affected = [payment]
        receipt = payment.receipt
        if receipt is not None:
            affected = [p for p in receipt.payments if p.status == "PAGADO"]
            receipt.status = "ANULADO"
            receipt.void_reason = reason[:200]
        for item in affected:
            item.status = "ANULADO"
            item.observations = (f"{item.observations} | {note}" if item.observations else note)[:500]
        audit_service.record(
            db, user, "ANULACION_PAGO", "receipt" if receipt else "payment",
            receipt.id if receipt else payment.id,
            f"{receipt.number if receipt else f'Pago #{payment.id}'} · "
            f"{len(affected)} cuota(s) · ${sum(Decimal(str(p.total)) for p in affected):.2f} · {reason}",
        )
        db.commit()
        db.refresh(payment)
        if payment.enrollment and payment.enrollment.status in TRACKED_STATUSES:
            PaymentService.refresh_enrollment_statuses(db, [payment.enrollment])
        return payment
