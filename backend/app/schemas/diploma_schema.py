from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from pydantic.config import ConfigDict

from app.core import validators


class _DiplomaFields(BaseModel):
    @field_validator("name", check_fields=False)
    @classmethod
    def _name(cls, v):
        if v is None:
            return v
        cleaned = validators.free_text(v, "El nombre del programa", min_length=3, max_length=150)
        if cleaned is None:
            raise ValueError("El nombre del programa es obligatorio")
        return cleaned

    @field_validator("description", check_fields=False)
    @classmethod
    def _description(cls, v):
        return validators.free_text(v, "La descripción", min_length=3, max_length=500)


class DiplomaBase(_DiplomaFields):
    name: str
    description: Optional[str] = None
    duration_months: int = Field(ge=1, le=36)
    registration_fee: int = Field(ge=0, le=1000)
    monthly_fee: int = Field(ge=0, le=1000)
    active: bool = True

class DiplomaCreate(DiplomaBase):
    pass

class DiplomaUpdate(_DiplomaFields):
    name: Optional[str] = None
    description: Optional[str] = None
    duration_months: Optional[int] = Field(None, ge=1, le=36)
    registration_fee: Optional[int] = Field(None, ge=0, le=1000)
    monthly_fee: Optional[int] = Field(None, ge=0, le=1000)
    active: Optional[bool] = None

class DiplomaResponse(DiplomaBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }

class DiplomaSimple(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)