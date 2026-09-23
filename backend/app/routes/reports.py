from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user
from app.core.pricing import TUITION_PLANS
from app.database.session import get_db
from app.models.enrollment import Enrollment
from app.services.cashier_service import CashierService
from app.services.payment_service import PaymentService

router = APIRouter(
    prefix="/reports",
    tags=["Reportes"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/upcoming-payments")
def upcoming_payments(days: int = 7, include_overdue: bool = True, db: Session = Depends(get_db)):
    """Cobros próximos (PDF: "muestra al cajero o administrador los pagos
    próximos"). Se calcula desde el próximo vencimiento de cada matrícula y
    no desde filas PENDIENTE en payments: el flujo normal de cobro nunca crea
    cuotas PENDIENTE por adelantado, así que antes este reporte salía vacío.
    """
    today = date.today()
    limit = today + timedelta(days=max(0, min(days, 60)))
    enrollments = (
        db.query(Enrollment)
        .options(joinedload(Enrollment.student), joinedload(Enrollment.diploma))
        .filter(Enrollment.status.in_(("ACTIVA", "PENDIENTE")))
        .all()
    )
    due_dates = PaymentService.refresh_enrollment_statuses(db, enrollments)
    rows = []
    for enrollment in enrollments:
        due_date = due_dates[enrollment.id]
        if due_date > limit or (due_date < today and not include_overdue):
            continue
        rows.append({
            "enrollment_id": enrollment.id,
            "student_name": enrollment.student.full_name,
            "student_email": enrollment.student.email,
            "diploma_name": enrollment.diploma.name,
            "status": enrollment.status,
            "due_date": due_date,
            "amount": TUITION_PLANS.get(enrollment.tuition_plan, TUITION_PLANS["GRUPAL"]),
            "days_remaining": (due_date - today).days,
            "is_overdue": due_date < today,
        })
    rows.sort(key=lambda row: row["due_date"])
    return rows


@router.get("/cashier-monthly")
def cashier_monthly(year: int, month: int, db: Session = Depends(get_db)):
    return CashierService.monthly_closure(db, year, month)
