from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import require_roles
from app.auth.security import hash_password
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