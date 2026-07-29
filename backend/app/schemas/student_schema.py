from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, EmailStr
from pydantic.config import ConfigDict

class StudentBase(BaseModel):
    full_name: str
    birth_date: date
    email: EmailStr
    phone: str
    address: str
    education_level: str

    guardian_name: str
    guardian_dui: str
    guardian_relationship: str

    guardian_email: Optional[EmailStr] = None
    guardian_whatsapp: Optional[str] = None

    observations: Optional[str] = None

class StudentCreate(StudentBase):
    pass

class StudentUpdate(BaseModel):
    full_name: Optional[str] = None
    birth_date: Optional[date] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    education_level: Optional[str] = None

    guardian_name: Optional[str] = None
    guardian_dui: Optional[str] = None
    guardian_relationship: Optional[str] = None

    guardian_email: Optional[EmailStr] = None
    guardian_whatsapp: Optional[str] = None

    observations: Optional[str] = None

    is_active: Optional[bool] = None

class StudentResponse(StudentBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }

class StudentSimple(BaseModel):
        id: int
        full_name: str

        model_config = ConfigDict(from_attributes=True)