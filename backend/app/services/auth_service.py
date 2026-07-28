from sqlalchemy.orm import Session
from app.repositories.user_repository import get_user_by_email
from app.auth.security import verify_password
from app.auth.jwt_handler import create_access_token

def login(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)

    if not user:
        return None

    if not verify_password(password, user.password):
        return None

    token = create_access_token(
        {
            "sub": user.email,
            "role": user.role.name,
            "user_id": user.id
        }
    )
    return token