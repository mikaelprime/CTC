from datetime import date

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QComboBox,
    QLabel,
    QLineEdit,
    QMessageBox,
)

from api_client import ApiError, api
from widgets.animated_button import AnimatedButton
from widgets.crud_page import Column, CrudPage, Field
from widgets.effects import apply_card_shadow


def _fetch():
    return api.get("/payments/")


def _enrollment_options():
    enrollments = api.get("/enrollments/") or []
    return [
        (f"#{e['id']} — {e['student']['full_name']} ({e['diploma']['name']})", e["id"])
        for e in enrollments
    ]


_STATUS_OPTIONS = [("Pendiente", "PENDIENTE"), ("Pagado", "PAGADO")]
_TYPE_OPTIONS = [("Efectivo", "Efectivo"), ("Tarjeta", "Tarjeta"), ("Transferencia", "Transferencia")]


def _create(payload: dict):
    amount = payload["amount"]
    surcharge = payload["surcharge"]
    body = {
        "enrollment_id": payload["enrollment_id"],
        "payment_date": payload["payment_date"],
        "due_date": payload["due_date"],
        "amount": amount,
        "surcharge": surcharge,
        "total": round(amount + surcharge, 2),
        "payment_type": payload["payment_type"],
        "status": payload["status"],
    }
    return api.post("/payments/", json=body)


def _delete(row: dict):
    return api.delete(f"/payments/{row['id']}")


