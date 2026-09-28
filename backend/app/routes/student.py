from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.models.student import Student
from app.schemas.student_schema import StudentCreate, StudentResponse, StudentUpdate, check_student_consistency
from app.models.enrollment import Enrollment
from app.auth.dependencies import get_current_user, require_admin
from app.services import audit_service, student_service

router = APIRouter(
    prefix="/students",
    tags=["Estudiantes"],
    dependencies=[Depends(get_current_user)],
)


@router.post("/", response_model=StudentResponse)
def create_student(student: StudentCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    db_student = student_service.build_student(db, student.model_dump(), current_user)
    db.commit()
    db.refresh(db_student)
    return db_student


@router.put("/{student_id}", response_model=StudentResponse)
def update_student(
    student_id: int,
    student: StudentUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    db_student = db.query(Student).filter(Student.id == student_id).first()
    if db_student is None:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    changes = student.model_dump(exclude_unset=True)
    if "full_name" in changes and changes["full_name"] is None:
        raise HTTPException(status_code=422, detail="El nombre completo es obligatorio")
    # Las reglas que cruzan campos (edad, datos del responsable si es menor)
    # se revisan sobre el registro ya combinado con los cambios.
    merged = {column.name: getattr(db_student, column.name) for column in Student.__table__.columns}
    merged.update(changes)
    if "birth_date" in changes and "age" not in changes:
        merged["age"] = None  # se recalcula desde la nueva fecha
    try:
        merged = check_student_consistency(merged)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    changes["age"] = merged.get("age", db_student.age)
    changed = [key for key, value in changes.items() if getattr(db_student, key) != value and key != "age"]
    for key, value in changes.items():
        setattr(db_student, key, value)
    if changed:
        audit_service.record(db, current_user, "EDICION_ESTUDIANTE", "student", student_id,
                             f"{db_student.full_name}: {', '.join(changed)}")
    db.commit()
    db.refresh(db_student)
    return db_student


@router.get("/", response_model=list[StudentResponse])
def list_students(db: Session = Depends(get_db)):
    return db.query(Student).order_by(Student.full_name).all()


@router.get("/{student_id}", response_model=StudentResponse)
def get_student(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    return student


@router.delete("/{student_id}")
def delete_student(student_id: int, db: Session = Depends(get_db), current_user=Depends(require_admin)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    has_enrollments = db.query(Enrollment).filter(Enrollment.student_id == student_id).first()
    if has_enrollments:
        raise HTTPException(
            status_code=409,
            detail="No se puede eliminar: el estudiante tiene inscripciones registradas. Elimina esas inscripciones primero.",
        )
    audit_service.record(db, current_user, "ELIMINACION_ESTUDIANTE", "student", student_id, student.full_name)
    db.delete(student)
    db.commit()
    return {"message": "Estudiante eliminado correctamente"}
