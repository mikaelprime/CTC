from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user
from app.database.session import get_db
from app.models.enrollment import Enrollment
from app.models.payment import Payment
from app.services.cashier_service import CashierService

router = APIRouter(
    prefix="/reports",
    tags=["Reportes"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/upcoming-payments")
def upcoming_payments(days: int = 7, db: Session = Depends(get_db)):
    today = date.today()
    limit = today + timedelta(days=max(0, min(days, 60)))
    payments = (
        db.query(Payment)
        .options(joinedload(Payment.enrollment).joinedload(Enrollment.student))
        .filter(
            Payment.status == "PENDIENTE",
            Payment.due_date >= today,
            Payment.due_date <= limit,
        )
        .order_by(Payment.due_date.asc())
        .all()
    )
    return [
        {
            "payment_id": payment.id,
            "enrollment_id": payment.enrollment_id,
            "student_name": payment.enrollment.student.full_name,
            "student_email": payment.enrollment.student.email,
            "due_date": payment.due_date,
            "amount": payment.total,
            "days_remaining": (payment.due_date - today).days,
        }
        for payment in payments
    ]


@router.get("/cashier-monthly")
def cashier_monthly(year: int, month: int, db: Session = Depends(get_db)):
    return CashierService.monthly_closure(db, year, month)
