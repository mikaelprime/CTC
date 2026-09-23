from PySide6.QtCore import QDate

from api_client import ApiError, api
from pages.student_history import StudentHistoryDialog
from widgets.crud_page import Column, CrudPage, Field

# Las reglas reales viven en el backend (app/core/validators.py y
# student_schema.py); aquí solo se impide teclear lo que nunca sería válido
# y se ofrecen listas cerradas para que no haya datos inventados.
_NAME_REGEX = r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ' \-]*$"
_PHONE_REGEX = r"^[+0-9 ()\-]{0,20}$"
_NO_SPACES_REGEX = r"^\S*$"
_DUI_MASK = "99999999-9;_"

_SCHOOLING_OPTIONS = [
    (label, label)
    for label in ("Primaria", "Tercer ciclo", "Bachillerato", "Técnico", "Universitario", "Otro")
]
_KINSHIP_OPTIONS = [("— Sin responsable (estudiante adulto) —", "")] + [
    (label, label)
    for label in ("Padre", "Madre", "Tutor", "Tutora", "Abuelo", "Abuela", "Hermano", "Hermana",
                  "Tío", "Tía", "Cónyuge", "Otro")
]
_STUDENT_MIN_AGE = 10
_STUDENT_MAX_AGE = 100


def _fetch():
    return api.get("/students/")


def _body(payload: dict) -> dict:
    return {
        "full_name": payload["full_name"],
        "age": payload["age"] or None,
        "birth_date": payload["birth_date"],
        "email": payload["email"],
        "contact_phone": payload["contact_phone"],
        "address": payload["address"],
        "schooling": payload["schooling"],
        "responsible_name": payload["responsible_name"] or None,
        "responsible_dui": payload["responsible_dui"] or None,
        "responsible_kinship": payload["responsible_kinship"] or None,
        "responsible_email": payload["responsible_email"] or None,
        "responsible_whatsapp": payload["responsible_whatsapp"] or None,
    }


def _create(payload: dict):
    return api.post("/students/", json=_body(payload))


def _update(row: dict, payload: dict):
    return api.put(f"/students/{row['id']}", json=_body(payload))


def _delete(row: dict):
    return api.delete(f"/students/{row['id']}")


class StudentsPage(CrudPage):
    def __init__(self, parent=None):
        columns = [
            Column("id", "ID"),
            Column("full_name", "Nombre completo"),
            Column("age", "Edad", formatter=lambda r: str(r.get("age") or "—")),
            Column("email", "Correo"),
            Column("contact_phone", "Teléfono"),
            Column("schooling", "Escolaridad"),
        ]
        create_spec = [
            Field("full_name", "Nombre completo", regex=_NAME_REGEX, max_length=150,
                  placeholder="Nombre y apellido", required=True),
            Field("birth_date", "Fecha de nacimiento", kind="date",
                  min_days=-365 * _STUDENT_MAX_AGE, max_days=-365 * _STUDENT_MIN_AGE, default_days=-365 * 18),
            # Se calcula sola desde la fecha de nacimiento (ver prepare_dialog).
            Field("age", "Edad", kind="int", minimum=_STUDENT_MIN_AGE, maximum=_STUDENT_MAX_AGE, default=18),
            Field("address", "Dirección", max_length=250, placeholder="Colonia, calle, municipio", required=True),
            Field("email", "Correo", regex=_NO_SPACES_REGEX, max_length=120,
                  placeholder="nombre@correo.com", required=True),
            Field("contact_phone", "Contacto", regex=_PHONE_REGEX, placeholder="7777-8888", required=True),
            Field("schooling", "Escolaridad", kind="combo", options=lambda: _SCHOOLING_OPTIONS),
            Field("responsible_name", "Nombre del responsable", regex=_NAME_REGEX, max_length=150,
                  placeholder="Obligatorio si es menor de 18 años"),
            Field("responsible_dui", "DUI del responsable", input_mask=_DUI_MASK),
            Field("responsible_kinship", "Parentesco", kind="combo", options=lambda: _KINSHIP_OPTIONS),
            Field("responsible_email", "Correo del responsable", regex=_NO_SPACES_REGEX, max_length=120),
            Field("responsible_whatsapp", "WhatsApp del responsable", regex=_PHONE_REGEX,
                  placeholder="7777-8888 o +1 213 555 0199"),
        ]
        super().__init__(
            title="Gestión de Estudiantes",
            subtitle="Ficha académica, matrícula y seguimiento de rendimiento",
            columns=columns,
            fetch_fn=_fetch,
            create_spec=create_spec,
            create_fn=_create,
            create_label="Registrar estudiante",
            delete_fn=_delete if api.is_admin() else None,
            edit_spec=create_spec,
            update_fn=_update,
            extra_actions=[("Historial", self.show_history, lambda row: True)],
            empty_message="No hay estudiantes registrados todavía.",
            parent=parent,
        )

    def show_history(self, row: dict) -> None:
        try:
            dialog = StudentHistoryDialog(row["id"], self)
        except ApiError as exc:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "No se pudo cargar el historial", str(exc))
            return
        dialog.exec()

    def prepare_dialog(self, dialog) -> None:
        birth = dialog.inputs["birth_date"]
        age = dialog.inputs["age"]
        age.setReadOnly(True)
        age.setToolTip("Se calcula a partir de la fecha de nacimiento")

        def sync_age():
            born = birth.date()
            today = QDate.currentDate()
            years = today.year() - born.year() - (
                (today.month(), today.day()) < (born.month(), born.day())
            )
            age.setValue(years)

        birth.dateChanged.connect(sync_age)
        sync_age()
