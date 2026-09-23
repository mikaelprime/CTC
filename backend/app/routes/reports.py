from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user, require_admin
from app.core.pricing import TUITION_PLANS
from app.database.session import get_db
from app.models.enrollment import Enrollment
from app.models.payment import Payment
from app.models.student import Student
from app.models.user import User
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


@router.get("/student-history/{student_id}")
def student_history(student_id: int, db: Session = Depends(get_db)):
    """Todo lo que ha pagado (o se le ha anulado) un estudiante, en todas sus
    inscripciones, con el estado actual de cada una."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")

    enrollments = (
        db.query(Enrollment)
        .options(joinedload(Enrollment.diploma), joinedload(Enrollment.schedule))
        .filter(Enrollment.student_id == student_id)
        .order_by(Enrollment.enrollment_date.asc())
        .all()
    )
    due_dates = PaymentService.refresh_enrollment_statuses(db, enrollments)
    diploma_by_enrollment = {e.id: e.diploma.name for e in enrollments}
    today = date.today()

    rows = (
        db.query(Payment, User.full_name)
        .outerjoin(User, User.id == Payment.cashier_id)
        .filter(Payment.enrollment_id.in_(diploma_by_enrollment.keys()))
        .order_by(Payment.payment_date.asc(), Payment.due_date.asc(), Payment.id.asc())
        .all()
    ) if enrollments else []

    payments = [
        {
            "id": payment.id,
            "enrollment_id": payment.enrollment_id,
            "diploma_name": diploma_by_enrollment[payment.enrollment_id],
            "kind": payment.kind,
            "payment_date": payment.payment_date,
            "due_date": payment.due_date,
            "amount": float(payment.amount),
            "surcharge": float(payment.surcharge or 0),
            "total": float(payment.total),
            "payment_type": payment.payment_type,
            "status": payment.status,
            "cash_received": float(payment.cash_received) if payment.cash_received is not None else None,
            "change": float(payment.change) if payment.change is not None else None,
            "cashier_name": cashier_name,
            "observations": payment.observations,
        }
        for payment, cashier_name in rows
    ]
    paid = [p for p in payments if p["status"] == "PAGADO"]
    active = [e for e in enrollments if e.status in ("ACTIVA", "PENDIENTE")]
    return {
        "student": {
            "id": student.id,
            "full_name": student.full_name,
            "email": student.email,
            "contact_phone": student.contact_phone,
        },
        "enrollments": [
            {
                "id": e.id,
                "diploma_name": e.diploma.name,
                "schedule_name": e.schedule.name,
                "tuition_plan": e.tuition_plan,
                "status": e.status,
                "enrollment_date": e.enrollment_date,
                "start_date": e.start_date,
                "next_payment_date": due_dates.get(e.id) if e.status in ("ACTIVA", "PENDIENTE") else None,
                "is_overdue": e.status in ("ACTIVA", "PENDIENTE") and due_dates[e.id] < today,
            }
            for e in enrollments
        ],
        "payments": payments,
        "totals": {
            "paid": round(sum(p["total"] for p in paid), 2),
            "registration": round(sum(p["total"] for p in paid if p["kind"] == "MATRICULA"), 2),
            "tuition": round(sum(p["total"] for p in paid if p["kind"] == "COLEGIATURA"), 2),
            "surcharges": round(sum(p["surcharge"] for p in paid), 2),
            "voided": round(sum(p["total"] for p in payments if p["status"] == "ANULADO"), 2),
            "tuition_installments_paid": sum(1 for p in paid if p["kind"] == "COLEGIATURA"),
            "overdue_enrollments": sum(1 for e in active if due_dates[e.id] < today),
        },
    }


@router.get("/cashier-monthly", dependencies=[Depends(require_admin)])
def cashier_monthly(year: int, month: int, db: Session = Depends(get_db)):
    return CashierService.monthly_closure(db, year, month)
