from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.session import get_db
from app.services import receipt_service

router = APIRouter(
    prefix="/receipts",
    tags=["Comprobantes"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/{receipt_id}")
def get_receipt(receipt_id: int, db: Session = Depends(get_db)):
    """Datos del ticket de un comprobante (para imprimirlo o reimprimirlo)."""
    return receipt_service.receipt_ticket(db, receipt_service.get_receipt(db, receipt_id))
