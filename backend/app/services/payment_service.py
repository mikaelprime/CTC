from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.payment import Payment
from app.repositories.payment_repository import PaymentRepository
from app.repositories.enrollment_repository import EnrollmentRepository

class PaymentService:

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

        return PaymentRepository.create(db, payment)

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