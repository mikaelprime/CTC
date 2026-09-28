"""Pantalla del cajero (PDF): caja del turno, cobro de colegiaturas cada 28
días con "Efectivo:" y "Cambio:", recargo opcional por mora, cobros próximos
y atrasados, comprobantes y cierres de caja diario/mensual."""

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from api_client import ApiError, api
from pages import cash_reports
from widgets.animated_button import AnimatedButton
from widgets.async_worker import AsyncWorker
from widgets.crud_page import Column, CrudPage
from widgets.effects import apply_card_shadow
from widgets.receipt_view import fmt_date, money, open_url, show_payment_ticket, show_receipt
from widgets.report_export import Report, Section, export_report

PAYMENT_TYPES = ["Efectivo", "Tarjeta", "Transferencia"]
CASH = "Efectivo"
_KIND_LABELS = {"MATRICULA": "Matrícula", "COLEGIATURA": "Colegiatura"}
# Billetes y monedas de dólar para el arqueo (igual que el backend).
DENOMINATIONS = ["100.00", "50.00", "20.00", "10.00", "5.00", "1.00", "0.25", "0.10", "0.05", "0.01"]


def receipt_label(row: dict) -> str:
    return f"R-{row['receipt_id']:06d}" if row.get("receipt_id") else f"PAGO-{row['id']:06d}"


def _fetch():
    """Pagos con el nombre del estudiante y del programa (la API de pagos
    solo trae el id de la matrícula)."""
    payments = api.get("/payments/") or []
    enrollments = {e["id"]: e for e in api.get("/enrollments/") or []}
    for payment in payments:
        enrollment = enrollments.get(payment["enrollment_id"])
        payment["student_name"] = enrollment["student"]["full_name"] if enrollment else "—"
        payment["diploma_name"] = enrollment["diploma"]["name"] if enrollment else "—"
        payment["receipt_number"] = receipt_label(payment)
    return payments


def collectable_enrollments() -> list[dict]:
    """Matrículas a las que se les puede cobrar colegiatura."""
    return [
        e for e in api.get("/enrollments/") or []
        if e["status"] in ("ACTIVA", "PENDIENTE")
        and (e.get("installments_total") or 0) > (e.get("installments_paid") or 0)
    ]


def denomination_total(counts: dict[str, int]) -> float:
    return round(sum(float(value) * quantity for value, quantity in counts.items()), 2)


