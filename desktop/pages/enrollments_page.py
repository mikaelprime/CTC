from PySide6.QtWidgets import QDialog, QInputDialog, QMessageBox

from api_client import ApiError, api
from pages.matricula_dialog import TUITION_PLANS, MatriculaDialog
from pages.student_history import StudentHistoryDialog
from widgets.crud_page import Column, CrudPage, Field
from widgets.receipt_view import fmt_date, show_receipt

_TUITION_PLAN_SHORT_LABELS = {"GRUPAL": "Grupal", "PRIVADO": "Privado", "ONLINE": "On-line"}


def _fetch():
    return api.get("/enrollments/")


def _schedule_options():
    schedules = api.get("/schedules/") or []
    return [(s["name"], s["id"]) for s in schedules if s.get("active")]


def _tuition_plan_label(value):
    return _TUITION_PLAN_SHORT_LABELS.get(value, value or "—")


def _installments(row: dict) -> str:
    if row.get("installments_total") is None:
        return "—"
    text = f"{row['installments_paid']} de {row['installments_total']}"
    if row.get("overdue_installments"):
        text += f" ({row['overdue_installments']} vencida{'s' if row['overdue_installments'] != 1 else ''})"
    return text


def _delete(row: dict):
    return api.delete(f"/enrollments/{row['id']}")


def _update(row: dict, payload: dict):
    body = {
        "schedule_id": payload["schedule_id"],
        "tuition_plan": payload["tuition_plan"],
        "observations": payload["observations"] or None,
    }
    # La fecha de inicio solo se envía si cambió: con colegiaturas ya
    # cobradas el backend no permite moverla.
    if payload["start_date"] != row.get("start_date"):
        body["start_date"] = payload["start_date"]
    return api.put(f"/enrollments/{row['id']}", json=body)


class EnrollmentsPage(CrudPage):
    def __init__(self, parent=None):
        columns = [
            Column("id", "#"),
            Column("student", "Estudiante", formatter=lambda r: r["student"]["full_name"]),
            Column("diploma", "Programa", formatter=lambda r: r["diploma"]["name"]),
            Column("schedule", "Horario", formatter=lambda r: r["schedule"]["name"]),
            Column("tuition_plan", "Plan", formatter=lambda r: _tuition_plan_label(r.get("tuition_plan"))),
            Column("start_date", "Inicio de clases", formatter=lambda r: fmt_date(r["start_date"])),
            Column("installments", "Cuotas pagadas", formatter=_installments),
            Column("next_payment_date", "Próximo pago", formatter=lambda r: fmt_date(r.get("next_payment_date"))),
            Column("status", "Estado"),
        ]
        self.is_admin = api.is_admin()
        # Editar: horario, plan (aplica desde la próxima cuota), fecha de
        # inicio (solo antes del primer cobro de colegiatura) y
        # observaciones. El programa no se cambia: se anula y se crea otra.
        edit_spec = [
            Field("schedule_id", "Horario", kind="combo", options=_schedule_options),
            Field("tuition_plan", "Plan de colegiatura", kind="combo",
                  options=lambda: [(label, code) for code, label, _column in TUITION_PLANS]),
            Field("start_date", "Fecha de inicio de clases", kind="date", min_days=-365 - 90, max_days=365),
            Field("observations", "Observaciones", max_length=500),
        ]
        super().__init__(
            title="Inscripciones",
            subtitle="Registro de matrícula (PDF: Datos de matrícula), cuotas y estado de cada estudiante",
            columns=columns,
            fetch_fn=_fetch,
            create_label="Nueva matrícula",
            custom_create=True,
            delete_fn=_delete if self.is_admin else None,
            edit_spec=edit_spec if self.is_admin else None,
            update_fn=_update,
            extra_actions=[
                ("Estado de cuenta", self.show_history, lambda row: True),
                ("Anular", self.cancel_enrollment,
                 lambda row: self.is_admin and row.get("status") not in ("ANULADA", "FINALIZADA")),
            ],
            empty_message="No hay inscripciones registradas todavía. Usa «Nueva matrícula».",
            parent=parent,
        )

    def on_create(self) -> None:
        try:
            dialog = MatriculaDialog(self)
        except ApiError as exc:
            QMessageBox.critical(self, "No se pudo abrir el formulario", str(exc))
            return
        if dialog.exec() != QDialog.Accepted:
            return
        result = dialog.result_data
        self.reload()
        first = fmt_date(result.get("next_payment_date") or result.get("start_date"))
        intro = (
            f"Matrícula #{result['id']} registrada para {result['student']['full_name']}.\n"
            f"Primera colegiatura: {first} · {result['installments_total']} cuotas en total."
        )
        if result.get("receipt_id"):
            show_receipt(self, result["receipt_id"], intro)
        else:
            QMessageBox.information(self, "Matrícula registrada", intro + "\n\nMatrícula gratis: no hubo cobro.")

    def on_edit(self, row: dict) -> None:
        if row.get("status") == "ANULADA":
            QMessageBox.information(self, "Inscripción anulada", "Una inscripción anulada no se puede editar.")
            return
        super().on_edit(row)

    def show_history(self, row: dict) -> None:
        try:
            dialog = StudentHistoryDialog(row["student"]["id"], self)
        except ApiError as exc:
            QMessageBox.critical(self, "No se pudo cargar el estado de cuenta", str(exc))
            return
        dialog.exec()

    def cancel_enrollment(self, row: dict) -> None:
        reason, ok = QInputDialog.getText(
            self,
            "Anular inscripción",
            f"Motivo para anular la inscripción #{row['id']} de {row['student']['full_name']}.\n"
            "Los pagos ya cobrados se conservan en los reportes de caja.",
        )
        if not ok:
            return
        try:
            api.post(f"/enrollments/{row['id']}/cancel", json={"reason": reason})
        except ApiError as exc:
            QMessageBox.critical(self, "No se pudo anular", str(exc))
            return
        self.reload()