class PaymentsPage(CrudPage):
    def __init__(self, parent=None):
        self.is_cashier = (api.user_role or "").upper() in {"CAJERO", "CASHIER"}
        columns = [
            Column("id", "ID"),
            Column("enrollment_id", "Matrícula", formatter=lambda r: f"#{r['enrollment_id']}"),
            Column("total", "Total", formatter=lambda r: f"${float(r['total']):,.2f}"),
            Column("payment_type", "Método"),
            Column("due_date", "Vencimiento"),
            Column("status", "Estado"),
        ]
        create_spec = None if self.is_cashier else [
            Field("enrollment_id", "Matrícula", kind="combo", options=_enrollment_options),
            Field("payment_date", "Fecha de pago", kind="date"),
            Field("due_date", "Fecha de vencimiento", kind="date"),
            Field("amount", "Monto (USD)", kind="float", default=0.0, maximum=100_000),
            Field("surcharge", "Recargo (USD)", kind="float", default=0.0, maximum=10_000),
            Field("payment_type", "Método de pago", kind="combo", options=lambda: _TYPE_OPTIONS),
            Field("status", "Estado", kind="combo", options=lambda: _STATUS_OPTIONS),
        ]
        super().__init__(
            title="Gestión de Pagos",
            subtitle="Cobranza, conciliación y estado de cuotas",
            columns=columns,
            fetch_fn=_fetch,
            create_spec=create_spec,
            create_fn=_create,
            create_label="Registrar pago",
            delete_fn=_delete,
            empty_message="No hay pagos registrados todavía. Crea primero una inscripción.",
            parent=parent,
        )
        self._add_register_controls()
        if self.is_cashier:
            self._add_collect_button()

    def _add_collect_button(self):
        button = AnimatedButton("Cobrar colegiatura")
        button.setProperty("class", "primary")
        button.clicked.connect(self.collect_payment)
        self.layout().insertWidget(3, button)

    def _add_register_controls(self):
        if (api.user_role or "").upper() not in {"CAJERO", "CASHIER"}:
            return
        panel = QGroupBox("Caja del turno")
        panel.setObjectName("RegisterPanel")
        apply_card_shadow(panel, blur=14, y_offset=6, alpha=55)
        row = QHBoxLayout(panel)
        self.register_status = QLabel("Comprobando caja...")
        self.register_status.setObjectName("RegisterStatus")
        row.addWidget(self.register_status)
        row.addStretch()
        self.open_register_button = AnimatedButton("Abrir caja")
        self.open_register_button.setProperty("class", "primary")
        self.open_register_button.clicked.connect(self.open_register)
        row.addWidget(self.open_register_button)
        self.close_register_button = AnimatedButton("Cerrar caja")
        self.close_register_button.clicked.connect(self.close_register)
        row.addWidget(self.close_register_button)
        self.monthly_button = AnimatedButton("Cierre mensual")
        self.monthly_button.clicked.connect(self.show_monthly_close)
        row.addWidget(self.monthly_button)
        self.layout().insertWidget(2, panel)
        self.refresh_register()

    def refresh_register(self):
        try:
            register = api.get("/cashier/register/current")
        except ApiError:
            self.register_status.setText("Caja cerrada")
            self.open_register_button.setEnabled(True)
            self.close_register_button.setEnabled(False)
            return
        self.register_status.setText(
            f"Caja abierta · Fondo ${float(register['initial_amount']):,.2f} · "
            f"Cobrado ${float(register['collected_amount']):,.2f} · "
            f"Total esperado ${float(register['expected_amount']):,.2f}"
        )
        self.open_register_button.setEnabled(False)
        self.close_register_button.setEnabled(True)

    def show_monthly_close(self):
        month = date.today().month
        year = date.today().year
        try:
            report = api.get(f"/cashier/monthly?year={year}&month={month}")
        except ApiError as exc:
            QMessageBox.critical(self, "No se pudo cargar el cierre mensual", str(exc))
            return
        QMessageBox.information(
            self,
            f"Cierre mensual {report['periodo']}",
            f"Cajas cerradas: {report['cajas_cerradas']}\n"
            f"Total cobrado: ${float(report['total_cobrado_mes']):,.2f}\n"
            f"Efectivo contado: ${float(report['total_efectivo_contado']):,.2f}\n"
            f"Descuadres: ${float(report['total_descuadres_mes']):,.2f}",
        )

    def open_register(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Abrir caja diaria")
        dialog.setMinimumWidth(380)
        form = QFormLayout(dialog)
        intro = QLabel("Define el fondo inicial. Desde ese momento el sistema sumará cada cobro y mostrará el total esperado.")
        intro.setWordWrap(True)
        intro.setObjectName("PaymentHint")
        amount_input = QDoubleSpinBox()
        amount_input.setRange(0, 1000000)
        amount_input.setDecimals(2)
        amount_input.setSuffix(" USD")
        form.addRow(intro)
        form.addRow("Fondo inicial", amount_input)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() != QDialog.Accepted:
            return
        amount = amount_input.value()
        try:
            api.post("/cashier/register/open", json={"initial_amount": amount})
        except ApiError as exc:
            QMessageBox.critical(self, "No se pudo abrir la caja", str(exc))
            return
        self.refresh_register()

    def collect_payment(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Cobro de colegiatura")
        dialog.setMinimumWidth(430)
        form = QFormLayout(dialog)
        enrollment = QComboBox()
        options = _enrollment_options()
        for label, value in options:
            enrollment.addItem(label, value)
        months = QComboBox()
        for number in range(1, 13):
            months.addItem(f"{number} mes{'es' if number != 1 else ''}", number)
        payment_type = QComboBox()
        for label, value in _TYPE_OPTIONS:
            payment_type.addItem(label, value)
        cash = QDoubleSpinBox()
        cash.setRange(0, 1000000)
        cash.setDecimals(2)
        apply_late_fee = QCheckBox("Aplicar recargo por mora si aplica ($3.00)")
        apply_late_fee.setChecked(True)
        due_info = QLabel("Selecciona una matrícula para consultar su vencimiento.")
        due_info.setWordWrap(True)
        due_info.setObjectName("PaymentHint")
        enrollment.currentIndexChanged.connect(
            lambda: self.update_due_info(enrollment, months, due_info)
        )
        months.currentIndexChanged.connect(
            lambda: self.update_due_info(enrollment, months, due_info)
        )
        form.addRow("Estudiante / matrícula", enrollment)
        form.addRow("Plan de pago", months)
        form.addRow("Método", payment_type)
        form.addRow("Efectivo recibido", cash)
        form.addRow(apply_late_fee)
        form.addRow(due_info)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        self.update_due_info(enrollment, months, due_info)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            result = api.post("/payments/collect", json={
                "enrollment_id": enrollment.currentData(),
                "payment_date": date.today().isoformat(),
                "payment_type": payment_type.currentData(),
                "cash_received": cash.value(),
                "months": months.currentData(),
                "apply_late_fee": apply_late_fee.isChecked(),
            })
        except ApiError as exc:
            QMessageBox.critical(self, "No se pudo registrar el cobro", str(exc))
            return
        QMessageBox.information(
            self,
            "Cobro registrado",
            f"Total: ${float(result['total']):,.2f}\n"
            f"Cambio: ${float(result['change']):,.2f}\n"
            f"Próximo pago: {result['next_payment_date']}",
        )
        self.reload()
        self.refresh_register()

    def update_due_info(self, enrollment, months, label):
        if enrollment.currentData() is None:
            return
        try:
            info = api.get(f"/payments/next/{enrollment.currentData()}")
            amount = float(info["monthly_amount"]) * int(months.currentData())
            surcharge = float(info["automatic_surcharge"])
            label.setText(
                f"Vence: {info['due_date']} ({info['days_until_due']} días) · "
                f"Total estimado: ${amount + surcharge:,.2f} "
                f"({'incluye mora de $3.00' if surcharge else 'sin mora'})"
            )
        except ApiError as exc:
            label.setText(str(exc))

    def close_register(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Cierre diario y arqueo")
        dialog.setMinimumWidth(430)
        form = QFormLayout(dialog)
        intro = QLabel("Cuenta el efectivo físico. El sistema comparará ese valor con el total esperado y dejará registrada la auditoría.")
        intro.setWordWrap(True)
        intro.setObjectName("PaymentHint")
        physical = QDoubleSpinBox()
        physical.setRange(0, 1000000)
        physical.setDecimals(2)
        explanation = QLineEdit()
        explanation.setPlaceholderText("Obligatoria si existe diferencia")
        form.addRow(intro)
        form.addRow("Efectivo contado", physical)
        form.addRow("Auditoría", explanation)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            result = api.post("/cashier/register/close", json={
                "physical_amount": physical.value(),
                "explanation": explanation.text().strip() or None,
            })
        except ApiError as exc:
            QMessageBox.critical(self, "No se pudo cerrar la caja", str(exc))
            return
        summary = (
            "CAJA CERRADA\n\n"
            f"Fondo inicial: ${float(result['monto_inicial']):,.2f}\n"
            f"Cobrado por sistema: ${float(result['cobrado_sistema']):,.2f}\n"
            f"Total esperado: ${float(result['esperado_total']):,.2f}\n"
            f"Efectivo contado: ${float(result['reportado_fisico']):,.2f}\n"
            f"Diferencia: ${float(result['diferencia']):,.2f}\n\n"
            f"Auditoría: {result['auditoria_nota']}"
        )
        QMessageBox.information(self, "Cierre diario y arqueo", summary)
        self.refresh_register()