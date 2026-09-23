import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.auth.jwt_handler import create_access_token
from pydantic import BaseModel, Field, field_validator

from app.auth.dependencies import get_current_user
from app.auth.security import hash_password, verify_password
from app.core import validators
from app.core.rate_limit import register_failure, register_success, seconds_until_retry
from app.database.database import get_db
from app.models.user import User
from app.schemas.auth_schema import LoginRequest, TokenResponse
from app.services.payment_service import PaymentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    email = str(credentials.email).lower()

    wait = seconds_until_retry(email)
    if wait > 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Demasiados intentos fallidos. Intenta de nuevo en {wait // 60 + 1} minuto(s).",
        )

    user = db.query(User).filter(User.email == email).first()

    if not user or not user.is_active or not verify_password(credentials.password, user.password):
        register_failure(email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    register_success(email)

    # Mejor esfuerzo: el backend gratuito no puede "despertar solo" a diario
    # para revisar vencimientos próximos, así que se aprovecha cada login
    # para hacerlo. Nunca debe bloquear el inicio de sesión si falla.
    try:
        PaymentService.send_due_reminders(db)
    except Exception:
        logger.exception("No se pudieron procesar los recordatorios de pago próximos")

    access_token = create_access_token(data={
        "sub": user.email,
        "user_id": user.id,
        "role": user.role.name,
    })
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role.name,
        "user_id": user.id,
        "email": user.email,
    }


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(max_length=128)

    @field_validator("new_password")
    @classmethod
    def _password(cls, v):
        return validators.password(v)


@router.post("/change-password")
def change_password(
    data: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cualquier usuario (admin o cajero) cambia su propia contraseña."""
    if not verify_password(data.current_password, current_user.password):
        raise HTTPException(status_code=400, detail="La contraseña actual no es correcta")
    if data.current_password == data.new_password:
        raise HTTPException(status_code=400, detail="La nueva contraseña debe ser distinta de la actual")
    # current_user viene de la sesión de get_current_user (otra sesión):
    # se vuelve a leer aquí para que el commit de esta sesión lo guarde.
    user = db.get(User, current_user.id)
    user.password = hash_password(data.new_password)
    db.commit()
    return {"message": "Contraseña actualizada"}
