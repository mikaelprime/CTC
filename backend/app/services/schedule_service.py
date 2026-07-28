from sqlalchemy.orm import Session
from app.repositories import schedule_repository
from app.schemas.schedule_schema import ScheduleCreate

def list_schedules(db: Session):
    return schedule_repository.get_all(db)

def create_schedule(db: Session, schedule: ScheduleCreate):
    return schedule_repository.create(db, schedule)