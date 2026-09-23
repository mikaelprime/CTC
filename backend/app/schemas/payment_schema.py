from datetime import date
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.core import validators

PAYMENT_TYPES = ("Efectivo", "Tarjeta", "Transferencia")
PAYMENT_STATUSES = ("PENDIENTE", "PAGADO")


def _payment_type(v):
    if v not in PAYMENT_TYPES:
        raise ValueError(f"El método de pago debe ser uno de: {', '.join(PAYMENT_TYPES)}")
    return v


def _payment_date(v):
    return validators.date_in_range(v, "La fecha de pago", past_days=365, future_days=0)

class PaymentBase(BaseModel):
    enrollment_id: int
    payment_date: date
    due_date: date
    amount: Decimal
    surcharge: Decimal = Decimal("0.00")
    total: Decimal
    payment_type: str
    status: Optional[str] = "PENDIENTE"
    cash_received: Optional[Decimal] = None
    change: Optional[Decimal] = None
    observations: Optional[str] = None

class PaymentCreate(PaymentBase):
    amount: Decimal = Field(ge=0, le=10000)
    surcharge: Decimal = Field(Decimal("0.00"), ge=0, le=1000)

    @field_validator("payment_type")
    @classmethod
    def _type(cls, v):
        return _payment_type(v)

    @field_validator("payment_date")
    @classmethod
    def _date(cls, v):
        return _payment_date(v)

    @field_validator("due_date")
    @classmethod
    def _due(cls, v):
        return validators.date_in_range(v, "La fecha de vencimiento", past_days=730, future_days=730)

    @field_validator("status")
    @classmethod
    def _status(cls, v):
        if v not in PAYMENT_STATUSES:
            raise ValueError(f"El estado debe ser uno de: {', '.join(PAYMENT_STATUSES)}")
        return v

class PaymentUpdate(BaseModel):
    status: Optional[str] = None
    surcharge: Optional[Decimal] = Field(None, ge=0, le=1000)

    @field_validator("status")
    @classmethod
    def _status(cls, v):
        if v is not None and v not in PAYMENT_STATUSES:
            raise ValueError(f"El estado debe ser uno de: {', '.join(PAYMENT_STATUSES)}")
        return v
    cash_received: Optional[Decimal] = None
    change: Optional[Decimal] = None
    observations: Optional[str] = None

class PaymentResponse(PaymentBase):
    id: int
    cashier_id: Optional[int] = None
    kind: str = "COLEGIATURA"
    model_config = ConfigDict(from_attributes=True)

class PaymentAdvanceCreate(BaseModel):
    enrollment_id: int
    months: int = Field(ge=1, le=12)
    payment_date: date
    payment_type: str
    cash_received: Optional[Decimal] = Field(None, ge=0, le=100000)
    change: Optional[Decimal] = None
    observations: Optional[str] = Field(None, max_length=500)

    @field_validator("payment_type")
    @classmethod
    def _type(cls, v):
        return _payment_type(v)

    @field_validator("payment_date")
    @classmethod
    def _date(cls, v):
        return _payment_date(v)


class PaymentCollectCreate(BaseModel):
    enrollment_id: int
    payment_date: date
    payment_type: str = "Efectivo"
    cash_received: Decimal = Field(ge=0, le=100000)
    months: int = 1
    observations: Optional[str] = Field(None, max_length=500)
    # El cajero puede decidir no aplicar el recargo por mora aunque la
    # matrícula esté vencida (ej. una excepción autorizada). True por
    # defecto para no cambiar el comportamiento existente.
    apply_late_fee: bool = True

    @field_validator("payment_type")
    @classmethod
    def _type(cls, v):
        return _payment_type(v)

    @field_validator("payment_date")
    @classmethod
    def _date(cls, v):
        return _payment_date(v)


class PaymentCollectResponse(BaseModel):
    payment_ids: list[int]
    enrollment_id: int
    months_paid: int
    amount: Decimal
    surcharge: Decimal
    total: Decimal
    cash_received: Decimal
    change: Decimal
    first_due_date: date
    next_payment_date: date
    late: bool