from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy.orm import Session

from app.auth.dependencies import require_roles
from app.auth.security import hash_password
from app.core import validators
from app.database.session import get_db
from app.models.role import Role
from app.models.user import User
from app.schemas.user_schema import CashierResponse

router = APIRouter(prefix="/users", tags=["Usuarios"])


class CashierCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    birth_date: date

    @field_validator("full_name")
    @classmethod
    def _full_name(cls, v):
        return validators.person_name(v, "El nombre del cajero")

    @field_validator("birth_date")
    @classmethod
    def _birth_date(cls, v):
        # Un cajero es un empleado: debe ser mayor de edad (y no "nacer hoy").
        return validators.birth_date(v, min_age=18, max_age=80)

    @field_validator("password")
    @classmethod
    def _password(cls, v):
        return validators.password(v)


class CashierStatusUpdate(BaseModel):
    is_active: bool


class PasswordReset(BaseModel):
    new_password: str = Field(max_length=128)

    @field_validator("new_password")
    @classmethod
    def _password(cls, v):
        return validators.password(v)


@router.post("/cashiers", response_model=CashierResponse, status_code=status.HTTP_201_CREATED)
def create_cashier(
    data: CashierCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("ADMIN", "ADMINISTRADOR")),
):
    email = str(data.email).lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="Ya existe un usuario con ese correo")

    role = db.query(Role).filter(Role.name.ilike("cajero%")) .first()
    if role is None:
        raise HTTPException(status_code=500, detail="El rol CAJERO no está configurado")

    cashier = User(
        full_name=data.full_name.strip(),
        email=email,
        password=hash_password(data.password),
        birth_date=data.birth_date,
        role_id=role.id,
        is_active=True,
    )
    db.add(cashier)
    db.commit()
    db.refresh(cashier)
    return cashier


@router.get("/cashiers", response_model=list[CashierResponse])
def list_cashiers(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("ADMIN", "ADMINISTRADOR")),
):
    return db.query(User).join(Role).filter(Role.name.ilike("cajero%" )).all()


def _get_cashier(db: Session, cashier_id: int) -> User:
    cashier = (
        db.query(User).join(Role)
        .filter(User.id == cashier_id, Role.name.ilike("cajero%"))
        .first()
    )
    if cashier is None:
        raise HTTPException(status_code=404, detail="Cajero no encontrado")
    return cashier


@router.patch("/cashiers/{cashier_id}", response_model=CashierResponse)
def set_cashier_status(
    cashier_id: int,
    data: CashierStatusUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("ADMIN", "ADMINISTRADOR")),
):
    """Desactivar a un cajero que deja de trabajar (no se borra: sus cobros y
    cajas siguen en los reportes). Su sesión deja de servir al instante, porque
    get_current_user rechaza usuarios inactivos."""
    cashier = _get_cashier(db, cashier_id)
    cashier.is_active = data.is_active
    db.commit()
    db.refresh(cashier)
    return cashier


@router.post("/cashiers/{cashier_id}/reset-password")
def reset_cashier_password(
    cashier_id: int,
    data: PasswordReset,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("ADMIN", "ADMINISTRADOR")),
):
    cashier = _get_cashier(db, cashier_id)
    cashier.password = hash_password(data.new_password)
    db.commit()
    return {"message": f"Contraseña de {cashier.full_name} restablecida"}
