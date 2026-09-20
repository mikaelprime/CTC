from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.auth.jwt_handler import create_access_token
from app.auth.security import verify_password
from app.database.database import get_db
from app.models.user import User
from app.schemas.auth_schema import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == str(credentials.email).lower()).first()

    if not user or not user.is_active or not verify_password(credentials.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )

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