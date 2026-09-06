from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.payment_schema import (
    PaymentCreate,
    PaymentUpdate,
    PaymentResponse
)
from app.services.payment_service import PaymentService

router = APIRouter(
    prefix="/payments",
    tags=["Payments"]
)

@router.post("/", response_model=PaymentResponse)
def create_payment(
    data: PaymentCreate,
    db: Session = Depends(get_db)
):
    return PaymentService.create(db, data)

@router.get("/", response_model=list[PaymentResponse])
def get_payments(
    db: Session = Depends(get_db)
):
    return PaymentService.get_all(db)

@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment(
    payment_id: int,
    db: Session = Depends(get_db)
):
    return PaymentService.get_by_id(db, payment_id)

@router.put("/{payment_id}", response_model=PaymentResponse)
def update_payment(
    payment_id: int,
    data: PaymentUpdate,
    db: Session = Depends(get_db)
):
    return PaymentService.update(db, payment_id, data)

@router.delete("/{payment_id}")
def delete_payment(
    payment_id: int,
    db: Session = Depends(get_db)
):
    PaymentService.delete(db, payment_id)

    return {
        "message": "Pago eliminado correctamente"
    }