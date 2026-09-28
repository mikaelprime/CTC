from sqlalchemy.orm import Session
from app.models.schedule import Schedule
from app.schemas.schedule_schema import ScheduleCreate, ScheduleUpdate

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

def update(db: Session, schedule_id: int, schedule: ScheduleUpdate):
    db_schedule = get_by_id(db, schedule_id)

    if not db_schedule:
        return None

    data = schedule.model_dump(exclude_unset=True)

    for key, value in data.items():
        setattr(db_schedule, key, value)

    db.commit()
    db.refresh(db_schedule)

    return db_schedule

def delete(db: Session, schedule_id: int):
    db_schedule = get_by_id(db, schedule_id)

    if not db_schedule:
        return None

    db.delete(db_schedule)
    db.commit()

    return db_schedule