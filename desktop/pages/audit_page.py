"""Bitácora: quién hizo cada operación sensible (cobros, anulaciones,
cierres de caja, cambios de configuración y de usuarios) y cuándo."""

from api_client import api
from widgets.animated_button import AnimatedButton
from widgets.crud_page import Column, CrudPage
from widgets.report_export import Report, Section, export_report

ACTION_LABELS = {
    "INICIO_SESION": "Inicio de sesión",
    "BLOQUEO_USUARIO": "Usuario bloqueado",
    "CAMBIO_CONTRASENA": "Cambio de contraseña",
    "REGISTRO_ESTUDIANTE": "Registro de estudiante",
    "EDICION_ESTUDIANTE": "Edición de estudiante",
    "ELIMINACION_ESTUDIANTE": "Eliminación de estudiante",
    "INSCRIPCION": "Matrícula",
    "EDICION_INSCRIPCION": "Edición de inscripción",
    "ANULACION_INSCRIPCION": "Anulación de inscripción",
    "ELIMINACION_INSCRIPCION": "Eliminación de inscripción",
    "COBRO": "Cobro de colegiatura",
    "ANULACION_PAGO": "Anulación de pago",
    "APERTURA_CAJA": "Apertura de caja",
    "CIERRE_CAJA": "Cierre de caja",
    "CAMBIO_CONFIGURACION": "Cambio de configuración",
    "CREACION_CAJERO": "Creación de cajero",
    "ACTIVACION_CAJERO": "Activación de cajero",
    "DESACTIVACION_CAJERO": "Desactivación de cajero",
    "RESTABLECER_CONTRASENA": "Contraseña restablecida",
}


def _fetch():
    return api.get("/audit/?limit=1000") or []


def action_label(row: dict) -> str:
    return ACTION_LABELS.get(row["action"], row["action"])


class AuditPage(CrudPage):
    def __init__(self, parent=None):
        super().__init__(
            title="Bitácora de auditoría",
            subtitle="Operaciones sensibles registradas por el sistema (las más recientes primero)",
            columns=[
                Column("created_at", "Fecha y hora"),
                Column("user_name", "Usuario"),
                Column("action", "Operación", formatter=action_label),
                Column("detail", "Detalle", formatter=lambda r: r.get("detail") or ""),
            ],
            fetch_fn=_fetch,
            empty_message="Todavía no hay operaciones registradas.",
            parent=parent,
        )
        export = AnimatedButton("Exportar Excel / PDF")
        export.clicked.connect(self.export)
        self.layout().insertWidget(3, export)

    def _search_text(self, value) -> str:
        # Permite buscar también por el nombre legible de la operación.
        if isinstance(value, dict) and "action" in value:
            return f"{super()._search_text(value)} {action_label(value)}"
        return super()._search_text(value)

    def export(self) -> None:
        rows = self.visible_rows()
        export_report(self, Report(
            title="Bitácora de auditoría",
            subtitle=f"{len(rows)} operaciones",
            sections=[Section(
                "Operaciones",
                ["Fecha y hora", "Usuario", "Operación", "Detalle"],
                [[r["created_at"], r["user_name"], action_label(r), r.get("detail") or ""] for r in rows],
            )],
        ), "Bitacora")
