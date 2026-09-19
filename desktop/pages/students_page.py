from api_client import api
from widgets.crud_page import Column, CrudPage, Field


def _fetch():
    return api.get("/students/")


def _create(payload: dict):
    body = {
        "full_name": payload["full_name"],
        "birth_date": payload["birth_date"],
        "email": payload["email"],
        "phone": payload["phone"],
        "address": payload["address"],
        "education_level": payload["education_level"],
        "guardian_name": payload["guardian_name"],
        "guardian_dui": payload["guardian_dui"],
        "guardian_relationship": payload["guardian_relationship"],
    }
    return api.post("/students/", json=body)


def _delete(row: dict):
    return api.delete(f"/students/{row['id']}")


class StudentsPage(CrudPage):
    def __init__(self, parent=None):
        columns = [
            Column("id", "ID"),
            Column("full_name", "Nombre completo"),
            Column("email", "Correo"),
            Column("phone", "Teléfono"),
            Column("education_level", "Nivel educativo"),
            Column("is_active", "Estado", formatter=lambda r: "Activo" if r.get("is_active") else "Inactivo"),
        ]
        create_spec = [
            Field("full_name", "Nombre completo"),
            Field("birth_date", "Fecha de nacimiento", kind="date"),
            Field("email", "Correo"),
            Field("phone", "Teléfono"),
            Field("address", "Dirección"),
            Field("education_level", "Nivel educativo"),
            Field("guardian_name", "Nombre del responsable"),
            Field("guardian_dui", "DUI del responsable"),
            Field("guardian_relationship", "Parentesco"),
        ]
        super().__init__(
            title="Gestión de Estudiantes",
            subtitle="Ficha académica, matrícula y seguimiento de rendimiento",
            columns=columns,
            fetch_fn=_fetch,
            create_spec=create_spec,
            create_fn=_create,
            create_label="Registrar estudiante",
            delete_fn=_delete,
            empty_message="No hay estudiantes registrados todavía.",
            parent=parent,
        )
