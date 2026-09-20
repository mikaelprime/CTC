from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.payment_schema import (
    PaymentCreate,
    PaymentUpdate,
    PaymentResponse,
    PaymentAdvanceCreate
    ,PaymentCollectCreate, PaymentCollectResponse
)
from app.services.payment_service import PaymentService
from app.auth.dependencies import get_current_user
from app.services.cashier_service import CashierService

router = APIRouter(
    prefix="/payments",
    tags=["Payments"],
    dependencies=[Depends(get_current_user)]
)

@router.post("/", response_model=PaymentResponse)
def create_payment(
    data: PaymentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    cashier_id = None
    if current_user.role.name.upper() in {"CAJERO", "CASHIER"}:
        CashierService.verify_active_box(db, current_user.id)
        cashier_id = current_user.id
    return PaymentService.create(db, data, cashier_id=cashier_id)

@router.post("/advance", response_model=list[PaymentResponse])
def create_advance_payment(
    data: PaymentAdvanceCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    cashier_id = None
    if current_user.role.name.upper() in {"CAJERO", "CASHIER"}:
        CashierService.verify_active_box(db, current_user.id)
        cashier_id = current_user.id
    return PaymentService.create_advance(db, data, cashier_id=cashier_id)


@router.post("/collect", response_model=PaymentCollectResponse)
def collect_payment(
    data: PaymentCollectCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    cashier_id = None
    if current_user.role.name.upper() in {"CAJERO", "CASHIER"}:
        CashierService.verify_active_box(db, current_user.id)
        cashier_id = current_user.id
    return PaymentService.collect(db, data, cashier_id=cashier_id)


@router.get("/next/{enrollment_id}")
def next_payment(enrollment_id: int, db: Session = Depends(get_db)):
    return PaymentService.next_payment_info(db, enrollment_id)

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