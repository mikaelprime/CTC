import logging
from types import SimpleNamespace
from datetime import date, timedelta
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from app.core.pricing import TUITION_PLANS
from app.core.runtime_config import get_institution_config
from app.models.enrollment import Enrollment
from app.models.payment import Payment
from app.repositories.payment_repository import PaymentRepository
from app.repositories.enrollment_repository import EnrollmentRepository
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)


class PaymentService:

    @staticmethod
    def _cycle_days(db: Session) -> int:
        return int(get_institution_config(db).payment_cycle_days)

    @staticmethod
    def _late_fee(db: Session) -> Decimal:
        return Decimal(str(get_institution_config(db).late_fee))

    @staticmethod
    def _notify_if_paid(payment: Payment):
        if payment.status == "PAGADO":
            EmailService.send_payment_confirmation(payment)
        else:
            logger.info(
                "Pago #%s registrado con estado %s (no PAGADO); no se envía comprobante.",
                payment.id, payment.status,
            )

    @staticmethod
    def next_due_dates(db: Session, enrollments: list[Enrollment]) -> dict[int, date]:
        """Próximo vencimiento de colegiatura de cada matrícula, con dos
        consultas en total (no dos por matrícula): la cuota PENDIENTE más
        antigua si existe; si no, la última cuota de colegiatura + ciclo; si
        aún no hay cuotas, la fecha de inicio de clases."""
        ids = [enrollment.id for enrollment in enrollments]
        if not ids:
            return {}
        pending = dict(
            db.query(Payment.enrollment_id, func.min(Payment.due_date))
            .filter(Payment.enrollment_id.in_(ids), Payment.status == "PENDIENTE")
            .group_by(Payment.enrollment_id)
            .all()
        )
        last = dict(
            db.query(Payment.enrollment_id, func.max(Payment.due_date))
            .filter(Payment.enrollment_id.in_(ids), Payment.kind == "COLEGIATURA")
            .group_by(Payment.enrollment_id)
            .all()
        )
        cycle = timedelta(days=PaymentService._cycle_days(db))
        result = {}
        for enrollment in enrollments:
            if enrollment.id in pending:
                result[enrollment.id] = pending[enrollment.id]
            elif enrollment.id in last:
                result[enrollment.id] = last[enrollment.id] + cycle
            else:
                result[enrollment.id] = enrollment.start_date
        return result

    @staticmethod
    def refresh_enrollment_statuses(db: Session, enrollments: list[Enrollment] | None = None) -> dict[int, date]:
        """PDF: cambiar el estatus del alumno a "PENDIENTE" si se superan los
        28 días sin registrar un nuevo cobro (su próximo vencimiento ya pasó),
        y devolverlo a "ACTIVA" cuando se pone al día. Solo toca matrículas
        ACTIVA/PENDIENTE: un estado puesto a mano (p. ej. FINALIZADA) se
        respeta. Devuelve el próximo vencimiento por matrícula."""
        if enrollments is None:
            enrollments = db.query(Enrollment).filter(
                Enrollment.status.in_(("ACTIVA", "PENDIENTE"))
            ).all()
        due_dates = PaymentService.next_due_dates(db, enrollments)
        today = date.today()
        changed = False
        for enrollment in enrollments:
            if enrollment.status not in ("ACTIVA", "PENDIENTE"):
                continue
            expected = "PENDIENTE" if due_dates[enrollment.id] < today else "ACTIVA"
            if enrollment.status != expected:
                enrollment.status = expected
                changed = True
        if changed:
            db.commit()
        return due_dates

    @staticmethod
    def collect(db: Session, data, cashier_id: int | None = None):
        # Bloquea la fila de la matrícula hasta el commit: si dos cobros
        # llegan casi al mismo tiempo para la misma matrícula (dos cajeros,
        # o un doble clic que dispara dos peticiones), el segundo espera a
        # que el primero termine en vez de leer el mismo "próximo pago
        # pendiente" y generar dos cuotas duplicadas.
        locked = db.query(Enrollment.id).filter(Enrollment.id == data.enrollment_id).with_for_update().first()
        if not locked:
            raise HTTPException(status_code=404, detail="La matrícula no existe")

        enrollment = EnrollmentRepository.get_by_id(db, data.enrollment_id)
        if not enrollment:
            raise HTTPException(status_code=404, detail="La matrícula no existe")
        if enrollment.status == "ANULADA":
            raise HTTPException(status_code=400, detail="La matrícula está anulada; no se le puede cobrar")
        if data.months < 1 or data.months > 12:
            raise HTTPException(status_code=400, detail="Puedes pagar entre 1 y 12 meses")

        today = data.payment_date
        # Cuotas ya generadas y aún sin cobrar (p. ej. registradas a mano por
        # el administrador): se cobran esas primero, en vez de crear cuotas
        # nuevas con la misma fecha y dejar las viejas PENDIENTE para siempre.
        pending_payments = (
            db.query(Payment)
            .filter(Payment.enrollment_id == enrollment.id, Payment.status == "PENDIENTE")
            .order_by(Payment.due_date.asc())
            .all()
        )
        cycle_days = PaymentService._cycle_days(db)
        first_due = PaymentService.next_due_dates(db, [enrollment])[enrollment.id]
        surcharge = (
            PaymentService._late_fee(db)
            if first_due < today and data.apply_late_fee
            else Decimal("0.00")
        )
        monthly_amount = TUITION_PLANS.get(enrollment.tuition_plan, TUITION_PLANS["GRUPAL"])
        amount = monthly_amount * data.months
        total = amount + surcharge
        if data.cash_received < total:
            raise HTTPException(status_code=400, detail=f"El efectivo debe ser de al menos ${total:.2f}")

        created = []
        due_date = first_due
        for index in range(data.months):
            fee = surcharge if index == 0 else Decimal("0.00")
            payment = pending_payments[index] if index < len(pending_payments) else None
            if payment is None:
                if created:
                    due_date = created[-1].due_date + timedelta(days=cycle_days)
                payment = Payment(enrollment_id=enrollment.id, due_date=due_date, kind="COLEGIATURA")
                db.add(payment)
            payment.cashier_id = cashier_id
            payment.payment_date = today
            payment.amount = monthly_amount
            payment.surcharge = fee
            payment.total = monthly_amount + fee
            payment.payment_type = data.payment_type
            payment.status = "PAGADO"
            payment.cash_received = data.cash_received if index == 0 else None
            payment.change = (data.cash_received - total) if index == 0 else None
            payment.observations = data.observations or f"Cobro de {data.months} mes(es)"
            created.append(payment)
        db.commit()
        for payment in created:
            db.refresh(payment)
        # Puede seguir PENDIENTE si debía varios ciclos y solo pagó uno.
        due_dates = PaymentService.refresh_enrollment_statuses(db, [enrollment])
        next_payment = due_dates[enrollment.id]
        EmailService.send_payment_confirmation(
            created[0], next_payment_date=next_payment, months_paid=data.months
        )
        return {
            "payment_ids": [payment.id for payment in created],
            "enrollment_id": enrollment.id,
            "months_paid": data.months,
            "amount": amount,
            "surcharge": surcharge,
            "total": total,
            "cash_received": data.cash_received,
            "change": data.cash_received - total,
            "first_due_date": first_due,
            "next_payment_date": next_payment,
            "late": surcharge > 0,
        }

    @staticmethod
    def next_payment_info(db: Session, enrollment_id: int) -> dict:
        enrollment = EnrollmentRepository.get_by_id(db, enrollment_id)
        if not enrollment:
            raise HTTPException(status_code=404, detail="La matrícula no existe")
        due_date = PaymentService.refresh_enrollment_statuses(db, [enrollment])[enrollment.id]
        today = date.today()
        surcharge = PaymentService._late_fee(db) if due_date < today else Decimal("0.00")
        return {
            "enrollment_id": enrollment_id,
            "student_name": enrollment.student.full_name,
            "diploma_name": enrollment.diploma.name,
            "due_date": due_date,
            "days_until_due": (due_date - today).days,
            "monthly_amount": TUITION_PLANS.get(enrollment.tuition_plan, TUITION_PLANS["GRUPAL"]),
            "automatic_surcharge": surcharge,
            "is_overdue": due_date < today,
            "status": enrollment.status,
        }

    @staticmethod
    def send_due_reminders(db: Session) -> int:
        """Manda un recordatorio por correo a los estudiantes cuya próxima
        colegiatura vence dentro de `alert_days_before` días. Se llama desde
        el login (best-effort, no bloquea si falla) en vez de un cron: el
        backend gratuito no tiene forma de "despertar solo" a diario, pero sí
        se ejecuta cada vez que alguien entra a la app. `last_reminder_due_date`
        evita mandar el mismo aviso de nuevo en cada login del mismo día.
        """
        alert_days = get_institution_config(db).alert_days_before
        today = date.today()
        limit = today + timedelta(days=int(alert_days))
        enrollments = (
            db.query(Enrollment)
            .options(joinedload(Enrollment.student), joinedload(Enrollment.diploma))
            .filter(Enrollment.status.in_(("ACTIVA", "PENDIENTE")))
            .all()
        )
        # Aprovecha la misma pasada para marcar como PENDIENTE a quien ya
        # se pasó de su fecha (el login es el "cron" de este backend).
        due_dates = PaymentService.refresh_enrollment_statuses(db, enrollments)
        sent = 0
        for enrollment in enrollments:
            due_date = due_dates[enrollment.id]
            if not (today <= due_date <= limit):
                continue
            if enrollment.last_reminder_due_date == due_date:
                continue
            amount = TUITION_PLANS.get(enrollment.tuition_plan, TUITION_PLANS["GRUPAL"])
            EmailService.send_due_reminder(enrollment, due_date, amount)
            enrollment.last_reminder_due_date = due_date
            sent += 1
        if sent:
            db.commit()
        return sent

    @staticmethod
    def create(db: Session, data, cashier_id: int | None = None):

        # Validar matrícula
        enrollment = EnrollmentRepository.get_by_id(
            db,
            data.enrollment_id
        )

        if not enrollment:
            raise HTTPException(
                status_code=404,
                detail="La matrícula no existe"
            )

        # Validar montos
        if data.amount < 0:
            raise HTTPException(
                status_code=400,
                detail="El monto no puede ser negativo"
            )

        if data.surcharge < 0:
            raise HTTPException(
                status_code=400,
                detail="El recargo no puede ser negativo"
            )

        if data.amount + data.surcharge <= 0:
            raise HTTPException(status_code=400, detail="El total debe ser mayor que cero")

        if data.cash_received is not None and data.cash_received < data.amount + data.surcharge:
            raise HTTPException(status_code=400, detail="El efectivo recibido es menor al total")

        # Crear pago
        payment = Payment(
            enrollment_id=data.enrollment_id,
            cashier_id=cashier_id,
            payment_date=data.payment_date,
            due_date=data.due_date,
            amount=data.amount,
            surcharge=data.surcharge,
            total=data.amount + data.surcharge,
            payment_type=data.payment_type,
            status=data.status,
            cash_received=data.cash_received,
            change=data.change,
            observations=data.observations
        )

        created = PaymentRepository.create(db, payment)

        PaymentService._notify_if_paid(created)

        return created

    @staticmethod
    def create_advance(db: Session, data, cashier_id: int | None = None):
        """Pago adelantado de varias cuotas. Antes generaba las cuotas por
        mes calendario (no cada 28 días) y dejaba las futuras en PENDIENTE
        aunque ya se habían pagado, así que aparecían como deuda y un cobro
        posterior las volvía a cobrar. Ahora reutiliza collect(): mismo ciclo,
        todas PAGADO y un solo comprobante."""
        total_hint = None
        if data.cash_received is None:
            enrollment = EnrollmentRepository.get_by_id(db, data.enrollment_id)
            if not enrollment:
                raise HTTPException(status_code=404, detail="La matrícula no existe")
            total_hint = TUITION_PLANS.get(enrollment.tuition_plan, TUITION_PLANS["GRUPAL"]) * max(data.months, 0)
        result = PaymentService.collect(
            db,
            SimpleNamespace(
                enrollment_id=data.enrollment_id,
                payment_date=data.payment_date,
                payment_type=data.payment_type,
                cash_received=data.cash_received if data.cash_received is not None else total_hint,
                months=data.months,
                observations=data.observations or f"Pago adelantado de {data.months} meses",
                apply_late_fee=False,
            ),
            cashier_id=cashier_id,
        )
        return (
            db.query(Payment)
            .filter(Payment.id.in_(result["payment_ids"]))
            .order_by(Payment.due_date.asc())
            .all()
        )

    @staticmethod
    def get_by_id(db: Session, payment_id: int):

        payment = PaymentRepository.get_by_id(
            db,
            payment_id
        )

        if not payment:
            raise HTTPException(
                status_code=404,
                detail="El pago no existe"
            )

        return payment

    @staticmethod
    def get_all(db: Session):

        return PaymentRepository.get_all(db)

    @staticmethod
    def update(db: Session, payment_id: int, data):

        payment = PaymentRepository.get_by_id(
            db,
            payment_id
        )

        if not payment:
            raise HTTPException(
                status_code=404,
                detail="El pago no existe"
            )

        update_data = data.model_dump(
            exclude_unset=True
        )

        for key, value in update_data.items():
            setattr(payment, key, value)

        if "amount" in update_data or "surcharge" in update_data:
            payment.total = (
                payment.amount +
                payment.surcharge
            )

        return PaymentRepository.update(
            db,
            payment
        )

    @staticmethod
    def delete(db: Session, payment_id: int):

        payment = PaymentRepository.get_by_id(
            db,
            payment_id
        )

        if not payment:
            raise HTTPException(
                status_code=404,
                detail="El pago no existe"
            )

        PaymentRepository.delete(
            db,
            payment
        )