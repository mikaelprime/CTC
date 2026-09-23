from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.enrollment_schema import (EnrollmentCancel, EnrollmentCreate, EnrollmentResponse)
from app.services.enrollment_service import EnrollmentService
from app.auth.dependencies import get_current_user, require_admin, require_roles
from app.core.pricing import REGISTRATION_TYPES
from app.services.cashier_service import CashierService

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
    # Igual que en /payments: si un cajero cobra la matrícula debe tener la
    # caja abierta, o esos $20/$10 quedan fuera de todo arqueo.
    if (
        current_user.role.name.upper() in {"CAJERO", "CASHIER"}
        and REGISTRATION_TYPES.get(enrollment.registration_type, 0) > 0
    ):
        CashierService.verify_active_box(db, current_user.id)
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

@router.post("/{enrollment_id}/cancel", response_model=EnrollmentResponse)
def cancel(
    enrollment_id: int,
    data: EnrollmentCancel,
    db: Session = Depends(get_db),
    _admin=Depends(require_roles("ADMIN", "ADMINISTRADOR")),
):
    enrollment = EnrollmentService.cancel(db, enrollment_id, data.reason)
    if not enrollment:
        raise HTTPException(404, "Inscripción no encontrada")
    return enrollment


@router.delete("/{enrollment_id}", dependencies=[Depends(require_admin)])
def delete(
    enrollment_id: int,
    db: Session = Depends(get_db)
):
    enrollment = EnrollmentService.delete(db, enrollment_id)

    if not enrollment:
        raise HTTPException(404, "Inscripción no encontrada")

    return {"message": "Inscripción eliminada correctamente"}