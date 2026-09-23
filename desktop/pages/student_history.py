"""Historial de pagos de un estudiante: todas sus inscripciones y cada cobro
(incluidos los anulados), con totales y exportación a Excel/PDF."""

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from api_client import api
from widgets.animated_button import AnimatedButton
from widgets.report_export import Report, Section, export_report

_KIND = {"MATRICULA": "Matrícula", "COLEGIATURA": "Colegiatura"}
_PLAN = {"GRUPAL": "Grupal", "PRIVADO": "Privado", "ONLINE": "On-line"}

ENROLLMENT_HEADERS = ["#", "Programa", "Turno", "Plan", "Inicio", "Estado", "Próximo pago"]
PAYMENT_HEADERS = [
    "Pago", "Programa", "Concepto", "Fecha de pago", "Vence", "Monto", "Recargo",
    "Total", "Método", "Estado", "Registró", "Observaciones",
]
PAYMENT_MONEY_COLUMNS = {5, 6, 7}


def enrollment_rows(data: dict) -> list[list]:
    rows = []
    for e in data["enrollments"]:
        next_payment = e.get("next_payment_date") or "—"
        if e.get("is_overdue"):
            next_payment = f"{next_payment} (atrasado)"
        rows.append([
            e["id"], e["diploma_name"], e["schedule_name"], _PLAN.get(e["tuition_plan"], e["tuition_plan"]),
            e["start_date"], e["status"], next_payment,
        ])
    return rows


def payment_rows(data: dict) -> list[list]:
    return [
        [
            p["id"], p["diploma_name"], _KIND.get(p["kind"], p["kind"]), p["payment_date"], p["due_date"],
            p["amount"], p["surcharge"], p["total"], p["payment_type"], p["status"],
            p.get("cashier_name") or "—", p.get("observations") or "",
        ]
        for p in data["payments"]
    ]


def summary(data: dict) -> list[tuple[str, object]]:
    t = data["totals"]
    return [
        ("Total pagado", float(t["paid"])),
        ("Matrículas", float(t["registration"])),
        ("Colegiaturas", float(t["tuition"])),
        ("Recargos por mora", float(t["surcharges"])),
        ("Pagos anulados", float(t["voided"])),
        ("Cuotas de colegiatura pagadas", int(t["tuition_installments_paid"])),
        ("Inscripciones atrasadas", int(t["overdue_enrollments"])),
    ]


def build_report(data: dict) -> Report:
    student = data["student"]
    contact = " · ".join(filter(None, [student.get("email"), student.get("contact_phone")]))
    return Report(
        title=f"Historial de pagos — {student['full_name']}",
        subtitle=contact,
        summary=summary(data),
        sections=[
            Section("Inscripciones", ENROLLMENT_HEADERS, enrollment_rows(data)),
            Section("Pagos", PAYMENT_HEADERS, payment_rows(data), money=PAYMENT_MONEY_COLUMNS),
        ],
    )


def _fill(table: QTableWidget, headers: list[str], rows: list[list], money: set[int] = frozenset()) -> None:
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setRowCount(len(rows))
    for r, row in enumerate(rows):
        for c, value in enumerate(row):
            text = f"${float(value):,.2f}" if c in money else ("" if value is None else str(value))
            table.setItem(r, c, QTableWidgetItem(text))
    table.resizeColumnsToContents()
    table.horizontalHeader().setStretchLastSection(True)


class StudentHistoryDialog(QDialog):
    def __init__(self, student_id: int, parent=None):
        super().__init__(parent)
        self.data = api.get(f"/reports/student-history/{student_id}")
        student = self.data["student"]
        self.setWindowTitle(f"Historial de pagos — {student['full_name']}")
        self.setMinimumSize(980, 620)
        layout = QVBoxLayout(self)

        title = QLabel(student["full_name"])
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        contact = QLabel(" · ".join(filter(None, [student.get("email"), student.get("contact_phone")])))
        contact.setObjectName("PageSubtitle")
        layout.addWidget(contact)

        grid = QGridLayout()
        for index, (label, value) in enumerate(summary(self.data)):
            caption = QLabel(label)
            caption.setObjectName("SummaryCaption")
            shown = QLabel(f"${value:,.2f}" if isinstance(value, float) else str(value))
            shown.setObjectName("SummaryValue")
            grid.addWidget(caption, 0, index)
            grid.addWidget(shown, 1, index)
        layout.addLayout(grid)

        layout.addWidget(QLabel("Inscripciones"))
        enrollments = QTableWidget()
        enrollments.setEditTriggers(QTableWidget.NoEditTriggers)
        enrollments.verticalHeader().setVisible(False)
        enrollments.setMaximumHeight(150)
        _fill(enrollments, ENROLLMENT_HEADERS, enrollment_rows(self.data))
        layout.addWidget(enrollments)

        layout.addWidget(QLabel("Pagos"))
        payments = QTableWidget()
        payments.setEditTriggers(QTableWidget.NoEditTriggers)
        payments.verticalHeader().setVisible(False)
        _fill(payments, PAYMENT_HEADERS, payment_rows(self.data), PAYMENT_MONEY_COLUMNS)
        payments.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        layout.addWidget(payments, stretch=1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        export = AnimatedButton("Exportar Excel / PDF")
        export.setProperty("class", "primary")
        export.clicked.connect(self.export)
        buttons.addButton(export, QDialogButtonBox.ActionRole)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def export(self) -> None:
        export_report(self, build_report(self.data), f"Historial {self.data['student']['full_name']}")
