from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.auth.jwt_handler import verify_token
from app.repositories.user_repository import get_user_by_email
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user_allow_temporary_password(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"}
    )

    payload = verify_token(token)

    if payload is None:
        raise credentials_exception

    email = payload.get("sub")

    if email is None:
        raise credentials_exception

    user = get_user_by_email(db, email)

    if user is None or not user.is_active:
        raise credentials_exception

    return user


def get_current_user(user: User = Depends(get_current_user_allow_temporary_password)) -> User:
    """Usuario de la sesión. Con una contraseña temporal (creada o
    restablecida por el administrador) solo puede cambiarla: la API rechaza
    todo lo demás hasta que lo haga."""
    if user.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debes cambiar tu contraseña temporal antes de continuar",
        )
    return user

def require_roles(*allowed_roles: str):

    def dependency(current_user: User = Depends(get_current_user)) -> User:

        allowed = {role.upper() for role in allowed_roles}
        if current_user.role.name.upper() not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para realizar esta acción"
            )

        return current_user

    return dependency


# Acciones que cambian catálogos, borran datos o tocan dinero ya cobrado:
# antes solo se escondían en el menú del escritorio, pero la API las
# aceptaba de cualquier usuario con sesión (p. ej. un cajero podía borrar
# pagos llamando a DELETE /payments/{id}).
require_admin = require_roles("ADMIN", "ADMINISTRADOR")
