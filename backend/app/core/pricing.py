"""Tarifario institucional de CTC El Salvador (PDF punto 3).

No depende del diplomado: cualquier estudiante, en cualquier programa, elige
un tipo de matrícula y un plan de colegiatura. Los montos viven en
institution_config (los edita el administrador) con estos valores por
defecto: Matrícula $20.00, Promo-Matrícula 50% OFF $10.00, Matrícula gratis
$0.00, Plan Grupal $25.00, Plan Privado $55.00 y Plan On-line $70.00.
"""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.runtime_config import get_institution_config

REGISTRATION_LABELS: dict[str, str] = {
    "COMPLETA": "Matrícula completa",
    "PROMO": "Promo-Matrícula 50% OFF",
    "GRATIS": "Matrícula gratis",
}

TUITION_LABELS: dict[str, str] = {
    "GRUPAL": "Plan Grupal",
    "PRIVADO": "Plan Privado",
    "ONLINE": "Plan On-line",
}

REGISTRATION_TYPES = tuple(REGISTRATION_LABELS)
TUITION_PLANS = tuple(TUITION_LABELS)

# Columna de institution_config que guarda cada precio.
_REGISTRATION_COLUMNS = {"COMPLETA": "registration_full_fee", "PROMO": "registration_promo_fee"}
_TUITION_COLUMNS = {
    "GRUPAL": "tuition_group_fee",
    "PRIVADO": "tuition_private_fee",
    "ONLINE": "tuition_online_fee",
}


def _money(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


def registration_fees(db: Session) -> dict[str, Decimal]:
    config = get_institution_config(db)
    fees = {key: _money(getattr(config, column)) for key, column in _REGISTRATION_COLUMNS.items()}
    fees["GRATIS"] = Decimal("0.00")
    return fees


def tuition_fees(db: Session) -> dict[str, Decimal]:
    config = get_institution_config(db)
    return {key: _money(getattr(config, column)) for key, column in _TUITION_COLUMNS.items()}


def registration_fee(db: Session, registration_type: str) -> Decimal:
    return registration_fees(db)[registration_type]


def tuition_fee(db: Session, tuition_plan: str) -> Decimal:
    return tuition_fees(db).get(tuition_plan, tuition_fees(db)["GRUPAL"])
