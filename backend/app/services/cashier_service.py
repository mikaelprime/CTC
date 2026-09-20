from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date
from fastapi import HTTPException
from app.models.cash_register import CashRegister
from app.models.payment import Payment

class CashierService:

    @staticmethod
    def open_register(db: Session, cashier_id: int, initial_amount: float) -> CashRegister:
        """Abre la caja diaria. Bloquea si ya hay una abierta."""
        active_box = db.query(CashRegister).filter(
            CashRegister.cashier_id == cashier_id,
            CashRegister.is_open == True
        ).first()

        if active_box:
            raise HTTPException(status_code=400, detail="Ya tienes una caja abierta. Debes cerrarla antes de abrir una nueva.")

        new_box = CashRegister(
            cashier_id=cashier_id,
            initial_amount=initial_amount,
            is_open=True
        )
        db.add(new_box)
        db.commit()
        db.refresh(new_box)
        return new_box

    @staticmethod
    def verify_active_box(db: Session, cashier_id: int) -> CashRegister:
        """Verifica que exista una caja abierta antes de permitir cobrar."""
        active_box = db.query(CashRegister).filter(
            CashRegister.cashier_id == cashier_id,
            CashRegister.is_open == True
        ).first()

        if not active_box:
            raise HTTPException(
                status_code=403, 
                detail="Operación bloqueada: No hay una caja abierta. Debe abrir la caja diaria para registrar cobros."
            )
        return active_box

    @staticmethod
    def current_register_summary(db: Session, cashier_id: int) -> dict:
        register = CashierService.verify_active_box(db, cashier_id)
        collected = db.query(func.sum(Payment.amount + Payment.surcharge)).filter(
            Payment.cashier_id == cashier_id,
            Payment.status == "PAGADO",
            Payment.created_at >= register.opened_at,
        ).scalar() or 0
        expected = float(register.initial_amount or 0) + float(collected)
        return {
            "id": register.id,
            "initial_amount": float(register.initial_amount or 0),
            "collected_amount": round(float(collected), 2),
            "expected_amount": round(expected, 2),
            "is_open": True,
            "opened_at": register.opened_at,
        }

    @staticmethod
    def close_daily_register(db: Session, cashier_id: int, physical_amount: float, explanation: str = None) -> dict:
        """Cierra la caja diaria y realiza auditoría de sobrantes/faltantes."""
        active_box = CashierService.verify_active_box(db, cashier_id)

        # Suma de pagos procesados hoy en esta caja
        today_payments = db.query(func.sum(Payment.amount + Payment.surcharge)).filter(
            Payment.cashier_id == cashier_id,
            Payment.created_at >= active_box.opened_at
        ).scalar() or 0.0

        expected_total = active_box.initial_amount + float(today_payments)
        diff = round(physical_amount - expected_total, 2)

        # Exigir explicación si hay descuadre (Auditoría)
        if diff != 0.0 and not explanation:
            raise HTTPException(
                status_code=400, 
                detail=f"Hay un descuadre de ${diff:.2f}. Es obligatorio ingresar una justificación de auditoría para cerrar caja."
            )

        active_box.system_expected_amount = expected_total
        active_box.real_physical_amount = physical_amount
        active_box.difference = diff
        active_box.audit_explanation = explanation
        active_box.is_open = False
        active_box.closed_at = datetime.now()

        db.commit()
        return {
            "status": "Caja Cerrada Exitosamente",
            "monto_inicial": active_box.initial_amount,
            "cobrado_sistema": float(today_payments),
            "esperado_total": expected_total,
            "reportado_fisico": physical_amount,
            "diferencia": diff,
            "auditoria_nota": explanation if diff != 0.0 else "Caja cuadrada sin novedades"
        }

    @staticmethod
    def monthly_closure(db: Session, year: int, month: int, cashier_id: int = None) -> dict:
        """Resume cajas cerradas, cobros y descuadres de un mes."""
        register_filter = [
            func.extract('year', CashRegister.closed_at) == year,
            func.extract('month', CashRegister.closed_at) == month,
            CashRegister.is_open == False,
        ]
        payment_filter = [
            func.extract('year', Payment.created_at) == year,
            func.extract('month', Payment.created_at) == month,
        ]
        if cashier_id is not None:
            register_filter.append(CashRegister.cashier_id == cashier_id)
            payment_filter.append(Payment.cashier_id == cashier_id)

        registers = db.query(CashRegister).filter(*register_filter).all()
        collected = db.query(func.sum(Payment.amount + Payment.surcharge)).filter(*payment_filter).scalar() or 0
        physical_total = sum(float(register.real_physical_amount or 0) for register in registers)
        expected_total = sum(float(register.system_expected_amount or 0) for register in registers)
        total_diff = sum(float(register.difference or 0) for register in registers)

        return {
            "periodo": f"{year}-{month:02d}",
            "cajas_cerradas": len(registers),
            "total_cobrado_mes": round(float(collected), 2),
            "total_esperado_cajas": round(expected_total, 2),
            "total_efectivo_contado": round(physical_total, 2),
            "total_descuadres_mes": round(total_diff, 2),
            "mensaje": f"Cierre mensual completado. Cobrado en pagos: ${float(collected):.2f}",
        }