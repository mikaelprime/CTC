"""Acceso a la fila única de políticas institucionales (institution_config).

Antes esto era un diccionario en memoria: se perdía cada vez que el proceso
se reiniciaba, algo frecuente en el free tier de Render (el servicio se
duerme y se despierta solo). Ahora vive en la base de datos.
"""

from sqlalchemy.orm import Session

from app.models.institution_config import InstitutionConfig

_DEFAULTS = {
    "institution_name": "CTC El Salvador",
    "late_fee": 3.00,
    "payment_cycle_days": 28,
    "alert_days_before": 7,
}


def get_institution_config(db: Session) -> InstitutionConfig:
    config = db.query(InstitutionConfig).filter(InstitutionConfig.id == 1).first()
    if config is None:
        # No debería pasar (la migración inserta la fila), pero si alguien
        # corrió el proyecto sin migraciones o la borró a mano, se recrea
        # con los valores por defecto en vez de fallar.
        config = InstitutionConfig(id=1, **_DEFAULTS)
        db.add(config)
        db.commit()
        db.refresh(config)
    return config
