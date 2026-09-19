from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date
from app.database.database import get_db
from app.models.student import Student # Tu modelo actualizado con campos del responsable

router = APIRouter(prefix="/students", tags=["Estudiantes"])

class StudentCreate(BaseModel):
    full_name: str
    age: Optional[int] = None
    birth_date: Optional[date] = None
    dui: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None
    contact_phone: Optional[str] = None
    schooling: Optional[str] = None # Escolaridad (PDF)

    # Campos Obligatorios del Responsable (PDF)
    responsible_name: Optional[str] = None
    responsible_dui: Optional[str] = None
    responsible_kinship: Optional[str] = None # Parentesco (PDF)
    responsible_email: Optional[str] = None
    responsible_whatsapp: Optional[str] = None

@router.post("/")
def create_student(student: StudentCreate, db: Session = Depends(get_db)):
    db_student = Student(**student.dict())
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return {
        "status": "Estudiante y Responsable registrados exitosamente",
        "data": db_student
    }

@router.get("/")
def list_students(db: Session = Depends(get_db)):
    return db.query(Student).all()