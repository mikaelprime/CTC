from api_client import api
from widgets.crud_page import Column, CrudPage, Field


def _fetch():
    return api.get("/diplomas/")


def _create(payload: dict):
    body = {
        "name": payload["name"],
        "description": payload["description"] or None,
        "duration_months": payload["duration_months"],
        "registration_fee": payload["registration_fee"],
        "monthly_fee": payload["monthly_fee"],
        "active": payload["active"],
    }
    return api.post("/diplomas/", json=body)


def _update(row: dict, payload: dict):
    body = {
        "name": payload["name"],
        "description": payload["description"] or None,
        "duration_months": payload["duration_months"],
        "registration_fee": payload["registration_fee"],
        "monthly_fee": payload["monthly_fee"],
        "active": payload["active"],
    }
    return api.put(f"/diplomas/{row['id']}", json=body)


def _delete(row: dict):
    return api.delete(f"/diplomas/{row['id']}")


class DiplomasPage(CrudPage):
    def __init__(self, parent=None):
        columns = [
            Column("id", "ID"),
            Column("name", "Programa"),
            Column("duration_months", "Duración (meses)"),
            Column("registration_fee", "Matrícula", formatter=lambda r: f"${r['registration_fee']:,}"),
            Column("monthly_fee", "Mensualidad", formatter=lambda r: f"${r['monthly_fee']:,}"),
            Column("active", "Estado", formatter=lambda r: "Activo" if r.get("active") else "Inactivo"),
        ]
        create_spec = [
            Field("name", "Nombre del programa"),
            Field("description", "Descripción"),
            Field("duration_months", "Duración (meses)", kind="int", default=6, minimum=1, maximum=60),
            Field("registration_fee", "Cuota de matrícula (USD)", kind="int", default=50, maximum=100_000),
            Field("monthly_fee", "Cuota mensual (USD)", kind="int", default=40, maximum=100_000),
            Field("active", "Activo", kind="bool", default=True),
        ]
        super().__init__(
            title="Diplomas y Programas Académicos",
            subtitle="Catálogo de programas, duración y aranceles",
            columns=columns,
            fetch_fn=_fetch,
            create_spec=create_spec,
            create_fn=_create,
            create_label="Nuevo programa",
            delete_fn=_delete,
            edit_spec=create_spec,
            update_fn=_update,
            empty_message="No hay programas registrados todavía.",
            parent=parent,
        )
