from datetime import date
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, ConfigDict

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
    pass

class PaymentUpdate(BaseModel):
    status: Optional[str] = None
    surcharge: Optional[Decimal] = None
    cash_received: Optional[Decimal] = None
    change: Optional[Decimal] = None
    observations: Optional[str] = None

class PaymentResponse(PaymentBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class PaymentAdvanceCreate(BaseModel):
    enrollment_id: int
    months: int
    payment_date: date
    payment_type: str
    cash_received: Optional[Decimal] = None
    change: Optional[Decimal] = None
    observations: Optional[str] = None