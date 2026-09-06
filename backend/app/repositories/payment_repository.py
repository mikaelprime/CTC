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