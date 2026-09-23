"""Convierte los errores 422 de FastAPI/Pydantic (una lista en inglés con
rutas tipo ["body", "contact_phone"]) en un texto en español que el cajero
pueda leer directamente en el mensaje de error del escritorio."""

FIELD_LABELS = {
    "full_name": "Nombre completo",
    "age": "Edad",
    "birth_date": "Fecha de nacimiento",
    "dui": "DUI",
    "address": "Dirección",
    "email": "Correo",
    "contact_phone": "Teléfono de contacto",
    "schooling": "Escolaridad",
    "responsible_name": "Nombre del responsable",
    "responsible_dui": "DUI del responsable",
    "responsible_kinship": "Parentesco",
    "responsible_email": "Correo del responsable",
    "responsible_whatsapp": "WhatsApp del responsable",
    "password": "Contraseña",
    "name": "Nombre",
    "description": "Descripción",
    "duration_months": "Duración (meses)",
    "registration_fee": "Cuota de matrícula",
    "monthly_fee": "Cuota mensual",
    "start_time": "Hora de inicio",
    "end_time": "Hora de fin",
    "student_id": "Estudiante",
    "diploma_id": "Programa",
    "schedule_id": "Turno",
    "enrollment_date": "Fecha de matrícula",
    "start_date": "Fecha de inicio de clases",
    "end_date": "Fecha de fin",
    "observations": "Observaciones",
    "cash_received": "Efectivo",
    "payment_date": "Fecha de pago",
    "due_date": "Fecha de vencimiento",
    "amount": "Monto",
    "surcharge": "Recargo",
    "payment_type": "Método de pago",
    "status": "Estado",
    "months": "Meses",
    "initial_amount": "Fondo inicial",
    "physical_amount": "Efectivo contado",
    "explanation": "Justificación",
    "reason": "Motivo",
    "late_fee": "Recargo por mora",
    "payment_cycle_days": "Días del ciclo de pago",
    "alert_days_before": "Días de aviso",
    "institution_name": "Nombre de la institución",
}

_MESSAGES = {
    "missing": "es obligatorio",
    "greater_than_equal": "debe ser mayor o igual a {ge}",
    "greater_than": "debe ser mayor que {gt}",
    "less_than_equal": "debe ser menor o igual a {le}",
    "less_than": "debe ser menor que {lt}",
    "string_too_short": "debe tener al menos {min_length} caracteres",
    "string_too_long": "no puede pasar de {max_length} caracteres",
    "int_parsing": "debe ser un número entero",
    "int_from_float": "debe ser un número entero",
    "float_parsing": "debe ser un número",
    "decimal_parsing": "debe ser un número",
    "date_parsing": "no es una fecha válida (use AAAA-MM-DD)",
    "date_from_datetime_parsing": "no es una fecha válida (use AAAA-MM-DD)",
    "time_parsing": "no es una hora válida",
    "bool_parsing": "debe ser Sí o No",
    "string_type": "debe ser texto",
}


def _one(error: dict) -> str:
    loc = [part for part in error.get("loc", ()) if part not in ("body", "query", "path")]
    field = str(loc[-1]) if loc else ""
    label = FIELD_LABELS.get(field, field)
    kind = error.get("type", "")
    msg = str(error.get("msg", ""))

    if kind == "value_error":
        msg = msg.removeprefix("Value error, ")
        if "email address" in msg.lower():
            return f"{label}: no es un correo electrónico válido"
        # Los mensajes de app.core.validators ya nombran el campo.
        return msg if not label or msg.startswith(("El ", "La ", "Los ", "Las ")) else f"{label}: {msg}"

    template = _MESSAGES.get(kind)
    if template:
        try:
            text = template.format(**error.get("ctx", {}))
        except (KeyError, IndexError):
            text = template
        return f"{label} {text}" if label else text
    return f"{label}: {msg}" if label else msg


def humanize(errors: list[dict]) -> str:
    lines = []
    for error in errors:
        line = _one(error)
        if line not in lines:
            lines.append(line)
    return "\n".join(lines) or "Los datos enviados no son válidos"
