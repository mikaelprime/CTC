import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.auth.jwt_handler import create_access_token
from pydantic import BaseModel, Field, field_validator

from app.auth.dependencies import get_current_user_allow_temporary_password
from app.auth.security import hash_password, verify_password
from app.core import clock, validators
from app.core.rate_limit import LOCKOUT_SECONDS, MAX_ATTEMPTS, register_failure, register_success, seconds_until_retry
from app.database.database import get_db
from app.models.user import User
from app.schemas.auth_schema import LoginRequest, TokenResponse
from app.services import audit_service
from app.services.payment_service import PaymentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _locked_seconds(user: User | None) -> int:
    """Bloqueo guardado en la cuenta (sobrevive a reinicios del backend)."""
    if user is None or user.locked_until is None:
        return 0
    return max(0, int((clock.to_local(user.locked_until) - clock.now()).total_seconds()))


@router.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    email = str(credentials.email).lower()
    user = db.query(User).filter(User.email == email).first()

    # Dos capas: el contador en memoria (cubre también correos que no
    # existen, para no revelar cuáles sí) y el bloqueo guardado en la
    # cuenta, que no se pierde cuando Render reinicia el servicio.
    wait = max(seconds_until_retry(email), _locked_seconds(user))
    if wait > 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Demasiados intentos fallidos. Intenta de nuevo en {wait // 60 + 1} minuto(s).",
        )

    if not user or not user.is_active or not verify_password(credentials.password, user.password):
        register_failure(email)
        if user is not None:
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            if user.failed_login_attempts >= MAX_ATTEMPTS:
                user.failed_login_attempts = 0
                # En UTC: SQLite guarda las fechas sin zona horaria y se leen como UTC.
                user.locked_until = datetime.now(timezone.utc) + timedelta(seconds=LOCKOUT_SECONDS)
                audit_service.record(db, user, "BLOQUEO_USUARIO", "user", user.id,
                                     f"{MAX_ATTEMPTS} intentos fallidos de inicio de sesión")
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    register_success(email)
    user.failed_login_attempts = 0
    user.locked_until = None
    audit_service.record(db, user, "INICIO_SESION", "user", user.id, user.role.name)
    db.commit()

    # Además del hilo horario y del cron externo, cada login revisa los
    # vencimientos próximos. Nunca debe bloquear el inicio de sesión.
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
        "full_name": user.full_name,
        "must_change_password": user.must_change_password,
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
    current_user: User = Depends(get_current_user_allow_temporary_password),
):
    """Cualquier usuario (admin o cajero) cambia su propia contraseña. Es lo
    único que se puede hacer con una contraseña temporal."""
    if not verify_password(data.current_password, current_user.password):
        raise HTTPException(status_code=400, detail="La contraseña actual no es correcta")
    if data.current_password == data.new_password:
        raise HTTPException(status_code=400, detail="La nueva contraseña debe ser distinta de la actual")
    # current_user viene de la sesión de get_current_user (otra sesión):
    # se vuelve a leer aquí para que el commit de esta sesión lo guarde.
    user = db.get(User, current_user.id)
    user.password = hash_password(data.new_password)
    user.must_change_password = False
    audit_service.record(db, user, "CAMBIO_CONTRASENA", "user", user.id)
    db.commit()
    return {"message": "Contraseña actualizada"}
