"""Caja diaria: apertura, arqueo, cierre y reportes de cierre (PDF punto 5).

Montos en Decimal, no float: son dinero real que se audita al centavo.
"""

import json
from calendar import monthrange
from collections import OrderedDict
from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core import clock
from app.core.pricing import REGISTRATION_LABELS, TUITION_LABELS
from app.models.cash_register import CashRegister
from app.models.enrollment import Enrollment
from app.models.payment import Payment
from app.models.user import User
from app.services import audit_service

ZERO = Decimal("0.00")
CASH = "Efectivo"
# Billetes y monedas de dólar en circulación en El Salvador, para el arqueo.
DENOMINATIONS = ("100.00", "50.00", "20.00", "10.00", "5.00", "1.00", "0.25", "0.10", "0.05", "0.01")


def _money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def _concept(payment: Payment) -> str:
    enrollment = payment.enrollment
    if payment.kind == "MATRICULA":
        return REGISTRATION_LABELS.get(enrollment.registration_type, "Matrícula")
    return f"Colegiatura {TUITION_LABELS.get(enrollment.tuition_plan, enrollment.tuition_plan)}"


def summarize_payments(payments: list[Payment]) -> dict:
    """Totales de un conjunto de pagos: por concepto (matrícula por tipo,
    colegiatura por plan y recargos aparte), por método y anulados."""
    paid = [p for p in payments if p.status == "PAGADO"]
    by_concept: dict[str, Decimal] = OrderedDict()
    for payment in sorted(paid, key=lambda p: (p.kind != "MATRICULA", _concept(p))):
        key = _concept(payment)
        by_concept[key] = by_concept.get(key, ZERO) + _money(payment.amount)
    surcharges = sum((_money(p.surcharge) for p in paid), ZERO)
    if surcharges:
        by_concept["Recargos por mora"] = surcharges
    by_method: dict[str, Decimal] = OrderedDict()
    for payment in paid:
        by_method[payment.payment_type] = by_method.get(payment.payment_type, ZERO) + _money(payment.total)
    receipts = {p.receipt_id or f"p{p.id}" for p in paid}
    return {
        "total": sum((_money(p.total) for p in paid), ZERO),
        "cash_total": by_method.get(CASH, ZERO),
        "receipts": len(receipts),
        "installments": sum(1 for p in paid if p.kind == "COLEGIATURA"),
        "registrations": sum(1 for p in paid if p.kind == "MATRICULA"),
        "by_concept": [{"concept": k, "amount": v} for k, v in by_concept.items()],
        "by_method": [{"method": k, "amount": v} for k, v in by_method.items()],
        "voided_total": sum((_money(p.total) for p in payments if p.status == "ANULADO"), ZERO),
    }


def payment_rows(payments: list[Payment], cashier_names: dict[int, str]) -> list[dict]:
    rows = []
    for p in sorted(payments, key=lambda p: p.id):
        created = clock.to_local(p.created_at)
        rows.append({
            "payment_id": p.id,
            "receipt_number": p.receipt.number if p.receipt else f"PAGO-{p.id:06d}",
            "time": created.strftime("%d/%m/%Y %H:%M") if created else "",
            "student_name": p.enrollment.student.full_name,
            "diploma_name": p.enrollment.diploma.name,
            "concept": _concept(p),
            "due_date": p.due_date,
            "payment_type": p.payment_type,
            "amount": _money(p.amount),
            "surcharge": _money(p.surcharge),
            "total": _money(p.total),
            "status": p.status,
            "cashier_name": cashier_names.get(p.cashier_id, "—"),
        })
    return rows


def _load_payments(db: Session, *filters) -> list[Payment]:
    return (
        db.query(Payment)
        .options(
            joinedload(Payment.enrollment).joinedload(Enrollment.student),
            joinedload(Payment.enrollment).joinedload(Enrollment.diploma),
            joinedload(Payment.receipt),
        )
        .filter(*filters)
        .all()
    )


