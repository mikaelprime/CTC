from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_admin
from app.core.runtime_config import get_institution_config
from app.database.session import get_db
from app.services import audit_service

router = APIRouter(
    prefix="/config",
    tags=["Configuración"],
    dependencies=[Depends(get_current_user)],
)

_MONEY = dict(ge=0, le=10000, max_digits=10, decimal_places=2)


class ConfigUpdate(BaseModel):
    institution_name: str = Field("CTC El Salvador", min_length=1, max_length=150)
    late_fee: Decimal = Field(Decimal("3.00"), **_MONEY)
    # Un ciclo de 0 días (o negativo) rompería el cálculo de vencimientos.
    payment_cycle_days: int = Field(28, ge=1, le=365)
    alert_days_before: int = Field(7, ge=0, le=60)
    # Tarifario (PDF punto 3). La matrícula gratis siempre es $0.00.
    registration_full_fee: Decimal = Field(Decimal("20.00"), **_MONEY)
    registration_promo_fee: Decimal = Field(Decimal("10.00"), **_MONEY)
    tuition_group_fee: Decimal = Field(Decimal("25.00"), **_MONEY)
    tuition_private_fee: Decimal = Field(Decimal("55.00"), **_MONEY)
    tuition_online_fee: Decimal = Field(Decimal("70.00"), **_MONEY)


_FIELDS = tuple(ConfigUpdate.model_fields)


def _as_dict(config) -> dict:
    data = {field: getattr(config, field) for field in _FIELDS}
    for field, value in data.items():
        if isinstance(value, Decimal) or field.endswith("_fee"):
            data[field] = float(value)
    return data


@router.get("/")
def get_config(db: Session = Depends(get_db)):
    """Parámetros institucionales: políticas de cobro y tarifario."""
    return _as_dict(get_institution_config(db))


@router.put("/")
def update_config(data: ConfigUpdate, db: Session = Depends(get_db), admin=Depends(require_admin)):
    """El administrador actualiza las políticas de cobro, recargos y tarifas.
    Cada cambio queda en la bitácora con el valor anterior y el nuevo."""
    config = get_institution_config(db)
    changes = []
    for field in _FIELDS:
        new = getattr(data, field)
        old = getattr(config, field)
        if (Decimal(str(old)) != new) if isinstance(new, Decimal) else (old != new):
            changes.append(f"{field}: {old} → {new}")
            setattr(config, field, new)
    if changes:
        audit_service.record(db, admin, "CAMBIO_CONFIGURACION", "institution_config", 1, "; ".join(changes))
    db.commit()
    db.refresh(config)
    return {
        "status": "Configuración actualizada con éxito",
        "config": _as_dict(config),
    }
