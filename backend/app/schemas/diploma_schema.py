from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from pydantic.config import ConfigDict

class DiplomaBase(BaseModel):
    name: str
    description: Optional[str] = None
    duration_months: int
    registration_fee: int
    monthly_fee: int
    active: bool = True

class DiplomaCreate(DiplomaBase):
    pass

class DiplomaUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    duration_months: Optional[int] = None
    registration_fee: Optional[int] = None
    monthly_fee: Optional[int] = None
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