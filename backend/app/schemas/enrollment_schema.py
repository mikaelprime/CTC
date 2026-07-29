from datetime import date
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.student_schema import StudentSimple
from app.schemas.diploma_schema import DiplomaSimple
from app.schemas.schedule_schema import ScheduleSimple

class EnrollmentBase(BaseModel):
    student_id: int
    diploma_id: int
    schedule_id: int

    enrollment_date: date
    start_date: date
    end_date: date

    status: Optional[str] = "ACTIVA"
    observations: Optional[str] = None

class EnrollmentCreate(EnrollmentBase):
    pass

class EnrollmentUpdate(BaseModel):
    status: Optional[str] = None
    observations: Optional[str] = None

class EnrollmentResponse(EnrollmentBase):
    id: int

    student: StudentSimple
    diploma: DiplomaSimple
    schedule: ScheduleSimple

    model_config = ConfigDict(from_attributes=True)