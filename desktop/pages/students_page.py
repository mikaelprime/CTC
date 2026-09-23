from api_client import api
from widgets.crud_page import Column, CrudPage, Field


def _fetch():
    return api.get("/students/")


def _create(payload: dict):
    body = {
        "full_name": payload["full_name"],
        "age": payload["age"] or None,
        "birth_date": payload["birth_date"],
        "email": payload["email"],
        "contact_phone": payload["contact_phone"],
        "address": payload["address"],
        "schooling": payload["schooling"],
        "responsible_name": payload["responsible_name"],
        "responsible_dui": payload["responsible_dui"],
        "responsible_kinship": payload["responsible_kinship"],
        "responsible_email": payload["responsible_email"] or None,
        "responsible_whatsapp": payload["responsible_whatsapp"],
    }
    return api.post("/students/", json=body)


def _update(row: dict, payload: dict):
    body = {
        "full_name": payload["full_name"],
        "age": payload["age"] or None,
        "birth_date": payload["birth_date"],
        "email": payload["email"],
        "contact_phone": payload["contact_phone"],
        "address": payload["address"],
        "schooling": payload["schooling"],
        "responsible_name": payload["responsible_name"],
        "responsible_dui": payload["responsible_dui"],
        "responsible_kinship": payload["responsible_kinship"],
        "responsible_email": payload["responsible_email"] or None,
        "responsible_whatsapp": payload["responsible_whatsapp"],
    }
    return api.put(f"/students/{row['id']}", json=body)


def _delete(row: dict):
    return api.delete(f"/students/{row['id']}")


class StudentsPage(CrudPage):
    def __init__(self, parent=None):
        columns = [
            Column("id", "ID"),
            Column("full_name", "Nombre completo"),
            Column("email", "Correo"),
            Column("contact_phone", "Teléfono"),
            Column("schooling", "Escolaridad"),
        ]
        create_spec = [
            Field("full_name", "Nombre completo"),
            Field("age", "Edad", kind="int", minimum=0, maximum=120),
            Field("birth_date", "Fecha de nacimiento", kind="date"),
            Field("address", "Dirección"),
            Field("email", "Correo"),
            Field("contact_phone", "Contacto"),
            Field("schooling", "Escolaridad"),
            Field("responsible_name", "Nombre del responsable"),
            Field("responsible_dui", "DUI del responsable"),
            Field("responsible_kinship", "Parentesco"),
            Field("responsible_email", "Correo del responsable"),
            Field("responsible_whatsapp", "WhatsApp del responsable"),
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
            edit_spec=create_spec,
            update_fn=_update,
            empty_message="No hay estudiantes registrados todavía.",
            parent=parent,
        )
