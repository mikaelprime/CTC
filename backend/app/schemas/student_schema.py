from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator, model_validator

from app.core import validators

# Edad aceptada para un estudiante de diplomado (PDF: "Datos de matrícula").
STUDENT_MIN_AGE = 10
STUDENT_MAX_AGE = 100
ADULT_AGE = 18

SCHOOLING_OPTIONS = ("Primaria", "Tercer ciclo", "Bachillerato", "Técnico", "Universitario", "Otro")
KINSHIP_OPTIONS = (
    "Padre", "Madre", "Tutor", "Tutora", "Abuelo", "Abuela", "Hermano", "Hermana",
    "Tío", "Tía", "Cónyuge", "Otro",
)


def _pick(value: Optional[str], options: tuple, label: str) -> Optional[str]:
    if value is None or not value.strip():
        return None
    by_key = {option.lower(): option for option in options}
    picked = by_key.get(value.strip().lower())
    if picked is None:
        raise ValueError(f"{label} debe ser uno de: {', '.join(options)}")
    return picked


class _StudentFields(BaseModel):
    """Validaciones por campo, comunes a crear y editar."""

    @field_validator("full_name", check_fields=False)
    @classmethod
    def _full_name(cls, v):
        return None if v is None else validators.person_name(v, "El nombre completo")

    @field_validator("responsible_name", check_fields=False)
    @classmethod
    def _responsible_name(cls, v):
        if v is None or not v.strip():
            return None
        return validators.person_name(v, "El nombre del responsable")

    @field_validator("age", check_fields=False)
    @classmethod
    def _age(cls, v):
        if v is not None and not STUDENT_MIN_AGE <= v <= STUDENT_MAX_AGE:
            raise ValueError(f"La edad debe estar entre {STUDENT_MIN_AGE} y {STUDENT_MAX_AGE} años")
        return v

    @field_validator("birth_date", check_fields=False)
    @classmethod
    def _birth_date(cls, v):
        return validators.birth_date(v, STUDENT_MIN_AGE, STUDENT_MAX_AGE)

    @field_validator("dui", check_fields=False)
    @classmethod
    def _dui(cls, v):
        return validators.dui(v, "El DUI del estudiante")

    @field_validator("responsible_dui", check_fields=False)
    @classmethod
    def _responsible_dui(cls, v):
        return validators.dui(v, "El DUI del responsable")

    @field_validator("address", check_fields=False)
    @classmethod
    def _address(cls, v):
        return validators.free_text(v, "La dirección", min_length=5, max_length=250)

    @field_validator("contact_phone", check_fields=False)
    @classmethod
    def _contact_phone(cls, v):
        return validators.phone(v, "El teléfono de contacto")

    @field_validator("responsible_whatsapp", check_fields=False)
    @classmethod
    def _whatsapp(cls, v):
        return validators.phone(v, "El WhatsApp del responsable")

    @field_validator("schooling", check_fields=False)
    @classmethod
    def _schooling(cls, v):
        return _pick(v, SCHOOLING_OPTIONS, "La escolaridad")

    @field_validator("responsible_kinship", check_fields=False)
    @classmethod
    def _kinship(cls, v):
        return _pick(v, KINSHIP_OPTIONS, "El parentesco")

    @field_validator("email", "responsible_email", mode="before", check_fields=False)
    @classmethod
    def _blank_email(cls, v):
        if isinstance(v, str):
            v = v.strip().lower()
            return v or None
        return v


_REQUIRED = {
    "address": "La dirección",
    "email": "El correo",
    "contact_phone": "El teléfono de contacto",
    "schooling": "La escolaridad",
    "birth_date": "La fecha de nacimiento",
}


def _check_required(model: BaseModel, only_sent: bool) -> None:
    # Un texto vacío ("") pasa el tipo str pero los validadores lo vuelven
    # None: sin esto, un campo obligatorio podía quedar en blanco.
    for field, label in _REQUIRED.items():
        if only_sent and field not in model.model_fields_set:
            continue
        if getattr(model, field) is None:
            raise ValueError(f"Falta {label[0].lower()}{label[1:]} (dato obligatorio)")


class StudentCreate(_StudentFields):
    full_name: str
    age: Optional[int] = None
    birth_date: date
    dui: Optional[str] = None
    address: str
    email: EmailStr
    contact_phone: str
    schooling: str

    responsible_name: Optional[str] = None
    responsible_dui: Optional[str] = None
    responsible_kinship: Optional[str] = None
    responsible_email: Optional[EmailStr] = None
    responsible_whatsapp: Optional[str] = None

    @model_validator(mode="after")
    def _required(self):
        _check_required(self, only_sent=False)
        return self


class StudentUpdate(_StudentFields):
    full_name: Optional[str] = None
    age: Optional[int] = None
    birth_date: Optional[date] = None
    dui: Optional[str] = None
    address: Optional[str] = None
    email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    schooling: Optional[str] = None

    responsible_name: Optional[str] = None
    responsible_dui: Optional[str] = None
    responsible_kinship: Optional[str] = None
    responsible_email: Optional[EmailStr] = None
    responsible_whatsapp: Optional[str] = None

    @model_validator(mode="after")
    def _required(self):
        _check_required(self, only_sent=True)
        return self


def check_student_consistency(data: dict) -> dict:
    """Reglas que cruzan campos, sobre el registro completo (al crear, o el
    registro existente + los cambios al editar):
    - la edad se calcula de la fecha de nacimiento; si se envía, debe coincidir;
    - un menor de edad necesita los datos de su responsable.
    Lanza ValueError con el primer problema encontrado."""
    birth = data.get("birth_date")
    if birth is None:
        return data
    real_age = validators.age_on(birth)
    if data.get("age") is not None and data["age"] != real_age:
        raise ValueError(
            f"La edad ({data['age']}) no coincide con la fecha de nacimiento (serían {real_age} años)"
        )
    data["age"] = real_age
    if real_age < ADULT_AGE:
        missing = [
            label
            for key, label in (
                ("responsible_name", "nombre del responsable"),
                ("responsible_dui", "DUI del responsable"),
                ("responsible_kinship", "parentesco"),
                ("responsible_whatsapp", "WhatsApp del responsable"),
            )
            if not data.get(key)
        ]
        if missing:
            raise ValueError(
                f"El estudiante es menor de edad ({real_age} años): falta {', '.join(missing)}"
            )
    return data


class StudentSimple(BaseModel):
    id: int
    full_name: str

    model_config = ConfigDict(from_attributes=True)
