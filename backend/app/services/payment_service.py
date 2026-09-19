import calendar
from datetime import date
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.payment import Payment
from app.repositories.payment_repository import PaymentRepository
from app.repositories.enrollment_repository import EnrollmentRepository
from app.services.email_service import EmailService

class PaymentService:

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

    @staticmethod
    def _apply_due_charges(db: Session):
        due_payments = PaymentRepository.get_due_unpaid(db, date.today())

        if not due_payments:
            return

        PaymentRepository.mark_as_paid(db, due_payments)

        for payment in due_payments:
            PaymentService._notify_if_paid(payment)

    @staticmethod
    def create(db: Session, data):

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

        # Crear pago
        payment = Payment(
            enrollment_id=data.enrollment_id,
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
    def create_advance(db: Session, data):

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