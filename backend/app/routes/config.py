from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_roles
from app.core.runtime_config import get_institution_config
from app.database.session import get_db

router = APIRouter(
    prefix="/config",
    tags=["Configuración"],
    dependencies=[Depends(get_current_user)],
)

class ConfigUpdate(BaseModel):
    institution_name: str = "CTC El Salvador"
    late_fee: float = 3.00
    payment_cycle_days: int = 28
    alert_days_before: int = 7


def _as_dict(config) -> dict:
    return {
        "institution_name": config.institution_name,
        "late_fee": float(config.late_fee),
        "payment_cycle_days": config.payment_cycle_days,
        "alert_days_before": config.alert_days_before,
    }


@router.get("/")
def get_config(db: Session = Depends(get_db)):
    """Retorna los parámetros institucionales globales de CTC El Salvador."""
    return _as_dict(get_institution_config(db))


@router.put("/")
def update_config(
    data: ConfigUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(require_roles("ADMIN", "ADMINISTRADOR")),
):
    """Permite al administrador actualizar las políticas de cobro y recargos."""
    config = get_institution_config(db)
    config.institution_name = data.institution_name
    config.late_fee = data.late_fee
    config.payment_cycle_days = data.payment_cycle_days
    config.alert_days_before = data.alert_days_before
    db.commit()
    db.refresh(config)
    return {
        "status": "Configuración actualizada con éxito",
        "config": _as_dict(config),
    }
