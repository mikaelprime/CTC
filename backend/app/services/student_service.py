from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.student import Student
from app.schemas.student_schema import StudentCreate, StudentUpdate
from app.repositories import student_repository

def get_students(db: Session):
    return student_repository.get_all(db)

def get_student(db: Session, student_id: int):
    student = student_repository.get_by_id(db, student_id)

    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estudiante no encontrado"
        )
    db.refresh(student)

    print("========== STUDENT ==========")
    print(student)
    print(student.__dict__)
    print("is_active:", student.is_active)
    print("=============================")

    return student

def create_student(db: Session, student_data: StudentCreate):
    existing_student = student_repository.get_by_email(
        db,
        student_data.email
    )

    if existing_student:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un estudiante con ese correo"
        )

    student = Student(**student_data.model_dump())

    return student_repository.create(db, student)

def update_student(
    db: Session,
    student_id: int,
    student_data: StudentUpdate
):

    student = student_repository.get_by_id(db, student_id)

    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estudiante no encontrado"
        )

    update_data = student_data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(student, key, value)

    return student_repository.update(db, student)

def delete_student(db: Session, student_id: int):
    student = student_repository.get_by_id(db, student_id)

    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estudiante no encontrado"
        )

    student_repository.delete(db, student)

    return {
        "message": "Estudiante eliminado correctamente"
    }