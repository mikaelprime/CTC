from datetime import date
from sqlalchemy.orm import Session
from app.models.payment import Payment

class PaymentRepository:
    @staticmethod
    def create(db: Session, payment: Payment):
        db.add(payment)
        db.commit()
        db.refresh(payment)
        return payment

    @staticmethod
    def create_many(db: Session, payments: list[Payment]):
        db.add_all(payments)
        db.commit()

        for payment in payments:
            db.refresh(payment)

        return payments

    @staticmethod
    def get_last_by_enrollment(db: Session, enrollment_id: int):
        return (
            db.query(Payment)
            .filter(Payment.enrollment_id == enrollment_id)
            .order_by(Payment.due_date.desc())
            .first()
        )

    @staticmethod
    def get_due_unpaid(db: Session, today: date):
        return (
            db.query(Payment)
            .filter(
                Payment.status == "PENDIENTE",
                Payment.due_date <= today
            )
            .all()
        )

    @staticmethod
    def mark_as_paid(db: Session, payments: list[Payment]):
        for payment in payments:
            payment.status = "PAGADO"

        db.commit()

        for payment in payments:
            db.refresh(payment)

    @staticmethod
    def get_by_id(db: Session, payment_id: int):
        return db.query(Payment).filter(
            Payment.id == payment_id
        ).first()

    @staticmethod
    def get_all(db: Session):
        return db.query(Payment).all()

    @staticmethod
    def update(db: Session, payment: Payment):
        db.commit()
        db.refresh(payment)
        return payment

    @staticmethod
    def delete(db: Session, payment: Payment):
        db.delete(payment)
        db.commit()