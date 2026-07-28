from datetime import time
from pydantic import BaseModel

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