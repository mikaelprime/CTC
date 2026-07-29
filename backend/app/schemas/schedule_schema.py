from datetime import time
from pydantic import BaseModel
from pydantic.config import ConfigDict

class ScheduleCreate(BaseModel):

    name: str

    start_time: time

    end_time: time

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