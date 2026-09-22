from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class CashierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    birth_date: date
    is_active: bool
    created_at: datetime
