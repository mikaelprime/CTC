from api_client import api
from widgets.crud_page import Column, CrudPage, Field


def _fetch():
    return api.get("/schedules/")


def _create(payload: dict):
    body = {
        "name": payload["name"],
        "start_time": payload["start_time"],
        "end_time": payload["end_time"],
    }
    return api.post("/schedules/", json=body)


def _update(row: dict, payload: dict):
    body = {
        "name": payload["name"],
        "start_time": payload["start_time"],
        "end_time": payload["end_time"],
        "active": payload["active"],
    }
    return api.put(f"/schedules/{row['id']}", json=body)


def _delete(row: dict):
    return api.delete(f"/schedules/{row['id']}")


class SchedulesPage(CrudPage):
    def __init__(self, parent=None):
        columns = [
            Column("id", "ID"),
            Column("name", "Turno"),
            Column("start_time", "Inicio"),
            Column("end_time", "Fin"),
            Column("active", "Estado", formatter=lambda r: "Activo" if r.get("active") else "Inactivo"),
        ]
        create_spec = [
            Field("name", "Nombre del turno"),
            Field("start_time", "Hora de inicio", kind="time"),
            Field("end_time", "Hora de fin", kind="time"),
        ]
        edit_spec = create_spec + [
            Field("active", "Activo", kind="bool", default=True),
        ]
        super().__init__(
            title="Horarios",
            subtitle="Turnos disponibles para las matrículas",
            columns=columns,
            fetch_fn=_fetch,
            create_spec=create_spec,
            create_fn=_create,
            create_label="Nuevo turno",
            delete_fn=_delete,
            edit_spec=edit_spec,
            update_fn=_update,
            empty_message="No hay horarios registrados todavía.",
            parent=parent,
        )
