from PySide6.QtWidgets import QInputDialog, QLabel, QMessageBox

from api_client import ApiError, api
from widgets.crud_page import Column, CrudPage, Field
from widgets.ticket_printer import print_ticket


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
# Solo para mostrar el total/cambio mientras se escribe; el backend
# (app/core/pricing.py) es quien cobra.
_REGISTRATION_FEES = {"COMPLETA": 20.0, "PROMO": 10.0, "GRATIS": 0.0}


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
        "cash_received": payload["cash_received"],
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
            Column("tuition_plan", "Plan", formatter=lambda r: _tuition_plan_label(r.get("tuition_plan"))),
            Column("start_date", "Inicio"),
            Column("end_date", "Fin"),
            # Antes se estimaba como inicio + 28 días, ignorando los pagos
            # hechos (y el primer cobro es el mismo día de inicio). Ahora lo
            # calcula el backend a partir de las cuotas registradas.
            Column(
                "next_payment_date",
                "Próximo pago",
                formatter=lambda r: r.get("next_payment_date") or "—",
            ),
            Column("status", "Estado"),
        ]
        create_spec = [
            Field("student_id", "Estudiante", kind="combo", options=_student_options),
            Field("diploma_id", "Programa", kind="combo", options=_diploma_options),
            Field("schedule_id", "Turno", kind="combo", options=_schedule_options),
            # No se matricula en el futuro; hasta un año atrás para pasar al
            # sistema matrículas hechas en papel.
            Field("enrollment_date", "Fecha de matrícula", kind="date", min_days=-365, max_days=0),
            # Distinta de la fecha de matrícula: es la que determina el
            # primer cobro y los siguientes cada 28 días (ver README/PDF de
            # la propuesta, sección "Funcionamiento básico").
            Field("start_date", "Fecha de inicio de clases", kind="date", min_days=-365 - 90, max_days=365),
            Field("registration_type", "Tipo de matrícula", kind="combo", options=lambda: _REGISTRATION_OPTIONS),
            Field("tuition_plan", "Plan de colegiatura", kind="combo", options=lambda: _TUITION_PLAN_OPTIONS),
            Field("observations", "Observaciones", max_length=500),
            # PDF punto 4: "Efectivo:" y el sistema calcula el "Cambio:".
            Field("cash_received", "Efectivo:", kind="float", default=20.0, maximum=100_000),
        ]
        self.is_admin = (api.user_role or "").upper() in {"ADMIN", "ADMINISTRADOR"}
        super().__init__(
            title="Gestión de Inscripciones",
            subtitle="Matrículas por estudiante, programa y turno",
            columns=columns,
            fetch_fn=_fetch,
            create_spec=create_spec,
            create_fn=_create,
            create_label="Nueva inscripción",
            delete_fn=_delete if self.is_admin else None,
            extra_actions=[
                ("Anular", self.cancel_enrollment,
                 lambda row: self.is_admin and row.get("status") != "ANULADA"),
            ],
            empty_message="No hay inscripciones registradas todavía. Crea primero un estudiante, un programa y un turno.",
            parent=parent,
        )

    def prepare_dialog(self, dialog) -> None:
        registration = dialog.inputs["registration_type"]
        cash = dialog.inputs["cash_received"]
        cash.setPrefix("$ ")
        total_label = QLabel()
        change_label = QLabel()
        change_label.setObjectName("PaymentHint")
        dialog.add_row("Total matrícula:", total_label)
        dialog.add_row("Cambio:", change_label)
        ok_button = dialog.buttons.button(dialog.buttons.StandardButton.Ok)

        def recalculate():
            fee = _REGISTRATION_FEES.get(registration.currentData(), 0.0)
            change = cash.value() - fee
            total_label.setText(f"${fee:,.2f}")
            change_label.setText(f"${change:,.2f}" if change >= 0 else f"Faltan ${-change:,.2f}")
            ok_button.setEnabled(change >= 0)

        registration.currentIndexChanged.connect(recalculate)
        cash.valueChanged.connect(recalculate)
        recalculate()

    def after_create(self, result) -> None:
        if not result:
            return
        fee = float(result.get("registration_fee") or 0)
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Information)
        box.setWindowTitle("Inscripción registrada")
        box.setText(
            f"Matrícula: ${fee:,.2f}\n"
            f"Cambio: ${float(result.get('change') or 0):,.2f}\n"
            f"Primer pago de colegiatura: {result.get('next_payment_date') or result.get('start_date')}"
        )
        print_button = box.addButton("Imprimir ticket", QMessageBox.ActionRole)
        box.addButton(QMessageBox.Ok)
        box.exec()
        if box.clickedButton() is print_button:
            print_ticket(
                self,
                "Comprobante de matrícula",
                [
                    ("Inscripción", f"#{result['id']}"),
                    ("Estudiante", result["student"]["full_name"]),
                    ("Programa", result["diploma"]["name"]),
                    ("Turno", result["schedule"]["name"]),
                    ("Plan", _tuition_plan_label(result.get("tuition_plan"))),
                    ("Inicio de clases", str(result.get("start_date"))),
                    ("Matrícula", f"${fee:,.2f}"),
                    ("Efectivo recibido", f"${float(result.get('cash_received') or 0):,.2f}"),
                    ("Cambio", f"${float(result.get('change') or 0):,.2f}"),
                    ("Primer pago de colegiatura", str(result.get("next_payment_date") or "—")),
                ],
                footer="Conserve este comprobante.",
            )

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
