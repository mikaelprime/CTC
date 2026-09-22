from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.schedule_schema import (ScheduleCreate, ScheduleUpdate, ScheduleResponse)
from app.services.schedule_service import (
    list_schedules,
    create_schedule,
    update_schedule,
    delete_schedule,
)
from app.auth.dependencies import get_current_user

router = APIRouter(
    prefix="/schedules",
    tags=["Schedules"],
    dependencies=[Depends(get_current_user)]
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

@router.put("/{schedule_id}", response_model=ScheduleResponse)
def edit_schedule(
    schedule_id: int,
    schedule: ScheduleUpdate,
    db: Session = Depends(get_db)
):
    updated = update_schedule(db, schedule_id, schedule)

    if not updated:
        raise HTTPException(404, "Horario no encontrado")

    return updated

@router.delete("/{schedule_id}")
def remove_schedule(
    schedule_id: int,
    db: Session = Depends(get_db)
):
    deleted = delete_schedule(db, schedule_id)

    if not deleted:
        raise HTTPException(404, "Horario no encontrado")

    return {"message": "Horario eliminado correctamente"}