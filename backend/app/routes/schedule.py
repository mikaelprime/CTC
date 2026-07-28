from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.schedule_schema import (ScheduleCreate, ScheduleResponse)
from app.services.schedule_service import (list_schedules, create_schedule)

router = APIRouter(
    prefix="/schedules",
    tags=["Schedules"]
)

@router.get("/", response_model=list[ScheduleResponse])
def get_schedules(db: Session = Depends(get_db)):
    return list_schedules(db)

@router.post("/", response_model=ScheduleResponse)
def add_schedule(
    schedule: ScheduleCreate,
    db: Session = Depends(get_db)
):
    return create_schedule(db, schedule)