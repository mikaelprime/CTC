from datetime import date, timedelta

from api_client import ApiError, api
from widgets.crud_page import Column, CrudPage, Field


def _fetch():
    return api.get("/enrollments/")


def _student_options():
    students = api.get("/students/") or []
    return [(s["full_name"], s["id"]) for s in students]


def _diploma_options():
    diplomas = api.get("/diplomas/") or []
    return [(d["name"], d["id"]) for d in diplomas]


def _schedule_options():
    schedules = api.get("/schedules/") or []
    return [(s["name"], s["id"]) for s in schedules]


# Tarifario fijo institucional (no depende del diplomado): ver
# backend/app/core/pricing.py, que es la fuente de verdad real para el
# cálculo. Estas opciones son solo lo que se muestra en el combo.
_REGISTRATION_OPTIONS = [
    ("Matrícula completa ($20.00)", "COMPLETA"),
    ("Promo-Matrícula 50% OFF ($10.00)", "PROMO"),
    ("Matrícula gratis ($0.00)", "GRATIS"),
]
_TUITION_PLAN_OPTIONS = [
    ("Plan Grupal ($25.00/mes)", "GRUPAL"),
    ("Plan Privado ($55.00/mes)", "PRIVADO"),
    ("Plan On-line ($70.00/mes)", "ONLINE"),
]
_TUITION_PLAN_SHORT_LABELS = {"GRUPAL": "Grupal", "PRIVADO": "Privado", "ONLINE": "On-line"}


def _tuition_plan_label(value):
    return _TUITION_PLAN_SHORT_LABELS.get(value, value or "—")


def _create(payload: dict):
    body = {
        "student_id": payload["student_id"],
        "diploma_id": payload["diploma_id"],
        "schedule_id": payload["schedule_id"],
        "enrollment_date": payload["enrollment_date"],
        "start_date": payload["start_date"],
        "registration_type": payload["registration_type"],
        "tuition_plan": payload["tuition_plan"],
        "observations": payload["observations"] or None,
    }
    return api.post("/enrollments/", json=body)


def _delete(row: dict):
    return api.delete(f"/enrollments/{row['id']}")


class EnrollmentsPage(CrudPage):
    def __init__(self, parent=None):
        # El ciclo de cobro es configurable desde Configuración (ya no son
        # siempre 28 días fijos); se trae una sola vez aquí, no por fila,
        # para no convertir esta tabla en una petición HTTP por matrícula.
        cycle_days = 28
        try:
            cycle_days = int(api.get("/config/")["payment_cycle_days"])
        except (ApiError, KeyError, TypeError, ValueError):
            pass

        columns = [
            Column("id", "ID"),
            Column("student", "Estudiante", formatter=lambda r: r["student"]["full_name"]),
            Column("diploma", "Programa", formatter=lambda r: r["diploma"]["name"]),
            Column("schedule", "Turno", formatter=lambda r: r["schedule"]["name"]),
            Column("tuition_plan", "Plan", formatter=lambda r: _tuition_plan_label(r.get("tuition_plan"))),
            Column("start_date", "Inicio"),
            Column("end_date", "Fin"),
            Column(
                "next_payment",
                "Próximo pago (estimado)",
                formatter=lambda r: (
                    date.fromisoformat(r["start_date"]) + timedelta(days=cycle_days)
                ).isoformat(),
            ),
            Column("status", "Estado"),
        ]
        create_spec = [
            Field("student_id", "Estudiante", kind="combo", options=_student_options),
            Field("diploma_id", "Programa", kind="combo", options=_diploma_options),
            Field("schedule_id", "Turno", kind="combo", options=_schedule_options),
            Field("enrollment_date", "Fecha de matrícula", kind="date"),
            # Distinta de la fecha de matrícula: es la que determina el
            # primer cobro y los siguientes cada 28 días (ver README/PDF de
            # la propuesta, sección "Funcionamiento básico").
            Field("start_date", "Fecha de inicio de clases", kind="date"),
            Field("registration_type", "Tipo de matrícula", kind="combo", options=lambda: _REGISTRATION_OPTIONS),
            Field("tuition_plan", "Plan de colegiatura", kind="combo", options=lambda: _TUITION_PLAN_OPTIONS),
            Field("observations", "Observaciones"),
        ]
        super().__init__(
            title="Gestión de Inscripciones",
            subtitle="Matrículas por estudiante, programa y turno",
            columns=columns,
            fetch_fn=_fetch,
            create_spec=create_spec,
            create_fn=_create,
            create_label="Nueva inscripción",
            delete_fn=_delete,
            empty_message="No hay inscripciones registradas todavía. Crea primero un estudiante, un programa y un turno.",
            parent=parent,
        )
