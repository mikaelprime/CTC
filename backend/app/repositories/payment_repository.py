from sqlalchemy.orm import Session
from app.models.payment import Payment


class PaymentRepository:
    @staticmethod
    def get_by_id(db: Session, payment_id: int):
        return db.query(Payment).filter(Payment.id == payment_id).first()

    @staticmethod
    def get_all(db: Session):
        return db.query(Payment).order_by(Payment.id.desc()).all()
