from decimal import Decimal
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user
from app.core import clock
from app.core.pricing import TUITION_LABELS, tuition_fees
from app.database.session import get_db
from app.models.enrollment import Enrollment
from app.models.payment import Payment
from app.models.receipt import Receipt
from app.models.student import Student
from app.models.user import User
from app.services.payment_service import TRACKED_STATUSES, PaymentService
from app.services.receipt_service import whatsapp_phone

router = APIRouter(
    prefix="/reports",
    tags=["Reportes"],
    dependencies=[Depends(get_current_user)],
)


def _whatsapp_url(student: Student, text: str) -> str | None:
    """Enlace wa.me con el mensaje ya escrito. WhatsApp del responsable (PDF:
    datos del responsable) o, si no hay, el contacto del estudiante."""
    phone = whatsapp_phone(student.responsible_whatsapp) or whatsapp_phone(student.contact_phone)
    return f"https://wa.me/{phone}?text={quote(text)}" if phone else None


@router.get("/upcoming-payments")
def upcoming_payments(days: int = 7, include_overdue: bool = True, db: Session = Depends(get_db)):
    """Cobros próximos y atrasados (PDF punto 6: "muestra al cajero o
    administrador los pagos próximos"), con cuántas cuotas debe cada
    estudiante, cuánto, si ya se le envió el aviso y un enlace de WhatsApp."""
    today = clock.today()
    limit = today.toordinal() + max(0, min(days, 60))
    enrollments = (
        db.query(Enrollment)
        .options(joinedload(Enrollment.student), joinedload(Enrollment.diploma))
        .filter(Enrollment.status.in_(TRACKED_STATUSES))
        .all()
    )
    statuses = PaymentService.refresh_enrollment_statuses(db, enrollments)
    fees = tuition_fees(db)
    late_fee = PaymentService.late_fee(db)
    rows = []
    for enrollment in enrollments:
        info = statuses[enrollment.id]
        due_date = info.next_due
        if due_date is None or due_date.toordinal() > limit or (due_date < today and not include_overdue):
            continue
        amount = fees.get(enrollment.tuition_plan, fees["GRUPAL"])
        is_overdue = due_date < today
        owed = amount * max(info.overdue, 1) + (late_fee if is_overdue else Decimal("0.00"))
        student = enrollment.student
        message = (
            f"Hola {student.full_name}, le saludamos de CTC El Salvador. "
            + (
                f"Su colegiatura de {enrollment.diploma.name} venció el {due_date:%d/%m/%Y}. "
                f"Saldo pendiente: ${owed:.2f} (incluye recargo por mora)."
                if is_overdue else
                f"Le recordamos que su colegiatura de {enrollment.diploma.name} vence el "
                f"{due_date:%d/%m/%Y}. Monto: ${amount:.2f}."
            )
        )
        rows.append({
            "enrollment_id": enrollment.id,
            "student_id": student.id,
            "student_name": student.full_name,
            "student_email": student.email,
            "responsible_name": student.responsible_name,
            "phone": student.responsible_whatsapp or student.contact_phone,
            "diploma_name": enrollment.diploma.name,
            "tuition_plan": TUITION_LABELS.get(enrollment.tuition_plan, enrollment.tuition_plan),
            "status": enrollment.status,
            "due_date": due_date,
            "amount": amount,
            "days_remaining": (due_date - today).days,
            "is_overdue": is_overdue,
            "overdue_installments": info.overdue,
            "amount_owed": owed,
            "reminder_sent": enrollment.last_reminder_due_date == due_date,
            "whatsapp_url": _whatsapp_url(student, message),
        })
    rows.sort(key=lambda row: row["due_date"])
    return rows


@router.get("/student-history/{student_id}")
def student_history(student_id: int, db: Session = Depends(get_db)):
    """Estado de cuenta del estudiante: sus inscripciones con cuotas pagadas,
    vencidas y saldo por pagar del diplomado, y cada cobro (incluidos los
    anulados)."""
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
    statuses = PaymentService.refresh_enrollment_statuses(db, enrollments)
    fees = tuition_fees(db)
    late_fee = PaymentService.late_fee(db)
    diploma_by_enrollment = {e.id: e.diploma.name for e in enrollments}
    today = clock.today()

    rows = (
        db.query(Payment, User.full_name, Receipt.id)
        .outerjoin(User, User.id == Payment.cashier_id)
        .outerjoin(Receipt, Receipt.id == Payment.receipt_id)
        .filter(Payment.enrollment_id.in_(diploma_by_enrollment.keys()))
        .order_by(Payment.payment_date.asc(), Payment.due_date.asc(), Payment.id.asc())
        .all()
    ) if enrollments else []

    payments = [
        {
            "id": payment.id,
            "receipt_number": f"R-{receipt_id:06d}" if receipt_id else None,
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
            "cashier_name": cashier_name,
            "observations": payment.observations,
        }
        for payment, cashier_name, receipt_id in rows
    ]
    paid = [p for p in payments if p["status"] == "PAGADO"]

    enrollment_rows = []
    overdue_balance = Decimal("0.00")
    remaining_balance = Decimal("0.00")
    for e in enrollments:
        info = statuses[e.id]
        tracked = e.status in TRACKED_STATUSES
        fee = fees.get(e.tuition_plan, fees["GRUPAL"])
        is_overdue = tracked and info.next_due is not None and info.next_due < today
        owed = (fee * info.overdue + late_fee) if is_overdue else Decimal("0.00")
        remaining = fee * info.remaining if tracked else Decimal("0.00")
        overdue_balance += owed
        remaining_balance += remaining
        enrollment_rows.append({
            "id": e.id,
            "diploma_name": e.diploma.name,
            "schedule_name": e.schedule.name,
            "tuition_plan": e.tuition_plan,
            "status": e.status,
            "enrollment_date": e.enrollment_date,
            "start_date": e.start_date,
            "end_date": e.end_date,
            "next_payment_date": info.next_due if tracked else None,
            "is_overdue": is_overdue,
            "installments_total": info.total,
            "installments_paid": info.paid,
            "overdue_installments": info.overdue if tracked else 0,
            "amount_overdue": float(owed),
            "remaining_balance": float(remaining),
        })

    return {
        "student": {
            "id": student.id,
            "full_name": student.full_name,
            "email": student.email,
            "contact_phone": student.contact_phone,
            "responsible_name": student.responsible_name,
        },
        "generated_at": clock.now().strftime("%d/%m/%Y %H:%M"),
        "enrollments": enrollment_rows,
        "payments": payments,
        "totals": {
            "paid": round(sum(p["total"] for p in paid), 2),
            "registration": round(sum(p["total"] for p in paid if p["kind"] == "MATRICULA"), 2),
            "tuition": round(sum(p["total"] for p in paid if p["kind"] == "COLEGIATURA"), 2),
            "surcharges": round(sum(p["surcharge"] for p in paid), 2),
            "voided": round(sum(p["total"] for p in payments if p["status"] == "ANULADO"), 2),
            "tuition_installments_paid": sum(1 for p in paid if p["kind"] == "COLEGIATURA"),
            "overdue_enrollments": sum(1 for e in enrollment_rows if e["is_overdue"]),
            "amount_overdue": float(overdue_balance),
            "remaining_balance": float(remaining_balance),
        },
    }
