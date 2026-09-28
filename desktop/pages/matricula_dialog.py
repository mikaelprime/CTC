"""Formulario único de matrícula (PDF punto 1 y página 2, "Datos de
matrícula"): estudiante (nuevo o ya registrado) y su responsable, servicio
(diplomado), horario, fecha de matrícula, fecha de inicio de clases,
observaciones, tipo de matrícula, plan de colegiatura y el cobro con
"Efectivo:" y "Cambio:". Todo se guarda en una sola operación: si algo falla
no queda un estudiante registrado sin su matrícula.
"""

from typing import Any, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QRadioButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from api_client import ApiError, api
from pages.students_page import link_age, student_body, student_fields
from widgets.crud_page import Field, build_field_widget, missing_required, read_field_value
from widgets.receipt_view import money

PAYMENT_TYPES = ["Efectivo", "Tarjeta", "Transferencia"]
REGISTRATION_TYPES = [
    ("COMPLETA", "Matrícula", "registration_full_fee"),
    ("PROMO", "Promo-Matrícula 50% OFF", "registration_promo_fee"),
    ("GRATIS", "Matrícula gratis", None),
]
TUITION_PLANS = [
    ("GRUPAL", "Plan Grupal", "tuition_group_fee"),
    ("PRIVADO", "Plan Privado", "tuition_private_fee"),
    ("ONLINE", "Plan On-line", "tuition_online_fee"),
]


def registration_fee(config: dict, registration_type: str) -> float:
    key = next(column for code, _label, column in REGISTRATION_TYPES if code == registration_type)
    return float(config[key]) if key else 0.0


class MatriculaDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nueva matrícula")
        self.setMinimumSize(760, 640)
        self.result_data: Optional[dict] = None
        # Catálogos y tarifario actuales (el backend es quien cobra; esto es
        # solo para mostrar precios, total y cambio mientras se llena).
        self.config = api.get("/config/")
        self.students = api.get("/students/") or []
        self.diplomas = [d for d in api.get("/diplomas/") or [] if d.get("active")]
        self.schedules = [s for s in api.get("/schedules/") or [] if s.get("active")]

        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        # Solo desplazamiento vertical: los campos se ajustan al ancho.
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        body = QWidget()
        layout = QVBoxLayout(body)
        scroll.setWidget(body)
        outer.addWidget(scroll, stretch=1)

        layout.addWidget(self._student_box())
        layout.addWidget(self._enrollment_box())
        layout.addWidget(self._payment_box())
        layout.addStretch()

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.button(QDialogButtonBox.Ok).setText("Registrar matrícula")
        self.buttons.accepted.connect(self._submit)
        self.buttons.rejected.connect(self.reject)
        outer.addWidget(self.buttons)
        self._recalculate()

    # ------------------------------------------------------------ secciones

    def _student_box(self) -> QGroupBox:
        box = QGroupBox("1. Estudiante")
        layout = QVBoxLayout(box)
        choice = QHBoxLayout()
        self.new_student = QRadioButton("Estudiante nuevo")
        self.existing_student = QRadioButton("Estudiante ya registrado")
        group = QButtonGroup(box)
        group.addButton(self.new_student)
        group.addButton(self.existing_student)
        self.new_student.setChecked(True)
        choice.addWidget(self.new_student)
        choice.addWidget(self.existing_student)
        choice.addStretch()
        layout.addLayout(choice)

        self.student_stack = QStackedWidget()
        new_page = QWidget()
        new_form = QFormLayout(new_page)
        self.student_spec = student_fields()
        self.student_inputs: dict[str, QWidget] = {}
        for f in self.student_spec:
            widget = build_field_widget(f)
            self.student_inputs[f.name] = widget
            new_form.addRow(f"{f.label} *" if f.required else f.label, widget)
        link_age(self.student_inputs)
        self.student_stack.addWidget(new_page)

        existing_page = QWidget()
        existing_form = QFormLayout(existing_page)
        self.student_combo = QComboBox()
        self.student_combo.setEditable(True)
        self.student_combo.setInsertPolicy(QComboBox.NoInsert)
        for s in sorted(self.students, key=lambda s: s["full_name"]):
            self.student_combo.addItem(f"{s['full_name']} — {s.get('email') or ''}", s["id"])
        completer = self.student_combo.completer()
        completer.setFilterMode(Qt.MatchContains)
        completer.setCompletionMode(QCompleter.PopupCompletion)
        existing_form.addRow("Buscar estudiante", self.student_combo)
        self.student_stack.addWidget(existing_page)
        layout.addWidget(self.student_stack)

        self.new_student.toggled.connect(lambda checked: self.student_stack.setCurrentIndex(0 if checked else 1))
        self.existing_student.setEnabled(bool(self.students))
        return box

    def _enrollment_box(self) -> QGroupBox:
        box = QGroupBox("2. Datos de matrícula")
        form = QFormLayout(box)
        self.enrollment_spec = [
            Field("diploma_id", "Servicio (diplomado)", kind="combo",
                  options=lambda: [(d["name"], d["id"]) for d in self.diplomas]),
            Field("schedule_id", "Horario", kind="combo",
                  options=lambda: [(s["name"], s["id"]) for s in self.schedules]),
            # No se matricula en el futuro; hasta un año atrás para pasar al
            # sistema matrículas hechas en papel.
            Field("enrollment_date", "Fecha de matrícula", kind="date", min_days=-365, max_days=0),
            # La fecha que ancla los cobros: el primero ese mismo día y los
            # siguientes cada 28 días (PDF, "Funcionamiento básico").
            Field("start_date", "Fecha de inicio de clases", kind="date", min_days=-365 - 90, max_days=365),
            Field("registration_type", "Tipo de matrícula", kind="combo", options=lambda: [
                (f"{label} ({money(registration_fee(self.config, code))})", code)
                for code, label, _column in REGISTRATION_TYPES
            ]),
            Field("tuition_plan", "Plan de colegiatura", kind="combo", options=lambda: [
                (f"{label} ({money(self.config[column])} cada 28 días)", code)
                for code, label, column in TUITION_PLANS
            ]),
            Field("observations", "Observaciones", max_length=500),
        ]
        self.enrollment_inputs: dict[str, QWidget] = {}
        for f in self.enrollment_spec:
            widget = build_field_widget(f)
            self.enrollment_inputs[f.name] = widget
            form.addRow(f.label, widget)
        self.first_payment_hint = QLabel()
        self.first_payment_hint.setObjectName("PaymentHint")
        form.addRow(self.first_payment_hint)
        start = self.enrollment_inputs["start_date"]
        start.dateChanged.connect(self._update_first_payment_hint)
        self._update_first_payment_hint()
        return box

    def _payment_box(self) -> QGroupBox:
        box = QGroupBox("3. Cobro de la matrícula")
        form = QFormLayout(box)
        self.payment_type = QComboBox()
        self.payment_type.addItems(PAYMENT_TYPES)
        self.cash = QDoubleSpinBox()
        self.cash.setRange(0, 100000)
        self.cash.setDecimals(2)
        self.cash.setPrefix("$ ")
        self.total_label = QLabel()
        self.total_label.setObjectName("SummaryValue")
        self.change_label = QLabel()
        self.change_label.setObjectName("SummaryValue")
        form.addRow("Método de pago", self.payment_type)
        form.addRow("Total matrícula:", self.total_label)
        form.addRow("Efectivo:", self.cash)
        form.addRow("Cambio:", self.change_label)
        self.enrollment_inputs["registration_type"].currentIndexChanged.connect(self._recalculate)
        self.payment_type.currentIndexChanged.connect(self._recalculate)
        self.cash.valueChanged.connect(self._recalculate)
        return box

    # ------------------------------------------------------------ cálculo

    def _update_first_payment_hint(self) -> None:
        start = self.enrollment_inputs["start_date"].date()
        second = start.addDays(int(self.config["payment_cycle_days"]))
        self.first_payment_hint.setText(
            f"Primera colegiatura: {start.toString('dd/MM/yyyy')} · "
            f"siguiente: {second.toString('dd/MM/yyyy')} (cada {self.config['payment_cycle_days']} días)"
        )

    def _fee(self) -> float:
        return registration_fee(self.config, self.enrollment_inputs["registration_type"].currentData())

    def _recalculate(self) -> None:
        fee = self._fee()
        is_cash = self.payment_type.currentText() == "Efectivo"
        free = fee <= 0
        self.payment_type.setEnabled(not free)
        self.cash.setEnabled(is_cash and not free)
        if free or not is_cash:
            self.cash.setValue(fee)
        self.total_label.setText(money(fee))
        change = self.cash.value() - fee
        self.change_label.setText(money(change) if change >= 0 else f"Faltan {money(-change)}")
        self.buttons.button(QDialogButtonBox.Ok).setEnabled(change >= -0.001)

    # ------------------------------------------------------------ envío

    def payload(self) -> dict[str, Any]:
        data = {f.name: read_field_value(f, self.enrollment_inputs[f.name]) for f in self.enrollment_spec}
        data["observations"] = data["observations"] or None
        data["payment_type"] = self.payment_type.currentText()
        data["cash_received"] = self.cash.value()
        if self.new_student.isChecked():
            values = {f.name: read_field_value(f, self.student_inputs[f.name]) for f in self.student_spec}
            data["student"] = student_body(values)
        else:
            data["student_id"] = self.student_combo.currentData()
        return data

    def _submit(self) -> None:
        if self.new_student.isChecked():
            missing = missing_required(self.student_spec, self.student_inputs)
            if missing:
                QMessageBox.warning(self, "Faltan datos del estudiante", "Completa: " + ", ".join(missing))
                return
        elif self.student_combo.currentData() is None:
            QMessageBox.warning(self, "Falta el estudiante", "Selecciona un estudiante registrado.")
            return
        if not self.diplomas or not self.schedules:
            QMessageBox.warning(self, "Catálogo incompleto", "Debe haber al menos un diplomado y un horario activos.")
            return
        try:
            self.result_data = api.post("/enrollments/", json=self.payload())
        except ApiError as exc:
            # Se queda abierto para corregir, sin perder lo ya escrito.
            QMessageBox.critical(self, "Revisa los datos", str(exc))
            return
        self.accept()
