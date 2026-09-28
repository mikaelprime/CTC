from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.payment_schema import (
    PaymentCollectCreate,
    PaymentCollectResponse,
    PaymentResponse,
    PaymentVoid,
)
from app.services import receipt_service
from app.services.payment_service import PaymentService
from app.auth.dependencies import get_current_user, require_admin
from app.services.cashier_service import CashierService

# Un cobro solo nace de /collect (colegiatura) o de la inscripción
# (matrícula), siempre con su comprobante y dentro de una caja abierta. No
# hay alta "manual" de pagos ni edición o borrado de pagos cobrados: eso
# permitía alterar dinero ya registrado. Un error se corrige anulando.
router = APIRouter(
    prefix="/payments",
    tags=["Payments"],
    dependencies=[Depends(get_current_user)]
)


@router.post("/collect", response_model=PaymentCollectResponse)
def collect_payment(
    data: PaymentCollectCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    register = CashierService.verify_active_box(db, current_user.id)
    return PaymentService.collect(db, data, current_user, register)


@router.get("/next/{enrollment_id}")
def next_payment(enrollment_id: int, db: Session = Depends(get_db)):
    return PaymentService.next_payment_info(db, enrollment_id)


@router.get("/", response_model=list[PaymentResponse])
def get_payments(db: Session = Depends(get_db)):
    return PaymentService.get_all(db)


@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment(payment_id: int, db: Session = Depends(get_db)):
    return PaymentService.get_by_id(db, payment_id)


@router.get("/{payment_id}/ticket")
def payment_ticket(payment_id: int, db: Session = Depends(get_db)):
    """Datos del ticket del cobro al que pertenece el pago (reimpresión)."""
    return receipt_service.payment_ticket(db, payment_id)


@router.post("/{payment_id}/void", response_model=PaymentResponse, dependencies=[Depends(require_admin)])
def void_payment(
    payment_id: int,
    data: PaymentVoid,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return PaymentService.void(db, payment_id, data.reason, current_user)
