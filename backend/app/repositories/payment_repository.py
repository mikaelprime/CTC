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
        # Solo colegiatura: la matrícula (kind="MATRICULA") es un cobro
        # único que no forma parte del ciclo recurrente de 28 días, y
        # mezclarla aquí desplazaba mal el primer vencimiento de colegiatura.
        return (
            db.query(Payment)
            .filter(Payment.enrollment_id == enrollment_id, Payment.kind == "COLEGIATURA")
            .order_by(Payment.due_date.desc())
            .first()
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