from api_client import api
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


def _create(payload: dict):
    body = {
        "student_id": payload["student_id"],
        "diploma_id": payload["diploma_id"],
        "schedule_id": payload["schedule_id"],
        "enrollment_date": payload["enrollment_date"],
        "start_date": payload["start_date"],
        "end_date": payload["end_date"],
    }
    return api.post("/enrollments/", json=body)


def _delete(row: dict):
    return api.delete(f"/enrollments/{row['id']}")


class EnrollmentsPage(CrudPage):
    def __init__(self, parent=None):
        columns = [
            Column("id", "ID"),
            Column("student", "Estudiante", formatter=lambda r: r["student"]["full_name"]),
            Column("diploma", "Programa", formatter=lambda r: r["diploma"]["name"]),
            Column("schedule", "Turno", formatter=lambda r: r["schedule"]["name"]),
            Column("start_date", "Inicio"),
            Column("end_date", "Fin"),
            Column("status", "Estado"),
        ]
        create_spec = [
            Field("student_id", "Estudiante", kind="combo", options=_student_options),
            Field("diploma_id", "Programa", kind="combo", options=_diploma_options),
            Field("schedule_id", "Turno", kind="combo", options=_schedule_options),
            Field("enrollment_date", "Fecha de inscripción", kind="date"),
            Field("start_date", "Fecha de inicio", kind="date"),
            Field("end_date", "Fecha de fin", kind="date"),
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
