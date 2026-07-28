from sqlalchemy.orm import Session
from app.models.schedule import Schedule
from app.schemas.schedule_schema import ScheduleCreate

def get_all(db: Session):
    return db.query(Schedule).all()

def get_by_id(db: Session, schedule_id: int):
    return db.query(Schedule).filter(Schedule.id == schedule_id).first()

def create(db: Session, schedule: ScheduleCreate):
    new_schedule = Schedule(**schedule.model_dump())

    db.add(new_schedule)
    db.commit()
    db.refresh(new_schedule)

    return new_schedule