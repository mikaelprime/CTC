"""Reglas de validación compartidas para que el sistema solo acepte datos
reales: nombres sin números ni signos sueltos, teléfonos y DUI de El
Salvador con formato válido, y fechas/edades posibles.

Cada función recibe el valor crudo y devuelve el valor normalizado, o lanza
ValueError con un mensaje en español; Pydantic lo convierte en un 422 que el
manejador de app.main muestra de forma legible.
"""

import re
from datetime import date
from typing import Optional

_LETTER = "A-Za-zÁÉÍÓÚÜÑáéíóúüñ"
_NAME_RE = re.compile(rf"^[{_LETTER}]+(?:[ '\-][{_LETTER}]+)*$")
_TEXT_RE = re.compile(rf"^[{_LETTER}0-9 .,#°º'/()\-]+$")
_HAS_LETTER = re.compile(rf"[{_LETTER}]")


def _collapse(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def person_name(value: str, label: str = "El nombre", min_words: int = 2) -> str:
    """Solo letras (con tildes/ñ), espacios, apóstrofo y guion; al menos
    `min_words` palabras de 2+ letras (nombre y apellido)."""
    value = _collapse(value or "")
    if not value:
        raise ValueError(f"{label} es obligatorio")
    if len(value) > 150:
        raise ValueError(f"{label} no puede pasar de 150 caracteres")
    if not _NAME_RE.match(value):
        raise ValueError(f"{label} solo puede contener letras y espacios (sin números ni signos)")
    words = [word for word in re.split(r"[ '\-]", value) if word]
    if len(words) < min_words or any(len(word) < 2 for word in words[:min_words]):
        raise ValueError(f"{label} debe incluir nombre y apellido")
    return value


def free_text(value: Optional[str], label: str, min_length: int = 2, max_length: int = 200) -> Optional[str]:
    """Texto como dirección, escolaridad o nombre de un programa: debe tener
    letras (no solo un punto o números) y solo caracteres razonables."""
    if value is None:
        return None
    value = _collapse(value)
    if not value:
        return None
    if len(value) < min_length:
        raise ValueError(f"{label} debe tener al menos {min_length} caracteres")
    if len(value) > max_length:
        raise ValueError(f"{label} no puede pasar de {max_length} caracteres")
    if not _HAS_LETTER.search(value):
        raise ValueError(f"{label} debe contener letras")
    if not _TEXT_RE.match(value):
        raise ValueError(f"{label} contiene caracteres no permitidos")
    return value


def phone(value: Optional[str], label: str = "El teléfono") -> Optional[str]:
    """Teléfono de El Salvador: 8 dígitos que empiezan con 2 (fijo), 6 o 7
    (celular), con o sin guion y con o sin +503. También acepta un número
    internacional con "+" y código de país (8 a 15 dígitos), útil para el
    WhatsApp de un responsable que vive fuera del país. Se guarda como
    ####-#### (o +<dígitos> si es internacional)."""
    if value is None:
        return None
    raw = value.strip()
    if not raw:
        return None
    if re.search(r"[^\d\s\-+()]", raw):
        raise ValueError(f"{label} solo puede contener números (ej. 7777-8888)")
    international = raw.startswith("+")
    digits = re.sub(r"\D", "", raw)
    if international and not digits.startswith("503"):
        if not 8 <= len(digits) <= 15:
            raise ValueError(f"{label} internacional debe tener entre 8 y 15 dígitos")
        return f"+{digits}"
    if len(digits) == 11 and digits.startswith("503"):
        digits = digits[3:]
    if len(digits) != 8 or digits[0] not in "267":
        raise ValueError(f"{label} debe tener 8 dígitos y empezar con 2, 6 o 7 (ej. 7777-8888)")
    return f"{digits[:4]}-{digits[4:]}"


def dui(value: Optional[str], label: str = "El DUI") -> Optional[str]:
    """DUI salvadoreño: 8 dígitos + dígito verificador (########-#). El
    verificador es (10 - Σ dígito_i × (9 - i)) mod 10, i = 0..7."""
    if value is None:
        return None
    raw = value.strip()
    if not raw:
        return None
    if not re.fullmatch(r"\d{8}-?\d", raw):
        raise ValueError(f"{label} debe tener el formato 00000000-0")
    digits = raw.replace("-", "")
    if digits == "0" * 9:
        raise ValueError(f"{label} no es válido")
    total = sum(int(d) * (9 - i) for i, d in enumerate(digits[:8]))
    if (10 - total % 10) % 10 != int(digits[8]):
        raise ValueError(f"{label} no es válido (el dígito verificador no coincide)")
    return f"{digits[:8]}-{digits[8]}"


def age_on(birth_date: date, today: Optional[date] = None) -> int:
    today = today or date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


def birth_date(value: Optional[date], min_age: int, max_age: int, label: str = "La fecha de nacimiento") -> Optional[date]:
    """No puede ser hoy ni en el futuro, y la edad resultante debe estar en
    [min_age, max_age] (p. ej. un cajero que "nació hoy" no es válido)."""
    if value is None:
        return None
    if value >= date.today():
        raise ValueError(f"{label} no puede ser hoy ni una fecha futura")
    age = age_on(value)
    if age < min_age:
        raise ValueError(f"{label} indica {age} años; la edad mínima es {min_age}")
    if age > max_age:
        raise ValueError(f"{label} indica {age} años; la edad máxima es {max_age}")
    return value


def date_in_range(value: Optional[date], label: str, *, past_days: int, future_days: int) -> Optional[date]:
    """Fecha entre hoy - past_days y hoy + future_days."""
    if value is None:
        return None
    today = date.today()
    if (today - value).days > past_days:
        raise ValueError(f"{label} es demasiado antigua (máximo {past_days} días atrás)")
    if (value - today).days > future_days:
        if future_days == 0:
            raise ValueError(f"{label} no puede ser una fecha futura")
        raise ValueError(f"{label} está demasiado lejos en el futuro (máximo {future_days} días)")
    return value
