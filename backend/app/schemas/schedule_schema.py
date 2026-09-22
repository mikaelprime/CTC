from datetime import time
from typing import Optional
from pydantic import BaseModel
from pydantic.config import ConfigDict

class ScheduleCreate(BaseModel):

    name: str

    start_time: time

    end_time: time

class ScheduleUpdate(BaseModel):

    name: Optional[str] = None

    start_time: Optional[time] = None

    end_time: Optional[time] = None

    active: Optional[bool] = None

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