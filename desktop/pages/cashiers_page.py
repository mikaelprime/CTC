from datetime import date

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QLabel,
    QLineEdit,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from api_client import ApiError, api
from widgets.animated_button import AnimatedButton
from widgets.crud_page import Field, RecordDialog


class CashiersPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        header = QLabel("Cajeros y cajas")
        header.setObjectName("PageTitle")
        sub = QLabel("Usuarios cajero, aperturas, cierres y auditorías")
        sub.setObjectName("PageSubtitle")
        layout.addWidget(header)
        layout.addWidget(sub)

        add_button = AnimatedButton("➕ Crear cajero")
        add_button.setProperty("class", "primary")
        add_button.clicked.connect(self.create_cashier)
        layout.addWidget(add_button)

        # Cuentas de cajero: desactivar a quien deja de trabajar (no se
        # borra, sus cobros siguen en los reportes) y restablecer contraseñas.
        self.cashiers_table = QTableWidget()
        self.cashiers_table.setColumnCount(4)
        self.cashiers_table.setHorizontalHeaderLabels(["Cajero", "Correo", "Estado", "Acciones"])
        self.cashiers_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.cashiers_table.verticalHeader().setVisible(False)
        self.cashiers_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.cashiers_table.setMaximumHeight(200)
        layout.addWidget(self.cashiers_table)

        summary_grid = QGridLayout()
        self.summary_labels = {}
        for index, (key, title) in enumerate((
            ("cajas_cerradas", "Cajas cerradas"),
            ("total_cobrado_mes", "Cobrado en pagos"),
            ("total_efectivo_contado", "Efectivo contado"),
            ("total_descuadres_mes", "Descuadres"),
        )):
            label = QLabel("—")
            label.setObjectName("SummaryValue")
            caption = QLabel(title)
            caption.setObjectName("SummaryCaption")
            summary_grid.addWidget(caption, 0, index)
            summary_grid.addWidget(label, 1, index)
            self.summary_labels[key] = label
        layout.addLayout(summary_grid)

        report_row = QGridLayout()
        self.month = QComboBox()
        for number in range(1, 13):
            self.month.addItem(f"{number:02d}", number)
        # Antes quedaba fijo en septiembre de 2026.
        self.month.setCurrentIndex(date.today().month - 1)
        self.year = QLineEdit(str(date.today().year))
        self.year.setInputMask("9999")
        self.cashier_filter = QComboBox()
        self.cashier_filter.addItem("Todos los cajeros", None)
        try:
            for cashier in api.get("/users/cashiers") or []:
                self.cashier_filter.addItem(cashier["full_name"], cashier["id"])
        except ApiError:
            pass
        report_button = AnimatedButton("Actualizar cierre mensual")
        report_button.clicked.connect(self.load_monthly_report)
        report_row.addWidget(QLabel("Mes"), 0, 0)
        report_row.addWidget(self.month, 0, 1)
        report_row.addWidget(QLabel("Año"), 0, 2)
        report_row.addWidget(self.year, 0, 3)
        report_row.addWidget(QLabel("Cajero"), 0, 4)
        report_row.addWidget(self.cashier_filter, 0, 5)
        report_row.addWidget(report_button, 0, 6)
        layout.addLayout(report_row)

        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels(["Cajero", "Correo", "Caja", "Fondo", "Esperado", "Físico", "Diferencia", "Estado", "Auditoría"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)
        self.status = QLabel("")
        self.status.setObjectName("PageSubtitle")
        layout.addWidget(self.status)
        self.reload()
        self.load_monthly_report()

    def create_cashier(self):
        fields = [
            Field("full_name", "Nombre completo", regex=r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ' \-]*$",
                  max_length=150, placeholder="Nombre y apellido", required=True),
            Field("email", "Correo", regex=r"^\S*$", max_length=120, required=True),
            Field("password", "Contraseña", regex=r"^\S*$", max_length=128,
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
        QMessageBox.information(self, "Cajero creado", "El cajero ya puede iniciar sesión con su correo.")
        self.reload()

    def reload_cashiers(self):
        try:
            cashiers = api.get("/users/cashiers") or []
        except ApiError as exc:
            self.status.setText(str(exc))
            return
        self.cashiers_table.setRowCount(len(cashiers))
        self.cashiers_table.verticalHeader().setDefaultSectionSize(40)
        for index, cashier in enumerate(cashiers):
            active = cashier["is_active"]
            values = [cashier["full_name"], cashier["email"], "Activo" if active else "Desactivado"]
            for column, value in enumerate(values):
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
        field = Field("new_password", "Nueva contraseña", regex=r"^\S*$", max_length=128,
                      placeholder="Mínimo 6, con letras y números", required=True)
        dialog = RecordDialog(
            f"Restablecer contraseña de {cashier['full_name']}", [field], self,
            submit=lambda values: api.post(f"/users/cashiers/{cashier['id']}/reset-password", json=values),
        )
        dialog.inputs["new_password"].setEchoMode(QLineEdit.Password)
        if dialog.exec() == QDialog.Accepted:
            QMessageBox.information(self, "Contraseña restablecida", "Comunica la nueva contraseña al cajero.")

    def reload(self):
        self.reload_cashiers()
        try:
            rows = api.get("/cashier/registers") or []
        except ApiError as exc:
            self.status.setText(str(exc))
            return
        self.table.setRowCount(len(rows))
        self.status.setText("Sin cajas registradas todavía." if not rows else "")
        for row_index, row in enumerate(rows):
            values = [row["cashier_name"], row["cashier_email"], f"#{row['id']}", f"${float(row['initial_amount']):,.2f}", f"${float(row['expected_amount']):,.2f}", f"${float(row['physical_amount']):,.2f}", f"${float(row['difference']):,.2f}", "Abierta" if row["is_open"] else "Cerrada", row.get("audit_explanation") or "Sin observaciones"]
            for column, value in enumerate(values):
                self.table.setItem(row_index, column, QTableWidgetItem(value))

    def load_monthly_report(self):
        try:
            cashier_id = self.cashier_filter.currentData()
            suffix = f"&cashier_id={cashier_id}" if cashier_id else ""
            report = api.get(f"/cashier/monthly?year={int(self.year.text())}&month={self.month.currentData()}{suffix}")
        except (ApiError, ValueError) as exc:
            self.status.setText(f"No se pudo cargar el cierre mensual: {exc}")
            return
        self.summary_labels["cajas_cerradas"].setText(str(report["cajas_cerradas"]))
        self.summary_labels["total_cobrado_mes"].setText(f"${float(report['total_cobrado_mes']):,.2f}")
        self.summary_labels["total_efectivo_contado"].setText(f"${float(report['total_efectivo_contado']):,.2f}")
        self.summary_labels["total_descuadres_mes"].setText(f"${float(report['total_descuadres_mes']):,.2f}")
