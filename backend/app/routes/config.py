from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/config", tags=["Configuración"])

class ConfigUpdate(BaseModel):
    institution_name: str = "CTC El Salvador"
    late_fee: float = 3.00
    payment_cycle_days: int = 28
    alert_days_before: int = 7

# Variable global con los parámetros por defecto del proyecto CTC
app_config = {
    "institution_name": "CTC El Salvador",
    "late_fee": 3.00,             # Recargo fijo de $3.00 por mora
    "payment_cycle_days": 28,      # Ciclo estricto de 28 días
    "alert_days_before": 7         # Alerta de cobro 7 días antes del vencimiento
}

@router.get("/")
def get_config():
    """Retorna los parámetros institucionales globales de CTC El Salvador."""
    return app_config

@router.put("/")
def update_config(data: ConfigUpdate):
    """Permite al administrador actualizar las políticas de cobro y recargos."""
    global app_config
    app_config["institution_name"] = data.institution_name
    app_config["late_fee"] = data.late_fee
    app_config["payment_cycle_days"] = data.payment_cycle_days
    app_config["alert_days_before"] = data.alert_days_before
    return {
        "status": "Configuración actualizada con éxito",
        "config": app_config
    }