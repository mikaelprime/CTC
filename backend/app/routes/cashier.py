from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database.database import get_db
from app.auth.dependencies import get_current_user, require_roles
from app.models.cash_register import CashRegister
from app.models.user import User
from app.services.cashier_service import CashierService

router = APIRouter(
    prefix="/cashier",
    tags=["cashier"],
    dependencies=[Depends(get_current_user)],
)

@router.get("/registers")
def list_registers(
    db: Session = Depends(get_db),
    _admin=Depends(require_roles("ADMIN", "ADMINISTRADOR")),
):
    rows = db.query(CashRegister, User.full_name, User.email).join(
        User, User.id == CashRegister.cashier_id
    ).order_by(CashRegister.opened_at.desc()).all()
    return [
        {
            "id": register.id,
            "cashier_id": register.cashier_id,
            "cashier_name": full_name,
            "cashier_email": email,
            "initial_amount": float(register.initial_amount or 0),
            "expected_amount": float(register.system_expected_amount or 0),
            "physical_amount": float(register.real_physical_amount or 0),
            "difference": float(register.difference or 0),
            "is_open": register.is_open,
            "opened_at": register.opened_at,
            "closed_at": register.closed_at,
            "audit_explanation": register.audit_explanation,
        }
        for register, full_name, email in rows
    ]


@router.get("/monthly")
def monthly_register(
    year: int,
    month: int,
    cashier_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="El mes debe estar entre 1 y 12")
    role = current_user.role.name.upper()
    if role in {"CAJERO", "CASHIER"}:
        if cashier_id is not None and cashier_id != current_user.id:
            raise HTTPException(status_code=403, detail="Solo puedes consultar tu propio cierre")
        cashier_id = current_user.id
    elif role not in {"ADMIN", "ADMINISTRADOR"}:
        raise HTTPException(status_code=403, detail="No tienes permisos para este reporte")
    return CashierService.monthly_closure(db, year, month, cashier_id)

class RegisterOpen(BaseModel):
    initial_amount: float = 0.0

class RegisterClose(BaseModel):
    physical_amount: float
    explanation: Optional[str] = None

@router.post("/register/open")
def open_register(
    data: RegisterOpen,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("CAJERO", "CASHIER")),
):
    if data.initial_amount < 0:
        raise HTTPException(status_code=400, detail="El fondo inicial no puede ser negativo")
    return CashierService.open_register(db, current_user.id, data.initial_amount)

@router.get("/register/current")
def current_register(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("CAJERO", "CASHIER")),
):
    return CashierService.current_register_summary(db, current_user.id)

@router.post("/register/close")
def close_register(
    data: RegisterClose,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("CAJERO", "CASHIER")),
):
    if data.physical_amount < 0:
        raise HTTPException(status_code=400, detail="El efectivo físico no puede ser negativo")
    return CashierService.close_daily_register(
        db, current_user.id, data.physical_amount, data.explanation
    )

