from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.student import Student
from app.schemas.student_schema import check_student_consistency
from app.services import audit_service


def build_student(db: Session, data: dict, user) -> Student:
    """Valida y agrega (sin commit) un estudiante nuevo. Lo usan el registro
    de estudiantes y el formulario único de matrícula, que lo guarda en la
    misma transacción que la inscripción."""
    try:
        data = check_student_consistency(data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    duplicate = db.query(Student.id).filter(
        func.lower(Student.full_name) == data["full_name"].lower(),
        Student.birth_date == data["birth_date"],
    ).first()
    if duplicate:
        raise HTTPException(
            status_code=409,
            detail=f"Ya existe un estudiante con ese nombre y fecha de nacimiento (#{duplicate.id}). "
                   "Selecciónalo en lugar de registrarlo de nuevo.",
        )
    student = Student(**data)
    db.add(student)
    db.flush()
    audit_service.record(db, user, "REGISTRO_ESTUDIANTE", "student", student.id, student.full_name)
    return student
