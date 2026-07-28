from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.auth_schema import LoginRequest, TokenResponse
from app.services.auth_service import login

router = APIRouter(
    prefix="/auth",
    tags=["Autenticación"]
)

@router.post(
    "/login",
    response_model=TokenResponse
)
def login_user(
    credentials: LoginRequest,
    db: Session = Depends(get_db)
):

    token = login(
        db,
        credentials.email,
        credentials.password
    )

    if token is None:
        raise HTTPException(
            status_code=401,
            detail="Correo o contraseña incorrectos."
        )

    return {
        "access_token": token,
        "token_type": "bearer"
    }