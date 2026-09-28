from datetime import date, timedelta
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.core import validators
from app.core.pricing import REGISTRATION_TYPES, TUITION_PLANS
from app.schemas.payment_schema import _payment_type
from app.schemas.student_schema import StudentCreate, StudentSimple
from app.schemas.diploma_schema import DiplomaSimple
from app.schemas.schedule_schema import ScheduleSimple


def _observations(v):
    if v is None or not v.strip():
        return None
    if len(v) > 500:
        raise ValueError("Las observaciones no pueden pasar de 500 caracteres")
    return v.strip()


class EnrollmentCreate(BaseModel):
    """Datos de matrícula (PDF, página 2). El estudiante puede ser uno ya
    registrado (`student_id`) o uno nuevo (`student`): así el cajero registra
    todo en un solo formulario y se guarda en una sola transacción."""

    student_id: Optional[int] = None
    student: Optional[StudentCreate] = None
    diploma_id: int
    schedule_id: int

    enrollment_date: date
    # Fecha de inicio de clases: el primer cobro de colegiatura y todos los
    # siguientes (cada 28 días) se calculan desde aquí.
    start_date: date

    # Ver app.core.pricing: COMPLETA/PROMO/GRATIS y GRUPAL/PRIVADO/ONLINE.
    registration_type: str = "COMPLETA"
    tuition_plan: str = "GRUPAL"
    observations: Optional[str] = None

    # Cobro de la matrícula: "Efectivo:" con el que paga; el sistema calcula
    # el cambio (PDF punto 4). Si no se envía, se asume pago exacto.
    payment_type: str = "Efectivo"
    cash_received: Optional[Decimal] = Field(None, ge=0, le=100000)

    @field_validator("enrollment_date")
    @classmethod
    def _enrollment_date(cls, v):
        # No se matricula en el futuro; se permite registrar hasta un año
        # atrás (p. ej. al pasar al sistema matrículas hechas en papel).
        return validators.date_in_range(v, "La fecha de matrícula", past_days=365, future_days=0)

    @field_validator("registration_type")
    @classmethod
    def _registration_type(cls, v):
        if v not in REGISTRATION_TYPES:
            raise ValueError(f"Tipo de matrícula inválido: {v}")
        return v

    @field_validator("tuition_plan")
    @classmethod
    def _tuition_plan(cls, v):
        if v not in TUITION_PLANS:
            raise ValueError(f"Plan de colegiatura inválido: {v}")
        return v

    @field_validator("payment_type")
    @classmethod
    def _type(cls, v):
        return _payment_type(v)

    @field_validator("observations")
    @classmethod
    def _observations(cls, v):
        return _observations(v)

    @model_validator(mode="after")
    def _checks(self):
        if (self.student_id is None) == (self.student is None):
            raise ValueError("Indica un estudiante registrado o los datos de un estudiante nuevo (solo uno)")
        if self.start_date < self.enrollment_date - timedelta(days=90):
            raise ValueError("La fecha de inicio de clases no puede ser más de 90 días anterior a la matrícula")
        if self.start_date > self.enrollment_date + timedelta(days=365):
            raise ValueError("La fecha de inicio de clases no puede ser más de un año después de la matrícula")
        return self


class EnrollmentUpdate(BaseModel):
    """Cambios permitidos a una inscripción existente. El programa no se
    cambia (se anula y se crea otra) y el estado lo maneja el sistema."""

    schedule_id: Optional[int] = None
    tuition_plan: Optional[str] = None
    start_date: Optional[date] = None
    observations: Optional[str] = None

    @field_validator("tuition_plan")
    @classmethod
    def _tuition_plan(cls, v):
        if v is not None and v not in TUITION_PLANS:
            raise ValueError(f"Plan de colegiatura inválido: {v}")
        return v

    @field_validator("observations")
    @classmethod
    def _observations(cls, v):
        return _observations(v)


class EnrollmentCancel(BaseModel):
    reason: str = Field(min_length=5, max_length=200)

    @field_validator("reason")
    @classmethod
    def _reason(cls, v):
        cleaned = validators.free_text(v, "El motivo de anulación", min_length=5, max_length=200)
        if cleaned is None:
            raise ValueError("El motivo de anulación es obligatorio")
        return cleaned


class EnrollmentResponse(BaseModel):
    id: int
    student_id: int
    diploma_id: int
    schedule_id: int
    enrollment_date: date
    start_date: date
    end_date: date
    status: str
    registration_type: str
    tuition_plan: str
    observations: Optional[str] = None

    student: StudentSimple
    diploma: DiplomaSimple
    schedule: ScheduleSimple

    # Calculados (no son columnas): situación de las colegiaturas.
    next_payment_date: Optional[date] = None
    installments_total: Optional[int] = None
    installments_paid: Optional[int] = None
    overdue_installments: Optional[int] = None

    # Solo al crear: comprobante de la matrícula para el ticket.
    registration_fee: Optional[Decimal] = None
    receipt_id: Optional[int] = None
    receipt_number: Optional[str] = None
    cash_received: Optional[Decimal] = None
    change: Optional[Decimal] = None

    model_config = ConfigDict(from_attributes=True)
