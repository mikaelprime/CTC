from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date
from app.database.database import get_db
from app.models.student import Student # Tu modelo actualizado con campos del responsable
from app.models.enrollment import Enrollment
from app.auth.dependencies import get_current_user

router = APIRouter(
    prefix="/students",
    tags=["Estudiantes"],
    dependencies=[Depends(get_current_user)],
)

class StudentCreate(BaseModel):
    full_name: str
    age: Optional[int] = None
    birth_date: Optional[date] = None
    dui: Optional[str] = None
    address: Optional[str] = None
    email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    schooling: Optional[str] = None # Escolaridad (PDF)

    # Campos Obligatorios del Responsable (PDF)
    responsible_name: Optional[str] = None
    responsible_dui: Optional[str] = None
    responsible_kinship: Optional[str] = None # Parentesco (PDF)
    responsible_email: Optional[EmailStr] = None
    responsible_whatsapp: Optional[str] = None

@router.post("/")
def create_student(student: StudentCreate, db: Session = Depends(get_db)):
    db_student = Student(**student.model_dump())
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return db_student

@router.get("/")
def list_students(db: Session = Depends(get_db)):
    return db.query(Student).all()


@router.get("/{student_id}")
def get_student(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    return student


@router.delete("/{student_id}")
def delete_student(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    has_enrollments = db.query(Enrollment).filter(Enrollment.student_id == student_id).first()
    if has_enrollments:
        raise HTTPException(
            status_code=409,
            detail="No se puede eliminar: el estudiante tiene inscripciones registradas. Elimina esas inscripciones primero.",
        )
    db.delete(student)
    db.commit()
    return {"message": "Estudiante eliminado correctamente"}