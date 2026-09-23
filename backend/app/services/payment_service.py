import calendar
import logging
from datetime import date, timedelta
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy.orm import Session
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
    def _add_months(base_date: date, months: int) -> date:
        month_index = base_date.month - 1 + months
        year = base_date.year + month_index // 12
        month = month_index % 12 + 1
        day = min(base_date.day, calendar.monthrange(year, month)[1])
        return date(year, month, day)

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
    def _apply_due_charges(db: Session):
        due_payments = PaymentRepository.get_due_unpaid(db, date.today())

        if not due_payments:
            return

        for payment in due_payments:
            payment.status = "PENDIENTE"
            if payment.enrollment:
                payment.enrollment.status = "PENDIENTE"
        db.commit()

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
        if data.months < 1 or data.months > 12:
            raise HTTPException(status_code=400, detail="Puedes pagar entre 1 y 12 meses")

        PaymentService._apply_due_charges(db)
        today = data.payment_date
        pending_payment = (
            db.query(Payment)
            .filter(Payment.enrollment_id == enrollment.id, Payment.status == "PENDIENTE")
            .order_by(Payment.due_date.asc())
            .first()
        )
        cycle_days = PaymentService._cycle_days(db)
        last_payment = PaymentRepository.get_last_by_enrollment(db, enrollment.id)
        first_due = pending_payment.due_date if pending_payment else (
            last_payment.due_date + timedelta(days=cycle_days)
            if last_payment else enrollment.start_date
        )
        surcharge = (
            PaymentService._late_fee(db)
            if first_due < today and data.apply_late_fee
            else Decimal("0.00")
        )
        monthly_amount = Decimal(str(enrollment.diploma.monthly_fee))
        amount = monthly_amount * data.months
        total = amount + surcharge
        if data.cash_received < total:
            raise HTTPException(status_code=400, detail=f"El efectivo debe ser de al menos ${total:.2f}")

        payments = []
        for index in range(data.months):
            due_date = first_due + timedelta(days=cycle_days * index)
            payments.append(Payment(
                enrollment_id=enrollment.id,
                cashier_id=cashier_id,
                payment_date=today,
                due_date=due_date,
                amount=monthly_amount,
                surcharge=surcharge if index == 0 else Decimal("0.00"),
                total=monthly_amount + (surcharge if index == 0 else Decimal("0.00")),
                payment_type=data.payment_type,
                status="PAGADO",
                cash_received=data.cash_received if index == 0 else None,
                change=(data.cash_received - total) if index == 0 else None,
                observations=data.observations or f"Cobro de {data.months} mes(es)",
            ))
        created = PaymentRepository.create_many(db, payments)
        enrollment.status = "ACTIVA"
        db.commit()
        next_payment = created[-1].due_date + timedelta(days=cycle_days)
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
        pending = (
            db.query(Payment)
            .filter(Payment.enrollment_id == enrollment_id, Payment.status == "PENDIENTE")
            .order_by(Payment.due_date.asc())
            .first()
        )
        last = PaymentRepository.get_last_by_enrollment(db, enrollment_id)
        due_date = pending.due_date if pending else (
            last.due_date + timedelta(days=PaymentService._cycle_days(db)) if last else enrollment.start_date
        )
        today = date.today()
        surcharge = PaymentService._late_fee(db) if due_date < today else Decimal("0.00")
        return {
            "enrollment_id": enrollment_id,
            "student_name": enrollment.student.full_name,
            "diploma_name": enrollment.diploma.name,
            "due_date": due_date,
            "days_until_due": (due_date - today).days,
            "monthly_amount": Decimal(str(enrollment.diploma.monthly_fee)),
            "automatic_surcharge": surcharge,
            "is_overdue": due_date < today,
        }

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

        if data.months <= 0:
            raise HTTPException(
                status_code=400,
                detail="El número de meses debe ser mayor a cero"
            )

        monthly_fee = Decimal(str(enrollment.diploma.monthly_fee))

        # El adelanto continúa después de la última cuota ya generada
        last_payment = PaymentRepository.get_last_by_enrollment(
            db,
            enrollment.id
        )

        start_due_date = (
            PaymentService._add_months(last_payment.due_date, 1)
            if last_payment else enrollment.start_date
        )

        payments = []

        for i in range(data.months):
            due_date = PaymentService._add_months(start_due_date, i)

            # Aunque se paga todo por adelantado, cada cuota solo se
            # considera cobrada cuando se cumple su fecha de pago
            status = (
                "PAGADO" if due_date <= data.payment_date else "PENDIENTE"
            )

            payments.append(
                Payment(
                    enrollment_id=enrollment.id,
                    cashier_id=cashier_id,
                    payment_date=data.payment_date,
                    due_date=due_date,
                    amount=monthly_fee,
                    surcharge=Decimal("0.00"),
                    total=monthly_fee,
                    payment_type=data.payment_type,
                    status=status,
                    cash_received=data.cash_received if i == 0 else None,
                    change=data.change if i == 0 else None,
                    observations=(
                        data.observations
                        or f"Pago adelantado de {data.months} meses"
                    ) if i == 0 else f"Cuota {i + 1} de {data.months} (pago adelantado)"
                )
            )

        created_payments = PaymentRepository.create_many(db, payments)

        for created in created_payments:
            PaymentService._notify_if_paid(created)

        return created_payments

    @staticmethod
    def get_by_id(db: Session, payment_id: int):

        PaymentService._apply_due_charges(db)

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

        PaymentService._apply_due_charges(db)

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