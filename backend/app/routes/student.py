from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.student_schema import (StudentCreate, StudentUpdate, StudentResponse)
from app.services import student_service
from app.auth.dependencies import get_current_user

router = APIRouter(
    prefix="/students",
    tags=["Students"],
    dependencies=[Depends(get_current_user)]
)

@router.get("/", response_model=list[StudentResponse])
def get_students(db: Session = Depends(get_db)):
    return student_service.get_students(db)

@router.get("/{student_id}", response_model=StudentResponse)
def get_student(student_id: int, db: Session = Depends(get_db)):
    return student_service.get_student(db, student_id)

@router.post("/", response_model=StudentResponse)
def create_student(
    student: StudentCreate,
    db: Session = Depends(get_db)
):
    return student_service.create_student(db, student)

@router.put("/{student_id}", response_model=StudentResponse)
def update_student(
    student_id: int,
    student: StudentUpdate,
    db: Session = Depends(get_db)
):
    return student_service.update_student(
        db,
        student_id,
        student
    )

@router.delete("/{student_id}")
def delete_student(
    student_id: int,
    db: Session = Depends(get_db)
):
    return student_service.delete_student(
        db,
        student_id
    )