class PaymentsPage(CrudPage):
    def __init__(self, parent=None):
        columns = [
            Column("receipt_number", "Comprobante"),
            Column("student_name", "Estudiante"),
            Column("diploma_name", "Programa"),
            Column("kind", "Concepto", formatter=lambda r: _KIND_LABELS.get(r.get("kind"), r.get("kind") or "—")),
            Column("payment_date", "Fecha de pago", formatter=lambda r: fmt_date(r["payment_date"])),
            Column("due_date", "Cuota del", formatter=lambda r: fmt_date(r["due_date"])),
            Column("total", "Total", formatter=lambda r: money(r["total"])),
            Column("payment_type", "Método"),
            Column("status", "Estado"),
        ]
        super().__init__(
            title="Caja y cobros",
            subtitle="Cobro de colegiaturas cada 28 días, comprobantes y cierre de caja",
            columns=columns,
            fetch_fn=_fetch,
            # Un pago cobrado no se borra ni se edita: el administrador anula
            # el comprobante con motivo y queda en el historial.
            extra_actions=[
                ("Ticket", lambda row: show_payment_ticket(self, row["id"]), lambda row: True),
                ("Anular", self.void_payment, lambda row: api.is_admin() and row.get("status") == "PAGADO"),
            ],
            empty_message="No hay pagos registrados todavía.",
            parent=parent,
        )
        self._add_register_panel()
        self._add_actions()
        self._add_upcoming_panel()

    # ------------------------------------------------------------ caja

    def _add_register_panel(self):
        panel = QGroupBox("Mi caja del turno")
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
        self.register_report_button = AnimatedButton("Ver cobros de mi caja")
        self.register_report_button.clicked.connect(self.show_current_register)
        row.addWidget(self.register_report_button)
        self.close_register_button = AnimatedButton("Cerrar caja (arqueo)")
        self.close_register_button.clicked.connect(self.close_register)
        row.addWidget(self.close_register_button)
        self.layout().insertWidget(2, panel)
        self._register_id = None
        self.refresh_register()

    def refresh_register(self):
        try:
            register = api.get("/cashier/register/current")
        except ApiError:
            self._register_id = None
            self.register_status.setText("Caja cerrada · ábrela para poder cobrar")
            self.open_register_button.setEnabled(True)
            self.close_register_button.setEnabled(False)
            self.register_report_button.setEnabled(False)
            return
        self._register_id = register["id"]
        self.register_status.setText(
            f"Caja #{register['id']} abierta · Fondo {money(register['initial_amount'])} · "
            f"Cobrado {money(register['collected_amount'])} "
            f"(efectivo {money(register['cash_amount'])}) · "
            f"Efectivo esperado {money(register['expected_amount'])}"
        )
        self.open_register_button.setEnabled(False)
        self.close_register_button.setEnabled(True)
        self.register_report_button.setEnabled(True)

    def open_register(self):
        amount, ok = QInputDialog.getDouble(
            self, "Abrir caja diaria",
            "Fondo inicial (efectivo con el que empieza la caja):", 0.0, 0.0, 100000.0, 2,
        )
        if not ok:
            return
        try:
            api.post("/cashier/register/open", json={"initial_amount": amount})
        except ApiError as exc:
            QMessageBox.critical(self, "No se pudo abrir la caja", str(exc))
            return
        self.refresh_register()

    def show_current_register(self):
        if self._register_id is None:
            return
        try:
            cash_reports.open_register_report(self, self._register_id)
        except ApiError as exc:
            QMessageBox.critical(self, "No se pudo cargar la caja", str(exc))

    def close_register(self):
        """Cierre diario con arqueo por denominación (PDF punto 5): el cajero
        cuenta billetes y monedas y el sistema lo compara con lo esperado."""
        try:
            register = api.get("/cashier/register/current")
        except ApiError as exc:
            QMessageBox.critical(self, "No se pudo cerrar la caja", str(exc))
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Cierre de caja y arqueo")
        dialog.setMinimumWidth(460)
        layout = QVBoxLayout(dialog)
        intro = QLabel(
            "Cuenta los billetes y monedas de la gaveta. El sistema compara el total con el "
            "efectivo esperado (fondo inicial + cobros en efectivo)."
        )
        intro.setWordWrap(True)
        intro.setObjectName("PaymentHint")
        layout.addWidget(intro)
        grid = QGridLayout()
        spins: dict[str, QSpinBox] = {}
        for index, value in enumerate(DENOMINATIONS):
            spin = QSpinBox()
            spin.setRange(0, 100000)
            spins[value] = spin
            label = f"Billete ${float(value):,.0f}" if float(value) >= 1 else f"Moneda ${float(value):.2f}"
            row, col = divmod(index, 2)
            grid.addWidget(QLabel(label), row, col * 2)
            grid.addWidget(spin, row, col * 2 + 1)
        layout.addLayout(grid)
        form = QFormLayout()
        expected = float(register["expected_amount"])
        counted_label = QLabel("$0.00")
        diff_label = QLabel()
        diff_label.setObjectName("PaymentHint")
        explanation = QLineEdit()
        explanation.setMaxLength(500)
        explanation.setPlaceholderText("Obligatoria si hay sobrante o faltante")
        form.addRow("Efectivo esperado:", QLabel(money(expected)))
        form.addRow("Efectivo contado:", counted_label)
        form.addRow("Diferencia:", diff_label)
        form.addRow("Justificación:", explanation)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Cerrar caja")
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        def recalculate():
            counted = denomination_total({k: s.value() for k, s in spins.items()})
            counted_label.setText(money(counted))
            diff = round(counted - expected, 2)
            diff_label.setText(
                "Caja cuadrada" if diff == 0 else (f"Sobrante {money(diff)}" if diff > 0 else f"Faltante {money(-diff)}")
            )

        for spin in spins.values():
            spin.valueChanged.connect(recalculate)
        recalculate()
        if dialog.exec() != QDialog.Accepted:
            return
        counts = {k: s.value() for k, s in spins.items() if s.value()}
        body = {"cash_count": counts, "explanation": explanation.text().strip() or None}
        if not counts:
            body = {"physical_amount": 0, "explanation": body["explanation"]}
        try:
            result = api.post("/cashier/register/close", json=body)
        except ApiError as exc:
            QMessageBox.critical(self, "No se pudo cerrar la caja", str(exc))
            return
        self.refresh_register()
        QMessageBox.information(
            self, "Caja cerrada",
            f"Esperado {money(result['esperado_total'])} · Contado {money(result['reportado_fisico'])} · "
            f"Diferencia {money(result['diferencia'])}\n\nA continuación se muestra el reporte de cierre.",
        )
        try:
            cash_reports.open_register_report(self, result["register_id"])
        except ApiError as exc:
            QMessageBox.critical(self, "No se pudo cargar el reporte", str(exc))

    # ------------------------------------------------------------ acciones

    def _add_actions(self):
        row = QHBoxLayout()
        collect = AnimatedButton("💵 Cobrar colegiatura")
        collect.setProperty("class", "primary")
        collect.clicked.connect(lambda: self.collect_payment())
        row.addWidget(collect)
        daily = AnimatedButton("Cierre del día")
        daily.clicked.connect(self.show_daily_close)
        row.addWidget(daily)
        monthly = AnimatedButton("Cierre mensual")
        monthly.clicked.connect(self.show_monthly_close)
        row.addWidget(monthly)
        export = AnimatedButton("Exportar pagos")
        export.clicked.connect(self.export_payments)
        row.addWidget(export)
        row.addStretch()
        self.layout().insertLayout(3, row)

    def show_daily_close(self):
        try:
            label = "Todos los cajeros" if api.is_admin() else (api.full_name or "Mi caja")
            cash_reports.open_daily_report(self, cashier_label=label)
        except ApiError as exc:
            QMessageBox.critical(self, "No se pudo cargar el cierre del día", str(exc))

    def show_monthly_close(self):
        today = date.today()
        try:
            label = "Todos los cajeros" if api.is_admin() else (api.full_name or "Mi caja")
            cash_reports.open_monthly_report(self, today.year, today.month, cashier_label=label)
        except ApiError as exc:
            QMessageBox.critical(self, "No se pudo cargar el cierre mensual", str(exc))

    def export_payments(self):
        rows = self.visible_rows()
        paid = [r for r in rows if r["status"] == "PAGADO"]
        export_report(self, Report(
            title="Reporte de pagos",
            subtitle=f"{len(rows)} registros" + (
                f" · filtro: “{self.search_input.text().strip()}”" if self.search_input.text().strip() else ""
            ),
            summary=[
                ("Total cobrado", sum(float(r["total"]) for r in paid)),
                ("Recargos", sum(float(r.get("surcharge") or 0) for r in paid)),
                ("Anulado", sum(float(r["total"]) for r in rows if r["status"] == "ANULADO")),
                ("Cuotas y matrículas cobradas", len(paid)),
            ],
            sections=[Section(
                "Pagos",
                ["Comprobante", "Estudiante", "Programa", "Concepto", "Fecha de pago", "Cuota del",
                 "Monto", "Recargo", "Total", "Método", "Estado", "Observaciones"],
                [
                    [r["receipt_number"], r["student_name"], r["diploma_name"],
                     _KIND_LABELS.get(r.get("kind"), r.get("kind")), fmt_date(r["payment_date"]),
                     fmt_date(r["due_date"]), float(r["amount"]), float(r.get("surcharge") or 0),
                     float(r["total"]), r["payment_type"], r["status"], r.get("observations") or ""]
                    for r in rows
                ],
                money={6, 7, 8},
            )],
        ), "Pagos")

    def void_payment(self, row: dict) -> None:
        reason, ok = QInputDialog.getText(
            self,
            "Anular comprobante",
            f"Motivo para anular el comprobante {row['receipt_number']} de {row['student_name']}.\n"
            "Se anula el comprobante completo (todas sus cuotas): queda en el historial,\n"
            "deja de sumar en caja y las cuotas vuelven a quedar por cobrar.",
        )
        if not ok:
            return
        try:
            api.post(f"/payments/{row['id']}/void", json={"reason": reason})
        except ApiError as exc:
            QMessageBox.critical(self, "No se pudo anular", str(exc))
            return
        self.reload()
        self.refresh_register()

    # ------------------------------------------------------------ próximos

    def _add_upcoming_panel(self):
        """PDF punto 6: "muestra al cajero o administrador los pagos próximos
        para que esté pendiente de los cobros" — siempre visible aquí."""
        box = QGroupBox("Cobros próximos (7 días) y atrasados")
        layout = QVBoxLayout(box)
        self.upcoming_table = QTableWidget(0, 8)
        self.upcoming_table.setHorizontalHeaderLabels(
            ["Estudiante", "Programa", "Vence", "Situación", "Cuotas vencidas", "Monto a cobrar", "Aviso enviado", "Responsable / contacto"]
        )
        self.upcoming_table.verticalHeader().setVisible(False)
        self.upcoming_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.upcoming_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.upcoming_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.upcoming_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.upcoming_table.setMaximumHeight(190)
        self.upcoming_table.doubleClicked.connect(lambda _index: self.collect_selected_upcoming())
        layout.addWidget(self.upcoming_table)
        buttons = QHBoxLayout()
        self.upcoming_status = QLabel("Cargando…")
        self.upcoming_status.setObjectName("PageSubtitle")
        buttons.addWidget(self.upcoming_status)
        buttons.addStretch()
        collect = AnimatedButton("Cobrar seleccionado")
        collect.clicked.connect(self.collect_selected_upcoming)
        whatsapp = AnimatedButton("Avisar por WhatsApp")
        whatsapp.clicked.connect(self.whatsapp_selected_upcoming)
        export = AnimatedButton("Exportar lista")
        export.clicked.connect(self.export_upcoming)
        for button in (collect, whatsapp, export):
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.layout().insertWidget(4, box)
        self._upcoming: list[dict] = []
        self.reload_upcoming()

    def reload(self) -> None:
        super().reload()
        if hasattr(self, "upcoming_table"):
            self.reload_upcoming()
            self.refresh_register()

    def reload_upcoming(self):
        worker = AsyncWorker(lambda: api.get("/reports/upcoming-payments?days=7") or [], self)
        self._upcoming_worker = worker
        worker.succeeded.connect(self._fill_upcoming)
        worker.failed.connect(lambda message: self.upcoming_status.setText(message))
        worker.start()

    def _fill_upcoming(self, rows: list[dict]):
        self._upcoming = rows
        self.upcoming_table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            days = int(row["days_remaining"])
            situation = f"Atrasado {abs(days)} día(s)" if days < 0 else ("Vence hoy" if days == 0 else f"En {days} día(s)")
            contact = " · ".join(filter(None, [row.get("responsible_name"), row.get("phone")]))
            values = [
                row["student_name"], row["diploma_name"], fmt_date(row["due_date"]), situation,
                str(row["overdue_installments"]), money(row["amount_owed"]),
                "Sí" if row["reminder_sent"] else "No", contact or "—",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if row["is_overdue"]:
                    item.setForeground(QBrush(QColor("#dc2626")))
                self.upcoming_table.setItem(index, column, item)
        overdue = sum(1 for r in rows if r["is_overdue"])
        self.upcoming_status.setText(
            f"{overdue} atrasado(s) · {len(rows) - overdue} por vencer · doble clic para cobrar"
            if rows else "No hay cobros próximos ni atrasados."
        )

    def _selected_upcoming(self) -> dict | None:
        index = self.upcoming_table.currentRow()
        if index < 0 or index >= len(self._upcoming):
            QMessageBox.information(self, "Selecciona un estudiante", "Selecciona una fila de la lista de cobros próximos.")
            return None
        return self._upcoming[index]

    def collect_selected_upcoming(self):
        row = self._selected_upcoming()
        if row:
            self.collect_payment(row["enrollment_id"])

    def whatsapp_selected_upcoming(self):
        row = self._selected_upcoming()
        if not row:
            return
        if not row.get("whatsapp_url"):
            QMessageBox.warning(self, "Sin WhatsApp", "El estudiante no tiene un número de WhatsApp o contacto válido.")
            return
        open_url(row["whatsapp_url"])

    def export_upcoming(self):
        rows = self._upcoming
        export_report(self, Report(
            title="Cobros próximos (7 días) y atrasados",
            summary=[
                ("Matrículas atrasadas", sum(1 for r in rows if r["is_overdue"])),
                ("Por vencer en 7 días", sum(1 for r in rows if not r["is_overdue"])),
                ("Monto por cobrar", sum(float(r["amount_owed"]) for r in rows)),
            ],
            sections=[Section(
                "Detalle",
                ["Matrícula", "Estudiante", "Programa", "Vence", "Días", "Cuotas vencidas", "Monto", "Aviso enviado", "Contacto"],
                [[f"#{r['enrollment_id']}", r["student_name"], r["diploma_name"], fmt_date(r["due_date"]),
                  int(r["days_remaining"]), int(r["overdue_installments"]), float(r["amount_owed"]),
                  "Sí" if r["reminder_sent"] else "No", r.get("phone") or ""] for r in rows],
                money={6},
            )],
        ), "Cobros proximos")

    # ------------------------------------------------------------ cobro

    def collect_payment(self, enrollment_id: int | None = None):
        """PDF puntos 2 y 4: cobro de colegiatura con "Efectivo:" y "Cambio:"
        calculado al instante, y opción de aplicar el recargo por mora."""
        if self._register_id is None:
            QMessageBox.warning(self, "Caja cerrada", "Abre tu caja antes de cobrar: todo cobro debe quedar en un arqueo.")
            return
        try:
            options = collectable_enrollments()
        except ApiError as exc:
            QMessageBox.critical(self, "No se pudieron cargar las matrículas", str(exc))
            return
        if not options:
            QMessageBox.information(self, "Sin cobros", "No hay matrículas con colegiaturas por cobrar.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Cobro de colegiatura")
        dialog.setMinimumWidth(520)
        form = QFormLayout(dialog)
        enrollment = QComboBox()
        enrollment.setEditable(True)
        enrollment.setInsertPolicy(QComboBox.NoInsert)
        for e in sorted(options, key=lambda e: e["student"]["full_name"]):
            enrollment.addItem(f"{e['student']['full_name']} — {e['diploma']['name']} (#{e['id']})", e["id"])
        completer = enrollment.completer()
        completer.setFilterMode(Qt.MatchContains)
        completer.setCompletionMode(QCompleter.PopupCompletion)
        if enrollment_id is not None and enrollment.findData(enrollment_id) >= 0:
            enrollment.setCurrentIndex(enrollment.findData(enrollment_id))
        months = QComboBox()
        payment_type = QComboBox()
        payment_type.addItems(PAYMENT_TYPES)
        cash = QDoubleSpinBox()
        cash.setRange(0, 100000)
        cash.setDecimals(2)
        cash.setPrefix("$ ")
        apply_late_fee = QCheckBox("Aplicar recargo por mora")
        apply_late_fee.setChecked(True)
        due_info = QLabel()
        due_info.setWordWrap(True)
        due_info.setObjectName("PaymentHint")
        total_label = QLabel("—")
        total_label.setObjectName("SummaryValue")
        change_label = QLabel("—")
        change_label.setObjectName("SummaryValue")
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Cobrar")
        state = {"info": None}

        def recalculate():
            info = state["info"]
            ok_button = buttons.button(QDialogButtonBox.Ok)
            if info is None or months.currentData() is None:
                total_label.setText("—")
                change_label.setText("—")
                ok_button.setEnabled(False)
                return
            surcharge = float(info["automatic_surcharge"]) if apply_late_fee.isChecked() else 0.0
            total = float(info["monthly_amount"]) * int(months.currentData()) + surcharge
            total_label.setText(money(total) + (f"  (incluye recargo {money(surcharge)})" if surcharge else ""))
            is_cash = payment_type.currentText() == CASH
            cash.setEnabled(is_cash)
            if not is_cash:
                cash.setValue(total)
            change = cash.value() - total
            change_label.setText(money(change) if change >= 0 else f"Faltan {money(-change)}")
            ok_button.setEnabled(change >= -0.001)

        def reload_info():
            state["info"] = None
            months.clear()
            if enrollment.currentData() is None:
                due_info.setText("Selecciona un estudiante.")
                recalculate()
                return
            try:
                info = api.get(f"/payments/next/{enrollment.currentData()}")
            except ApiError as exc:
                due_info.setText(str(exc))
                recalculate()
                return
            state["info"] = info
            remaining = int(info["installments_remaining"])
            for number in range(1, min(12, remaining) + 1):
                months.addItem(f"{number} cuota{'s' if number != 1 else ''}", number)
            if info["overdue_installments"]:
                months.setCurrentIndex(min(int(info["overdue_installments"]), months.count()) - 1)
            days = info["days_until_due"]
            when = f"atrasada {abs(days)} día(s)" if days < 0 else ("vence hoy" if days == 0 else f"vence en {days} día(s)")
            apply_late_fee.setEnabled(bool(info["is_overdue"]))
            apply_late_fee.setText(
                f"Aplicar recargo por mora ({money(info['automatic_surcharge'])})"
                if info["is_overdue"] else "Aplicar recargo por mora (no aplica: está al día)"
            )
            due_info.setText(
                f"Cuota {int(info['installments_paid']) + 1} de {info['installments_total']} · "
                f"vence {fmt_date(info['due_date'])} ({when}) · cuota {money(info['monthly_amount'])}"
                + (f"\nCuotas vencidas: {info['overdue_installments']} · adeuda {money(info['amount_overdue'])}"
                   if info["overdue_installments"] else "")
                + f"\nEstado: {info['status']}"
            )
            recalculate()

        enrollment.currentIndexChanged.connect(reload_info)
        months.currentIndexChanged.connect(recalculate)
        payment_type.currentIndexChanged.connect(recalculate)
        apply_late_fee.toggled.connect(recalculate)
        cash.valueChanged.connect(recalculate)
        form.addRow("Estudiante (escribe para buscar)", enrollment)
        form.addRow(due_info)
        form.addRow("Cuotas a pagar", months)
        form.addRow("Método de pago", payment_type)
        form.addRow(apply_late_fee)
        form.addRow("Total a cobrar:", total_label)
        form.addRow("Efectivo:", cash)
        form.addRow("Cambio:", change_label)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        reload_info()
        cash.setFocus()
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            result = api.post("/payments/collect", json={
                "enrollment_id": enrollment.currentData(),
                "payment_type": payment_type.currentText(),
                "cash_received": cash.value(),
                "months": months.currentData(),
                "apply_late_fee": apply_late_fee.isChecked() and apply_late_fee.isEnabled(),
            })
        except ApiError as exc:
            QMessageBox.critical(self, "No se pudo registrar el cobro", str(exc))
            return
        self.reload()
        show_receipt(self, result["receipt_id"], "Cobro registrado. El comprobante también se envió por correo.")
