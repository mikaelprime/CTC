from datetime import date
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.core import validators

PAYMENT_TYPES = ("Efectivo", "Tarjeta", "Transferencia")


def _payment_type(v):
    if v not in PAYMENT_TYPES:
        raise ValueError(f"El método de pago debe ser uno de: {', '.join(PAYMENT_TYPES)}")
    return v


class PaymentResponse(BaseModel):
    id: int
    enrollment_id: int
    receipt_id: Optional[int] = None
    cash_register_id: Optional[int] = None
    cashier_id: Optional[int] = None
    kind: str = "COLEGIATURA"
    payment_date: date
    due_date: date
    amount: Decimal
    surcharge: Decimal = Decimal("0.00")
    total: Decimal
    payment_type: str
    status: str
    cash_received: Optional[Decimal] = None
    change: Optional[Decimal] = None
    observations: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PaymentVoid(BaseModel):
    reason: str

    @field_validator("reason")
    @classmethod
    def _reason(cls, v):
        cleaned = validators.free_text(v, "El motivo de anulación", min_length=5, max_length=200)
        if cleaned is None:
            raise ValueError("El motivo de anulación es obligatorio")
        return cleaned


class PaymentCollectCreate(BaseModel):
    """Cobro de colegiatura (PDF punto 2). La fecha del cobro la pone el
    servidor (hora de El Salvador), no la computadora del cajero."""

    enrollment_id: int
    payment_type: str = "Efectivo"
    # "Efectivo:" (PDF punto 4). Con tarjeta o transferencia no se usa.
    cash_received: Optional[Decimal] = Field(None, ge=0, le=100000)
    # Cuotas a pagar de una vez (pago adelantado), hasta las que le quedan.
    months: int = Field(1, ge=1, le=12)
    observations: Optional[str] = Field(None, max_length=500)
    # PDF (mejora recomendada): "Muestra una opción para aplicar el recargo".
    apply_late_fee: bool = True

    @field_validator("payment_type")
    @classmethod
    def _type(cls, v):
        return _payment_type(v)


class PaymentCollectResponse(BaseModel):
    receipt_id: int
    receipt_number: str
    payment_ids: list[int]
    enrollment_id: int
    months_paid: int
    amount: Decimal
    surcharge: Decimal
    total: Decimal
    payment_type: str
    cash_received: Decimal
    change: Decimal
    first_due_date: date
    next_payment_date: Optional[date] = None
    installments_paid: int
    installments_total: int
    late: bool
