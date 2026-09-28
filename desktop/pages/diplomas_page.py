from api_client import api
from widgets.crud_page import Column, CrudPage, Field

# Los diplomados no tienen precios propios: la matrícula y la colegiatura
# salen del tarifario institucional (Configuración), igual para todos.


def _fetch():
    return api.get("/diplomas/")


def _body(payload: dict) -> dict:
    return {
        "name": payload["name"],
        "description": payload["description"] or None,
        "duration_months": payload["duration_months"],
        "active": payload["active"],
    }


def _create(payload: dict):
    return api.post("/diplomas/", json=_body(payload))


def _update(row: dict, payload: dict):
    return api.put(f"/diplomas/{row['id']}", json=_body(payload))


def _delete(row: dict):
    return api.delete(f"/diplomas/{row['id']}")


def _installments(row: dict) -> str:
    """Cuotas de colegiatura (una cada 28 días mientras dure el programa)."""
    days = round(row["duration_months"] * 365.25 / 12)
    return str(max(1, -(-days // 28)))


class DiplomasPage(CrudPage):
    def __init__(self, parent=None):
        columns = [
            Column("id", "ID"),
            Column("name", "Programa"),
            Column("description", "Descripción", formatter=lambda r: r.get("description") or "—"),
            Column("duration_months", "Duración (meses)"),
            Column("installments", "Cuotas aprox.", formatter=_installments),
            Column("active", "Estado", formatter=lambda r: "Activo" if r.get("active") else "Inactivo"),
        ]
        spec = [
            Field("name", "Nombre del programa", required=True),
            Field("description", "Descripción"),
            Field("duration_months", "Duración (meses)", kind="int", default=6, minimum=1, maximum=36),
            Field("active", "Activo (recibe inscripciones)", kind="bool", default=True),
        ]
        super().__init__(
            title="Diplomados",
            subtitle="Catálogo de programas y su duración · los precios están en Configuración (tarifario)",
            columns=columns,
            fetch_fn=_fetch,
            create_spec=spec,
            create_fn=_create,
            create_label="Nuevo programa",
            delete_fn=_delete,
            edit_spec=spec,
            update_fn=_update,
            empty_message="No hay programas registrados todavía.",
            parent=parent,
        )
