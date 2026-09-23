from datetime import date, timedelta
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.core import validators
from app.schemas.student_schema import StudentSimple
from app.schemas.diploma_schema import DiplomaSimple
from app.schemas.schedule_schema import ScheduleSimple

class EnrollmentBase(BaseModel):
    student_id: int
    diploma_id: int
    schedule_id: int

    enrollment_date: date
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    status: Optional[str] = "ACTIVA"
    # Ver app.core.pricing: COMPLETA/PROMO/GRATIS y GRUPAL/PRIVADO/ONLINE.
    registration_type: str = "COMPLETA"
    tuition_plan: str = "GRUPAL"
    observations: Optional[str] = None

class EnrollmentCreate(EnrollmentBase):
    # "Efectivo:" con el que se paga la matrícula; el sistema calcula el
    # cambio (PDF punto 4). Si no se envía, se asume pago exacto.
    cash_received: Optional[Decimal] = Field(None, ge=0, le=100000)

    @field_validator("enrollment_date")
    @classmethod
    def _enrollment_date(cls, v):
        # No se matricula en el futuro; se permite registrar hasta un año
        # atrás (p. ej. al pasar al sistema matrículas hechas en papel).
        return validators.date_in_range(v, "La fecha de matrícula", past_days=365, future_days=0)

    @field_validator("observations")
    @classmethod
    def _observations(cls, v):
        if v is None or not v.strip():
            return None
        if len(v) > 500:
            raise ValueError("Las observaciones no pueden pasar de 500 caracteres")
        return v.strip()

    @model_validator(mode="after")
    def _dates(self):
        if self.start_date is not None:
            if self.start_date < self.enrollment_date - timedelta(days=90):
                raise ValueError(
                    "La fecha de inicio de clases no puede ser más de 90 días anterior a la matrícula"
                )
            if self.start_date > self.enrollment_date + timedelta(days=365):
                raise ValueError(
                    "La fecha de inicio de clases no puede ser más de un año después de la matrícula"
                )
        if self.end_date is not None and self.end_date <= (self.start_date or self.enrollment_date):
            raise ValueError("La fecha de fin debe ser posterior a la fecha de inicio")
        return self

class EnrollmentUpdate(BaseModel):
    status: Optional[str] = None
    observations: Optional[str] = None


class EnrollmentCancel(BaseModel):
    reason: str = Field(min_length=5, max_length=200)

    @field_validator("reason")
    @classmethod
    def _reason(cls, v):
        cleaned = validators.free_text(v, "El motivo de anulación", min_length=5, max_length=200)
        if cleaned is None:
            raise ValueError("El motivo de anulación es obligatorio")
        return cleaned

class EnrollmentResponse(EnrollmentBase):
    id: int

    student: StudentSimple
    diploma: DiplomaSimple
    schedule: ScheduleSimple

    # Calculado (no es columna): próximo vencimiento de colegiatura.
    next_payment_date: Optional[date] = None

    # Solo al crear: datos para el ticket de matrícula.
    registration_fee: Optional[Decimal] = None
    cash_received: Optional[Decimal] = None
    change: Optional[Decimal] = None

    model_config = ConfigDict(from_attributes=True)