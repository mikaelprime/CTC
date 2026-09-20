from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QGridLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from api_client import ApiError, api
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

        add_button = QPushButton("➕ Crear cajero")
        add_button.setProperty("class", "primary")
        add_button.clicked.connect(self.create_cashier)
        layout.addWidget(add_button)

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
        self.month.setCurrentIndex(8)
        self.year = QLineEdit("2026")
        self.cashier_filter = QComboBox()
        self.cashier_filter.addItem("Todos los cajeros", None)
        try:
            for cashier in api.get("/users/cashiers") or []:
                self.cashier_filter.addItem(cashier["full_name"], cashier["id"])
        except ApiError:
            pass
        report_button = QPushButton("Actualizar cierre mensual")
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
        fields = [Field("full_name", "Nombre completo"), Field("email", "Correo"), Field("password", "Contraseña"), Field("birth_date", "Fecha de nacimiento", kind="date")]
        dialog = RecordDialog("Crear cajero", fields, self)
        dialog.inputs["password"].setEchoMode(QLineEdit.Password)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            api.post("/users/cashiers", json=dialog.values())
        except ApiError as exc:
            QMessageBox.critical(self, "No se pudo crear el cajero", str(exc))
            return
        QMessageBox.information(self, "Cajero creado", "El cajero ya puede iniciar sesión con su correo.")
        self.reload()

    def reload(self):
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
