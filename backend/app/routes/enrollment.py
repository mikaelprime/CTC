from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.enrollment_schema import (EnrollmentCreate, EnrollmentResponse)
from app.services.enrollment_service import EnrollmentService
from app.auth.dependencies import get_current_user

router = APIRouter(
    prefix="/enrollments",
    tags=["Enrollments"],
    dependencies=[Depends(get_current_user)]
)

@router.post("/", response_model=EnrollmentResponse)
def create_enrollment(
    enrollment: EnrollmentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        return EnrollmentService.create(db, enrollment, cashier_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

@router.get("/", response_model=list[EnrollmentResponse])
def get_all(db: Session = Depends(get_db)):
    return EnrollmentService.get_all(db)

@router.get("/{enrollment_id}", response_model=EnrollmentResponse)
def get_by_id(
    enrollment_id: int,
    db: Session = Depends(get_db)
):
    enrollment = EnrollmentService.get_by_id(db, enrollment_id)

    if not enrollment:
        raise HTTPException(404, "Inscripción no encontrada")

    return enrollment

@router.delete("/{enrollment_id}")
def delete(
    enrollment_id: int,
    db: Session = Depends(get_db)
):
    enrollment = EnrollmentService.delete(db, enrollment_id)

    if not enrollment:
        raise HTTPException(404, "Inscripción no encontrada")

    return {"message": "Inscripción eliminada correctamente"}