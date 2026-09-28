from datetime import date

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from api_client import ApiError, api
from pages import cash_reports
from widgets.animated_button import AnimatedButton
from widgets.crud_page import Field, RecordDialog
from widgets.receipt_view import money


class CashiersPage(QWidget):
    """Administración de cajeros y auditoría de cajas: cada apertura y cierre
    con su arqueo, y los cierres diario y mensual (PDF punto 5)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        header = QLabel("Cajeros y cierres de caja")
        header.setObjectName("PageTitle")
        sub = QLabel("Usuarios cajero, aperturas, cierres con arqueo, cierre diario y mensual")
        sub.setObjectName("PageSubtitle")
        layout.addWidget(header)
        layout.addWidget(sub)

        # -------------------------------------------------- cajeros
        users_box = QGroupBox("Cajeros")
        users_layout = QVBoxLayout(users_box)
        add_button = AnimatedButton("➕ Crear cajero")
        add_button.setProperty("class", "primary")
        add_button.clicked.connect(self.create_cashier)
        users_layout.addWidget(add_button)
        # Desactivar a quien deja de trabajar (no se borra: sus cobros siguen
        # en los reportes) y restablecer contraseñas (quedan temporales).
        self.cashiers_table = QTableWidget()
        self.cashiers_table.setColumnCount(4)
        self.cashiers_table.setHorizontalHeaderLabels(["Cajero", "Correo", "Estado", "Acciones"])
        self.cashiers_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.cashiers_table.verticalHeader().setVisible(False)
        self.cashiers_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.cashiers_table.setMaximumHeight(180)
        users_layout.addWidget(self.cashiers_table)
        layout.addWidget(users_box)

        # -------------------------------------------------- cierres
        reports_box = QGroupBox("Cierres de caja")
        reports_layout = QHBoxLayout(reports_box)
        self.cashier_filter = QComboBox()
        self.cashier_filter.addItem("Todos los cajeros", None)
        self.day = QDateEdit(QDate.currentDate())
        self.day.setCalendarPopup(True)
        self.day.setDisplayFormat("dd/MM/yyyy")
        self.day.setMaximumDate(QDate.currentDate())
        daily_button = AnimatedButton("Ver cierre del día")
        daily_button.clicked.connect(self.show_daily)
        self.month = QComboBox()
        for number in range(1, 13):
            self.month.addItem(f"{number:02d}", number)
        self.month.setCurrentIndex(date.today().month - 1)
        self.year = QSpinBox()
        self.year.setRange(2020, 2100)
        self.year.setValue(date.today().year)
        monthly_button = AnimatedButton("Ver cierre mensual")
        monthly_button.setProperty("class", "primary")
        monthly_button.clicked.connect(self.show_monthly)
        for widget in (QLabel("Cajero"), self.cashier_filter, QLabel("Día"), self.day, daily_button,
                       QLabel("Mes"), self.month, QLabel("Año"), self.year, monthly_button):
            reports_layout.addWidget(widget)
        reports_layout.addStretch()
        layout.addWidget(reports_box)

        # -------------------------------------------------- cajas
        layout.addWidget(QLabel("Historial de cajas (doble clic o «Ver reporte» para el detalle de cobros)"))
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels(
            ["Caja", "Cajero", "Apertura", "Cierre", "Fondo", "Esperado", "Contado", "Diferencia", "Justificación", ""]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.doubleClicked.connect(lambda index: self.show_register(self._registers[index.row()]["id"]))
        layout.addWidget(self.table)
        self.status = QLabel("")
        self.status.setObjectName("PageSubtitle")
        layout.addWidget(self.status)
        self._registers: list[dict] = []
        self.reload()

    # -------------------------------------------------- cajeros

    def create_cashier(self):
        fields = [
            Field("full_name", "Nombre completo", regex=r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ' \-]*$",
                  max_length=150, placeholder="Nombre y apellido", required=True),
            Field("email", "Correo", regex=r"^\S*$", max_length=120, required=True),
            Field("password", "Contraseña temporal", regex=r"^\S*$", max_length=128,
                  placeholder="Mínimo 6, con letras y números", required=True),
            # Un cajero es un empleado mayor de edad: el calendario no permite
            # elegir hoy, una fecha futura ni menos de 18 años.
            Field("birth_date", "Fecha de nacimiento", kind="date",
                  min_days=-365 * 80, max_days=-(365 * 18 + 5), default_days=-365 * 25),
        ]
        dialog = RecordDialog(
            "Crear cajero", fields, self,
            submit=lambda values: api.post("/users/cashiers", json=values),
        )
        dialog.inputs["password"].setEchoMode(QLineEdit.Password)
        if dialog.exec() != QDialog.Accepted:
            return
        QMessageBox.information(
            self, "Cajero creado",
            "El cajero ya puede iniciar sesión. Al entrar por primera vez el sistema le pedirá cambiar la contraseña.",
        )
        self.reload()

    def reload_cashiers(self):
        try:
            cashiers = api.get("/users/cashiers") or []
        except ApiError as exc:
            self.status.setText(str(exc))
            return
        selected = self.cashier_filter.currentData()
        self.cashier_filter.blockSignals(True)
        self.cashier_filter.clear()
        self.cashier_filter.addItem("Todos los cajeros", None)
        for cashier in cashiers:
            self.cashier_filter.addItem(cashier["full_name"], cashier["id"])
        if selected is not None and self.cashier_filter.findData(selected) >= 0:
            self.cashier_filter.setCurrentIndex(self.cashier_filter.findData(selected))
        self.cashier_filter.blockSignals(False)

        self.cashiers_table.setRowCount(len(cashiers))
        self.cashiers_table.verticalHeader().setDefaultSectionSize(40)
        for index, cashier in enumerate(cashiers):
            active = cashier["is_active"]
            state = "Activo" if active else "Desactivado"
            if active and cashier.get("must_change_password"):
                state += " · contraseña temporal"
            for column, value in enumerate([cashier["full_name"], cashier["email"], state]):
                self.cashiers_table.setItem(index, column, QTableWidgetItem(value))
            cell = QWidget()
            cell_layout = QHBoxLayout(cell)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            toggle = QPushButton("Desactivar" if active else "Activar")
            toggle.setStyleSheet("padding: 3px 10px;")
            toggle.clicked.connect(lambda _c=False, row=cashier: self.toggle_cashier(row))
            reset = QPushButton("Restablecer contraseña")
            reset.setStyleSheet("padding: 3px 10px;")
            reset.clicked.connect(lambda _c=False, row=cashier: self.reset_password(row))
            cell_layout.addWidget(toggle)
            cell_layout.addWidget(reset)
            cell_layout.addStretch()
            self.cashiers_table.setCellWidget(index, 3, cell)

    def toggle_cashier(self, cashier):
        action = "desactivar" if cashier["is_active"] else "activar"
        detail = (
            "\nNo podrá iniciar sesión y su sesión actual se cerrará. Sus cobros y cajas se conservan."
            if cashier["is_active"] else ""
        )
        if QMessageBox.question(self, "Confirmar", f"¿{action.capitalize()} a {cashier['full_name']}?{detail}") != QMessageBox.Yes:
            return
        try:
            api.patch(f"/users/cashiers/{cashier['id']}", json={"is_active": not cashier["is_active"]})
        except ApiError as exc:
            QMessageBox.critical(self, f"No se pudo {action}", str(exc))
            return
        self.reload_cashiers()

    def reset_password(self, cashier):
        field = Field("new_password", "Contraseña temporal", regex=r"^\S*$", max_length=128,
                      placeholder="Mínimo 6, con letras y números", required=True)
        dialog = RecordDialog(
            f"Restablecer contraseña de {cashier['full_name']}", [field], self,
            submit=lambda values: api.post(f"/users/cashiers/{cashier['id']}/reset-password", json=values),
        )
        dialog.inputs["new_password"].setEchoMode(QLineEdit.Password)
        if dialog.exec() == QDialog.Accepted:
            QMessageBox.information(
                self, "Contraseña restablecida",
                "Comunica la contraseña temporal al cajero: el sistema le pedirá cambiarla al entrar.",
            )
            self.reload_cashiers()

    # -------------------------------------------------- cajas y cierres

    def reload(self):
        self.reload_cashiers()
        try:
            rows = api.get("/cashier/registers") or []
        except ApiError as exc:
            self.status.setText(str(exc))
            return
        self._registers = rows
        self.table.setRowCount(len(rows))
        self.status.setText("Sin cajas registradas todavía." if not rows else "")
        for row_index, row in enumerate(rows):
            closed = not row["is_open"]
            values = [
                f"#{row['id']}", row["cashier_name"], row["opened_at"] or "",
                row["closed_at"] if closed else "ABIERTA",
                money(row["initial_amount"]),
                money(row["expected_amount"]) if closed else "—",
                money(row["physical_amount"]) if closed else "—",
                money(row["difference"]) if closed else "—",
                row.get("audit_explanation") or ("Caja cuadrada" if closed and float(row["difference"]) == 0 else ""),
            ]
            for column, value in enumerate(values):
                self.table.setItem(row_index, column, QTableWidgetItem(value))
            button = QPushButton("Ver reporte")
            button.setStyleSheet("padding: 3px 10px;")
            button.clicked.connect(lambda _c=False, register_id=row["id"]: self.show_register(register_id))
            self.table.setCellWidget(row_index, 9, button)

    def show_register(self, register_id: int):
        try:
            cash_reports.open_register_report(self, register_id)
        except ApiError as exc:
            QMessageBox.critical(self, "No se pudo cargar la caja", str(exc))

    def show_daily(self):
        try:
            cash_reports.open_daily_report(
                self, self.day.date().toString("yyyy-MM-dd"),
                self.cashier_filter.currentData(), self.cashier_filter.currentText(),
            )
        except ApiError as exc:
            QMessageBox.critical(self, "No se pudo cargar el cierre del día", str(exc))

    def show_monthly(self):
        try:
            cash_reports.open_monthly_report(
                self, self.year.value(), self.month.currentData(),
                self.cashier_filter.currentData(), self.cashier_filter.currentText(),
            )
        except ApiError as exc:
            QMessageBox.critical(self, "No se pudo cargar el cierre mensual", str(exc))
