from datetime import date

from PySide6.QtWidgets import (
    QCheckBox,
    QInputDialog,
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
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from api_client import ApiError, api
from widgets.animated_button import AnimatedButton
from widgets.crud_page import Column, CrudPage, Field
from widgets.effects import apply_card_shadow
from widgets.report_export import Report, Section, export_report
from widgets.ticket_printer import print_ticket, save_ticket_pdf


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


_KIND_LABELS = {"MATRICULA": "Matrícula", "COLEGIATURA": "Colegiatura"}


class PaymentsPage(CrudPage):
    def __init__(self, parent=None):
        self.is_cashier = (api.user_role or "").upper() in {"CAJERO", "CASHIER"}
        columns = [
            Column("id", "ID"),
            Column("enrollment_id", "Matrícula", formatter=lambda r: f"#{r['enrollment_id']}"),
            Column("total", "Total", formatter=lambda r: f"${float(r['total']):,.2f}"),
            Column("kind", "Concepto", formatter=lambda r: _KIND_LABELS.get(r.get("kind"), r.get("kind") or "—")),
            Column("payment_type", "Método"),
            Column("due_date", "Vencimiento"),
            Column("status", "Estado"),
        ]
        create_spec = None if self.is_cashier else [
            Field("enrollment_id", "Matrícula", kind="combo", options=_enrollment_options),
            Field("payment_date", "Fecha de pago", kind="date", min_days=-365, max_days=0),
            Field("due_date", "Fecha de vencimiento", kind="date", min_days=-730, max_days=730),
            Field("amount", "Monto (USD)", kind="float", default=0.0, maximum=10_000),
            Field("surcharge", "Recargo (USD)", kind="float", default=0.0, maximum=1_000),
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
            # Un pago cobrado no se borra (descuadraría la caja): el admin lo
            # anula con motivo y queda en el historial. Solo las cuotas
            # PENDIENTE (nunca cobradas) se pueden eliminar.
            extra_actions=[
                ("Anular", self.void_payment, lambda row: api.is_admin() and row.get("status") == "PAGADO"),
                ("Eliminar", self.delete_pending, lambda row: api.is_admin() and row.get("status") == "PENDIENTE"),
            ],
            empty_message="No hay pagos registrados todavía. Crea primero una inscripción.",
            parent=parent,
        )
        self._add_register_controls()
        if self.is_cashier:
            self._add_collect_button()
        self._add_upcoming_button()
        self._add_export_button()

    def _add_export_button(self):
        button = AnimatedButton("Exportar pagos")
        button.clicked.connect(self.export_payments)
        self.layout().insertWidget(3, button)

    def export_payments(self):
        rows = self.visible_rows()
        paid = [r for r in rows if r["status"] == "PAGADO"]
        report = Report(
            title="Reporte de pagos",
            subtitle=f"{len(rows)} registros" + (
                f" · filtro: “{self.search_input.text().strip()}”" if self.search_input.text().strip() else ""
            ),
            summary=[
                ("Total cobrado", sum(float(r["total"]) for r in paid)),
                ("Recargos", sum(float(r.get("surcharge") or 0) for r in paid)),
                ("Anulado", sum(float(r["total"]) for r in rows if r["status"] == "ANULADO")),
                ("Pagos cobrados", len(paid)),
            ],
            sections=[Section(
                "Pagos",
                ["ID", "Inscripción", "Concepto", "Fecha de pago", "Vence", "Monto", "Recargo", "Total",
                 "Método", "Estado", "Observaciones"],
                [
                    [r["id"], r["enrollment_id"], _KIND_LABELS.get(r.get("kind"), r.get("kind")), r["payment_date"],
                     r["due_date"], float(r["amount"]), float(r.get("surcharge") or 0), float(r["total"]),
                     r["payment_type"], r["status"], r.get("observations") or ""]
                    for r in rows
                ],
                money={5, 6, 7},
            )],
        )
        export_report(self, report, "Pagos")

    def _add_upcoming_button(self):
        # PDF: "muestra al cajero o administrador los pagos próximos".
        button = AnimatedButton("Próximos cobros")
        button.clicked.connect(self.show_upcoming)
        self.layout().insertWidget(3, button)

    def show_upcoming(self):
        try:
            rows = api.get("/reports/upcoming-payments?days=7") or []
        except ApiError as exc:
            QMessageBox.critical(self, "No se pudieron cargar los cobros próximos", str(exc))
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Cobros próximos (7 días) y atrasados")
        dialog.setMinimumSize(720, 380)
        layout = QVBoxLayout(dialog)
        if not rows:
            layout.addWidget(QLabel("No hay cobros próximos ni matrículas atrasadas."))
        headers = ["Matrícula", "Estudiante", "Programa", "Vence", "Días", "Monto", "Estado"]
        table = QTableWidget(len(rows), len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        for index, row in enumerate(rows):
            days = int(row["days_remaining"])
            values = [
                f"#{row['enrollment_id']}",
                row["student_name"],
                row["diploma_name"],
                str(row["due_date"]),
                f"Atrasado {abs(days)}" if days < 0 else ("Hoy" if days == 0 else str(days)),
                f"${float(row['amount']):,.2f}",
                row["status"],
            ]
            for column, value in enumerate(values):
                table.setItem(index, column, QTableWidgetItem(value))
        table.resizeColumnsToContents()
        layout.addWidget(table)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        export = AnimatedButton("Exportar Excel / PDF")
        export.clicked.connect(lambda: export_report(dialog, Report(
            title="Cobros próximos (7 días) y atrasados",
            summary=[
                ("Matrículas atrasadas", sum(1 for r in rows if r["is_overdue"])),
                ("Por vencer en 7 días", sum(1 for r in rows if not r["is_overdue"])),
                ("Monto por cobrar", sum(float(r["amount"]) for r in rows)),
            ],
            sections=[Section(
                "Detalle", headers,
                [[f"#{r['enrollment_id']}", r["student_name"], r["diploma_name"], str(r["due_date"]),
                  int(r["days_remaining"]), float(r["amount"]), r["status"]] for r in rows],
                money={5},
            )],
        ), "Cobros proximos"))
        buttons.addButton(export, QDialogButtonBox.ActionRole)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()

    def void_payment(self, row: dict) -> None:
        reason, ok = QInputDialog.getText(
            self,
            "Anular pago",
            f"Motivo para anular el pago #{row['id']} (${float(row['total']):,.2f}).\n"
            "Queda en el historial y la cuota vuelve a quedar por cobrar.",
        )
        if not ok:
            return
        try:
            api.post(f"/payments/{row['id']}/void", json={"reason": reason})
        except ApiError as exc:
            QMessageBox.critical(self, "No se pudo anular", str(exc))
            return
        self.reload()

    def delete_pending(self, row: dict) -> None:
        if QMessageBox.question(self, "Confirmar", f"¿Eliminar la cuota pendiente #{row['id']}?") != QMessageBox.Yes:
            return
        try:
            _delete(row)
        except ApiError as exc:
            QMessageBox.critical(self, "No se pudo eliminar", str(exc))
            return
        self.reload()

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
        cash.setPrefix("$ ")
        apply_late_fee = QCheckBox("Aplicar recargo por mora (si está vencida)")
        apply_late_fee.setChecked(True)
        due_info = QLabel("Selecciona una matrícula para consultar su vencimiento.")
        due_info.setWordWrap(True)
        due_info.setObjectName("PaymentHint")
        # PDF punto 4: el cajero digita el "Efectivo:" y el sistema calcula
        # el "Cambio:" al instante, antes de confirmar el cobro.
        total_label = QLabel("$0.00")
        change_label = QLabel("$0.00")
        change_label.setObjectName("PaymentHint")
        state = {"info": None}

        def recalculate():
            info = state["info"]
            if info is None:
                total_label.setText("—")
                change_label.setText("—")
                return
            surcharge = float(info["automatic_surcharge"]) if apply_late_fee.isChecked() else 0.0
            total = float(info["monthly_amount"]) * int(months.currentData()) + surcharge
            total_label.setText(
                f"${total:,.2f}" + (f"  (incluye mora ${surcharge:,.2f})" if surcharge else "")
            )
            change = cash.value() - total
            change_label.setText(
                f"${change:,.2f}" if change >= 0 else f"Faltan ${-change:,.2f}"
            )
            buttons.button(QDialogButtonBox.Ok).setEnabled(change >= 0)

        def reload_info():
            state["info"] = self.update_due_info(enrollment, due_info)
            recalculate()

        enrollment.currentIndexChanged.connect(reload_info)
        months.currentIndexChanged.connect(recalculate)
        apply_late_fee.toggled.connect(recalculate)
        cash.valueChanged.connect(recalculate)
        form.addRow("Estudiante / matrícula", enrollment)
        form.addRow("Plan de pago", months)
        form.addRow("Método", payment_type)
        form.addRow(apply_late_fee)
        form.addRow(due_info)
        form.addRow("Total a cobrar:", total_label)
        form.addRow("Efectivo:", cash)
        form.addRow("Cambio:", change_label)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        reload_info()
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
        self._show_collect_result(enrollment.currentText(), result)
        self.reload()
        self.refresh_register()

    def _show_collect_result(self, enrollment_label: str, result: dict) -> None:
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Information)
        box.setWindowTitle("Cobro registrado")
        box.setText(
            f"Total: ${float(result['total']):,.2f}\n"
            f"Cambio: ${float(result['change']):,.2f}\n"
            f"Próximo pago: {result['next_payment_date']}"
        )
        print_button = box.addButton("Imprimir ticket", QMessageBox.ActionRole)
        pdf_button = box.addButton("Guardar ticket PDF", QMessageBox.ActionRole)
        box.addButton(QMessageBox.Ok)
        box.exec()
        if box.clickedButton() in (print_button, pdf_button):
            action = print_ticket if box.clickedButton() is print_button else save_ticket_pdf
            action(
                self,
                "Comprobante de pago",
                [
                    ("Matrícula", enrollment_label),
                    ("Meses pagados", str(result["months_paid"])),
                    ("Monto", f"${float(result['amount']):,.2f}"),
                    ("Recargo", f"${float(result['surcharge']):,.2f}"),
                    ("Total", f"${float(result['total']):,.2f}"),
                    ("Efectivo recibido", f"${float(result['cash_received']):,.2f}"),
                    ("Cambio", f"${float(result['change']):,.2f}"),
                    ("Próximo pago", str(result["next_payment_date"])),
                ],
                footer="Conserve este comprobante.",
            )

    def update_due_info(self, enrollment, label):
        if enrollment.currentData() is None:
            return None
        try:
            info = api.get(f"/payments/next/{enrollment.currentData()}")
        except ApiError as exc:
            label.setText(str(exc))
            return None
        days = int(info["days_until_due"])
        when = f"atrasada {abs(days)} días" if days < 0 else f"en {days} días"
        label.setText(
            f"Vence: {info['due_date']} ({when}) · "
            f"Cuota: ${float(info['monthly_amount']):,.2f} · Estado: {info.get('status', '—')}"
        )
        return info

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