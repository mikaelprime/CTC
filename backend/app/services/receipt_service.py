"""Datos del ticket de un cobro, armados en el servidor.

El escritorio imprime exactamente lo que devuelve esto, así el ticket del
momento del cobro y una reimpresión posterior son idénticos (mismo número
correlativo, mismas cuotas, mismo cajero).
"""

from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core import clock
from app.core.pricing import REGISTRATION_LABELS, TUITION_LABELS
from app.core.runtime_config import get_institution_config
from app.models.payment import Payment
from app.models.receipt import Receipt
from app.models.user import User
from app.services.payment_service import PaymentService


def _money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def _line(payment: Payment, installments_total: int, cycle: int) -> dict:
    enrollment = payment.enrollment
    if payment.kind == "MATRICULA":
        concept = REGISTRATION_LABELS.get(enrollment.registration_type, "Matrícula")
    else:
        number = (payment.due_date - enrollment.start_date).days // cycle + 1
        concept = f"Colegiatura cuota {number} de {installments_total} (vence {payment.due_date:%d/%m/%Y})"
    return {
        "payment_id": payment.id,
        "concept": concept,
        "amount": _money(payment.amount),
        "surcharge": _money(payment.surcharge),
        "total": _money(payment.total),
        "status": payment.status,
    }


def _ticket(db: Session, *, number, issued_at, payments, enrollment, cashier_name, payment_type,
            total, cash_received, change, status, kind) -> dict:
    cycle = PaymentService.cycle_days(db)
    info = PaymentService.refresh_enrollment_statuses(db, [enrollment])[enrollment.id]
    issued_local = clock.to_local(issued_at)
    return {
        "institution_name": get_institution_config(db).institution_name,
        "receipt_number": number,
        "issued_at": issued_local.strftime("%d/%m/%Y %H:%M") if issued_local else None,
        "status": status,
        "kind": kind,
        "cashier_name": cashier_name,
        "enrollment_id": enrollment.id,
        "student_name": enrollment.student.full_name,
        "student_email": enrollment.student.email,
        "whatsapp": enrollment.student.responsible_whatsapp or enrollment.student.contact_phone,
        "diploma_name": enrollment.diploma.name,
        "schedule_name": enrollment.schedule.name,
        "tuition_plan": TUITION_LABELS.get(enrollment.tuition_plan, enrollment.tuition_plan),
        "lines": [_line(p, info.total, cycle) for p in sorted(payments, key=lambda p: p.due_date)],
        "surcharge": sum((_money(p.surcharge) for p in payments), Decimal("0.00")),
        "total": _money(total),
        "payment_type": payment_type,
        "cash_received": _money(cash_received),
        "change": _money(change),
        "next_payment_date": info.next_due,
        "installments_paid": info.paid,
        "installments_total": info.total,
    }


def receipt_ticket(db: Session, receipt: Receipt) -> dict:
    return _ticket(
        db,
        number=receipt.number,
        issued_at=receipt.issued_at,
        payments=list(receipt.payments),
        enrollment=receipt.enrollment,
        cashier_name=receipt.cashier.full_name if receipt.cashier else None,
        payment_type=receipt.payment_type,
        total=receipt.total,
        cash_received=receipt.cash_received,
        change=receipt.change,
        status=receipt.status,
        kind=receipt.kind,
    )


def payment_ticket(db: Session, payment_id: int) -> dict:
    """Ticket del cobro al que pertenece un pago. Los pagos anteriores a los
    comprobantes correlativos no tienen uno: se arma con el pago solo."""
    payment = PaymentService.get_by_id(db, payment_id)
    if payment.receipt is not None:
        return receipt_ticket(db, payment.receipt)
    cashier = db.get(User, payment.cashier_id) if payment.cashier_id else None
    return _ticket(
        db,
        number=f"PAGO-{payment.id:06d}",
        issued_at=payment.created_at,
        payments=[payment],
        enrollment=payment.enrollment,
        cashier_name=cashier.full_name if cashier else None,
        payment_type=payment.payment_type,
        total=payment.total,
        cash_received=payment.cash_received if payment.cash_received is not None else payment.total,
        change=payment.change or 0,
        status="ANULADO" if payment.status == "ANULADO" else "EMITIDO",
        kind=payment.kind,
    )


def get_receipt(db: Session, receipt_id: int) -> Receipt:
    receipt = db.get(Receipt, receipt_id)
    if receipt is None:
        raise HTTPException(status_code=404, detail="El comprobante no existe")
    return receipt


def whatsapp_phone(raw: str | None) -> str | None:
    """Número en formato internacional para un enlace wa.me (503XXXXXXXX)."""
    if not raw:
        return None
    digits = "".join(ch for ch in raw if ch.isdigit())
    if raw.strip().startswith("+"):
        return digits or None
    return f"503{digits}" if len(digits) == 8 else None

