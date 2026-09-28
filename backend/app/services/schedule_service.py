from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.enrollment import Enrollment
from app.repositories import schedule_repository
from app.schemas.schedule_schema import ScheduleCreate, ScheduleUpdate

def list_schedules(db: Session):
    return schedule_repository.get_all(db)

def create_schedule(db: Session, schedule: ScheduleCreate):
    return schedule_repository.create(db, schedule)

def update_schedule(db: Session, schedule_id: int, schedule: ScheduleUpdate):
    return schedule_repository.update(db, schedule_id, schedule)

def delete_schedule(db: Session, schedule_id: int):
    has_enrollments = db.query(Enrollment).filter(Enrollment.schedule_id == schedule_id).first()
    if has_enrollments:
        raise HTTPException(
            status_code=409,
            detail="No se puede eliminar: hay estudiantes inscritos en este turno. Elimina esas inscripciones primero.",
        )
    return schedule_repository.delete(db, schedule_id)
