from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_admin
from app.core import clock
from app.database.database import get_db
from app.services.cashier_service import CashierService

# Cualquier usuario que reciba dinero (cajero o administrador) abre y cierra
# su propia caja: así todo cobro queda dentro de un arqueo.
router = APIRouter(
    prefix="/cashier",
    tags=["cashier"],
    dependencies=[Depends(get_current_user)],
)


def _is_admin(user) -> bool:
    return user.role.name.upper() in {"ADMIN", "ADMINISTRADOR"}


@router.get("/registers", dependencies=[Depends(require_admin)])
def list_registers(db: Session = Depends(get_db)):
    return CashierService.list_registers(db)


@router.get("/registers/{register_id}/report")
def register_report(register_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Reporte de cierre de una caja (cada cobro y totales por concepto)."""
    return CashierService.register_report(db, register_id, current_user)


@router.get("/daily")
def daily_report(
    day: Optional[date] = None,
    cashier_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Cierre diario (PDF punto 5). Un cajero solo ve lo suyo."""
    if not _is_admin(current_user):
        if cashier_id is not None and cashier_id != current_user.id:
            raise HTTPException(status_code=403, detail="Solo puedes consultar tu propio cierre")
        cashier_id = current_user.id
    return CashierService.daily_report(db, day or clock.today(), cashier_id)


@router.get("/monthly")
def monthly_register(
    year: int,
    month: int,
    cashier_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Cierre mensual (PDF punto 5). Un cajero solo ve lo suyo."""
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="El mes debe estar entre 1 y 12")
    if not _is_admin(current_user):
        if cashier_id is not None and cashier_id != current_user.id:
            raise HTTPException(status_code=403, detail="Solo puedes consultar tu propio cierre")
        cashier_id = current_user.id
    return CashierService.monthly_closure(db, year, month, cashier_id)


class RegisterOpen(BaseModel):
    initial_amount: Decimal = Field(Decimal("0.00"), ge=0, le=100000)


class RegisterClose(BaseModel):
    physical_amount: Optional[Decimal] = Field(None, ge=0, le=1000000)
    # Arqueo por denominación: {"20.00": 3, "1.00": 7, "0.25": 4}.
    cash_count: Optional[dict[str, int]] = None
    explanation: Optional[str] = Field(None, max_length=500)


@router.post("/register/open")
def open_register(data: RegisterOpen, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return CashierService.open_register(db, current_user, data.initial_amount)


@router.get("/register/current")
def current_register(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return CashierService.current_register_summary(db, current_user.id)


@router.post("/register/close")
def close_register(data: RegisterClose, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return CashierService.close_daily_register(
        db, current_user, data.physical_amount, data.explanation, data.cash_count
    )