def _cashier_names(db: Session) -> dict[int, str]:
    return dict(db.query(User.id, User.full_name).all())


class CashierService:

    @staticmethod
    def _register_totals(db: Session, register: CashRegister) -> tuple[Decimal, Decimal]:
        """(total cobrado, cobrado en efectivo) en esta caja. Solo cuenta
        pagos PAGADO (un anulado ya no está en la gaveta), y el arqueo físico
        se compara solo contra el efectivo: un cobro con tarjeta o
        transferencia no está en la gaveta."""
        base = db.query(func.sum(Payment.total)).filter(
            Payment.cash_register_id == register.id,
            Payment.status == "PAGADO",
        )
        collected = base.scalar() or 0
        cash = base.filter(Payment.payment_type == CASH).scalar() or 0
        return _money(collected), _money(cash)

    @staticmethod
    def open_register(db: Session, user, initial_amount) -> CashRegister:
        """Abre la caja diaria. Bloquea si ya hay una abierta."""
        if CashierService.find_open(db, user.id):
            raise HTTPException(status_code=400, detail="Ya tienes una caja abierta. Debes cerrarla antes de abrir una nueva.")
        register = CashRegister(cashier_id=user.id, initial_amount=_money(initial_amount), is_open=True)
        db.add(register)
        db.flush()
        audit_service.record(db, user, "APERTURA_CAJA", "cash_register", register.id,
                             f"Fondo inicial ${_money(initial_amount):.2f}")
        db.commit()
        db.refresh(register)
        return register

    @staticmethod
    def find_open(db: Session, user_id: int) -> Optional[CashRegister]:
        return db.query(CashRegister).filter(
            CashRegister.cashier_id == user_id,
            CashRegister.is_open == True,  # noqa: E712
        ).first()

    @staticmethod
    def verify_active_box(db: Session, user_id: int) -> CashRegister:
        """Todo cobro entra a una caja abierta: si no, ese dinero quedaría
        fuera de todo arqueo."""
        register = CashierService.find_open(db, user_id)
        if not register:
            raise HTTPException(
                status_code=403,
                detail="Operación bloqueada: No hay una caja abierta. Debe abrir la caja diaria para registrar cobros.",
            )
        return register

    @staticmethod
    def current_register_summary(db: Session, user_id: int) -> dict:
        register = CashierService.verify_active_box(db, user_id)
        collected, cash = CashierService._register_totals(db, register)
        initial = _money(register.initial_amount)
        return {
            "id": register.id,
            "initial_amount": initial,
            "collected_amount": collected,
            "cash_amount": cash,
            "non_cash_amount": collected - cash,
            "expected_amount": initial + cash,
            "is_open": True,
            "opened_at": register.opened_at,
        }

    @staticmethod
    def count_cash(cash_count: dict) -> Decimal:
        """Suma el arqueo por denominación: {"20.00": 3, "0.25": 4} = $61.00."""
        total = ZERO
        for denomination, quantity in cash_count.items():
            if denomination not in DENOMINATIONS:
                raise HTTPException(status_code=400, detail=f"Denominación no válida: {denomination}")
            if not isinstance(quantity, int) or quantity < 0:
                raise HTTPException(status_code=400, detail=f"Cantidad no válida para ${denomination}")
            total += Decimal(denomination) * quantity
        return _money(total)

    @staticmethod
    def close_daily_register(db: Session, user, physical_amount=None, explanation: str = None,
                             cash_count: Optional[dict] = None) -> dict:
        """Cierra la caja diaria: compara el efectivo contado con lo que el
        sistema espera (fondo + cobros en efectivo) y exige justificación si
        hay sobrante o faltante."""
        register = CashierService.verify_active_box(db, user.id)
        if cash_count:
            counted = CashierService.count_cash(cash_count)
            if physical_amount is not None and _money(physical_amount) != counted:
                raise HTTPException(status_code=400, detail="El total contado no coincide con el arqueo por denominación")
            physical = counted
        elif physical_amount is not None:
            physical = _money(physical_amount)
        else:
            raise HTTPException(status_code=400, detail="Ingresa el efectivo contado o el arqueo por denominación")

        collected, cash = CashierService._register_totals(db, register)
        expected = _money(register.initial_amount) + cash
        diff = physical - expected
        explanation = (explanation or "").strip() or None
        if diff != 0 and not explanation:
            raise HTTPException(
                status_code=400,
                detail=f"Hay un descuadre de ${diff:.2f}. Es obligatorio ingresar una justificación de auditoría para cerrar caja.",
            )

        register.system_expected_amount = expected
        register.real_physical_amount = physical
        register.difference = diff
        register.audit_explanation = explanation
        register.cash_count = json.dumps(cash_count) if cash_count else None
        register.is_open = False
        # Misma fuente de hora que opened_at (el reloj de la BD, en UTC).
        register.closed_at = func.now()
        audit_service.record(
            db, user, "CIERRE_CAJA", "cash_register", register.id,
            f"Esperado ${expected:.2f} · contado ${physical:.2f} · diferencia ${diff:.2f}"
            + (f" · {explanation}" if explanation else ""),
        )
        db.commit()
        return {
            "register_id": register.id,
            "status": "Caja Cerrada Exitosamente",
            "monto_inicial": _money(register.initial_amount),
            "cobrado_sistema": collected,
            "cobrado_efectivo": cash,
            "cobrado_otros_metodos": collected - cash,
            "esperado_total": expected,
            "reportado_fisico": physical,
            "diferencia": diff,
            "auditoria_nota": explanation if diff != 0 else "Caja cuadrada sin novedades",
        }

    @staticmethod
    def register_report(db: Session, register_id: int, user) -> dict:
        """Reporte de cierre de una caja: cada cobro que entró y los totales
        por concepto y método, para contrastar con el dinero físico."""
        register = db.get(CashRegister, register_id)
        if register is None:
            raise HTTPException(status_code=404, detail="La caja no existe")
        is_admin = user.role.name.upper() in {"ADMIN", "ADMINISTRADOR"}
        if not is_admin and register.cashier_id != user.id:
            raise HTTPException(status_code=403, detail="Solo puedes consultar tus propias cajas")
        payments = _load_payments(db, Payment.cash_register_id == register.id)
        collected, cash = CashierService._register_totals(db, register)
        initial = _money(register.initial_amount)
        names = _cashier_names(db)
        opened = clock.to_local(register.opened_at)
        closed = clock.to_local(register.closed_at)
        return {
            "register_id": register.id,
            "cashier_name": names.get(register.cashier_id, "—"),
            "opened_at": opened.strftime("%d/%m/%Y %H:%M") if opened else None,
            "closed_at": closed.strftime("%d/%m/%Y %H:%M") if closed else None,
            "is_open": register.is_open,
            "initial_amount": initial,
            "collected_amount": collected,
            "cash_amount": cash,
            "expected_amount": initial + cash if register.is_open else _money(register.system_expected_amount),
            "physical_amount": None if register.is_open else _money(register.real_physical_amount),
            "difference": None if register.is_open else _money(register.difference),
            "audit_explanation": register.audit_explanation,
            "cash_count": json.loads(register.cash_count) if register.cash_count else None,
            "summary": summarize_payments(payments),
            "payments": payment_rows(payments, names),
        }

    @staticmethod
    def daily_report(db: Session, day: date, cashier_id: Optional[int] = None) -> dict:
        """Cierre diario general (PDF punto 5): todo lo cobrado ese día, de
        todas las cajas o de un cajero, y cómo cerró cada caja."""
        filters = [Payment.payment_date == day, Payment.status.in_(("PAGADO", "ANULADO"))]
        if cashier_id is not None:
            filters.append(Payment.cashier_id == cashier_id)
        payments = _load_payments(db, *filters)
        begin, end = clock.local_day_bounds_utc(day, day)
        register_filters = [CashRegister.opened_at >= begin, CashRegister.opened_at < end]
        if cashier_id is not None:
            register_filters.append(CashRegister.cashier_id == cashier_id)
        registers = db.query(CashRegister).filter(*register_filters).order_by(CashRegister.opened_at).all()
        names = _cashier_names(db)
        return {
            "date": day,
            "summary": summarize_payments(payments),
            "payments": payment_rows(payments, names),
            "registers": [CashierService._register_row(r, names) for r in registers],
        }

    @staticmethod
    def _register_row(register: CashRegister, names: dict[int, str]) -> dict:
        opened = clock.to_local(register.opened_at)
        closed = clock.to_local(register.closed_at)
        return {
            "id": register.id,
            "cashier_id": register.cashier_id,
            "cashier_name": names.get(register.cashier_id, "—"),
            "opened_at": opened.strftime("%d/%m/%Y %H:%M") if opened else None,
            "closed_at": closed.strftime("%d/%m/%Y %H:%M") if closed else None,
            "initial_amount": _money(register.initial_amount),
            "expected_amount": _money(register.system_expected_amount),
            "physical_amount": _money(register.real_physical_amount),
            "difference": _money(register.difference),
            "is_open": register.is_open,
            "audit_explanation": register.audit_explanation,
        }

    @staticmethod
    def list_registers(db: Session) -> list[dict]:
        names = _cashier_names(db)
        emails = dict(db.query(User.id, User.email).all())
        registers = db.query(CashRegister).order_by(CashRegister.opened_at.desc()).all()
        rows = []
        for register in registers:
            row = CashierService._register_row(register, names)
            row["cashier_email"] = emails.get(register.cashier_id)
            rows.append(row)
        return rows

    @staticmethod
    def monthly_closure(db: Session, year: int, month: int, cashier_id: Optional[int] = None) -> dict:
        """Cierre mensual (PDF punto 5): cobros del mes por día y por
        concepto, cajas cerradas y descuadres. Los días son de calendario de
        El Salvador, no de UTC."""
        first = date(year, month, 1)
        last = date(year, month, monthrange(year, month)[1])
        begin, end = clock.local_day_bounds_utc(first, last)
        register_filter = [
            CashRegister.closed_at >= begin,
            CashRegister.closed_at < end,
            CashRegister.is_open == False,  # noqa: E712
        ]
        payment_filter = [
            Payment.payment_date >= first,
            Payment.payment_date <= last,
            Payment.status.in_(("PAGADO", "ANULADO")),
        ]
        if cashier_id is not None:
            register_filter.append(CashRegister.cashier_id == cashier_id)
            payment_filter.append(Payment.cashier_id == cashier_id)

        registers = db.query(CashRegister).filter(*register_filter).order_by(CashRegister.closed_at).all()
        payments = _load_payments(db, *payment_filter)
        summary = summarize_payments(payments)
        by_day: dict[date, dict] = OrderedDict()
        for payment in sorted(payments, key=lambda p: p.payment_date):
            if payment.status != "PAGADO":
                continue
            day = by_day.setdefault(payment.payment_date, {"date": payment.payment_date, "total": ZERO, "cash": ZERO})
            day["total"] += _money(payment.total)
            if payment.payment_type == CASH:
                day["cash"] += _money(payment.total)
        names = _cashier_names(db)
        return {
            "periodo": f"{year}-{month:02d}",
            "cajas_cerradas": len(registers),
            "total_cobrado_mes": summary["total"],
            "total_efectivo_mes": summary["cash_total"],
            "total_esperado_cajas": sum((_money(r.system_expected_amount) for r in registers), ZERO),
            "total_efectivo_contado": sum((_money(r.real_physical_amount) for r in registers), ZERO),
            "total_descuadres_mes": sum((_money(r.difference) for r in registers), ZERO),
            "summary": summary,
            "by_day": list(by_day.values()),
            "registers": [CashierService._register_row(r, names) for r in registers],
            "mensaje": f"Cierre mensual completado. Cobrado en pagos: ${summary['total']:.2f}",
        }
