from pydantic import BaseModel, EmailStr

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    user_id: int
    email: EmailStr
    full_name: str
    # Contraseña temporal: el escritorio pide cambiarla antes de continuar.
    must_change_password: bool = False
