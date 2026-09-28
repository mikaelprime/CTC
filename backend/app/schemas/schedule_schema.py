from datetime import time
from typing import Optional
from pydantic import BaseModel, field_validator, model_validator
from pydantic.config import ConfigDict

from app.core import validators


class ScheduleCreate(BaseModel):

    name: str

    start_time: time

    end_time: time

    @field_validator("name")
    @classmethod
    def _name(cls, v):
        cleaned = validators.free_text(v, "El nombre del turno", min_length=3, max_length=100)
        if cleaned is None:
            raise ValueError("El nombre del turno es obligatorio")
        return cleaned

    @model_validator(mode="after")
    def _times(self):
        if self.end_time <= self.start_time:
            raise ValueError("La hora de fin debe ser posterior a la hora de inicio")
        return self

class ScheduleUpdate(BaseModel):

    name: Optional[str] = None

    start_time: Optional[time] = None

    end_time: Optional[time] = None

    active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def _name(cls, v):
        if v is None:
            return v
        cleaned = validators.free_text(v, "El nombre del turno", min_length=3, max_length=100)
        if cleaned is None:
            raise ValueError("El nombre del turno es obligatorio")
        return cleaned

    @model_validator(mode="after")
    def _times(self):
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValueError("La hora de fin debe ser posterior a la hora de inicio")
        return self

class ScheduleResponse(BaseModel):

    id: int

    name: str

    start_time: time

    end_time: time

    active: bool

class Config:
    from_attributes = True

class ScheduleSimple(BaseModel):
    id: int
    name: str
    start_time: time
    end_time: time

    model_config = ConfigDict(from_attributes=True)