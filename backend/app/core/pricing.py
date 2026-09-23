"""Tarifario institucional fijo de CTC El Salvador (ver propuesta del
proyecto). No depende del diplomado: cualquier estudiante, en cualquier
programa, elige un tipo de matrícula y un plan de colegiatura, y el precio
sale de aquí — no de un campo editable por diplomado.
"""

from decimal import Decimal
from typing import Dict

REGISTRATION_TYPES: Dict[str, Decimal] = {
    "COMPLETA": Decimal("20.00"),
    "PROMO": Decimal("10.00"),
    "GRATIS": Decimal("0.00"),
}

REGISTRATION_LABELS: Dict[str, str] = {
    "COMPLETA": "Matrícula completa",
    "PROMO": "Promo-Matrícula 50% OFF",
    "GRATIS": "Matrícula gratis",
}

TUITION_PLANS: Dict[str, Decimal] = {
    "GRUPAL": Decimal("25.00"),
    "PRIVADO": Decimal("55.00"),
    "ONLINE": Decimal("70.00"),
}

TUITION_LABELS: Dict[str, str] = {
    "GRUPAL": "Plan Grupal",
    "PRIVADO": "Plan Privado",
    "ONLINE": "Plan On-line",
}
