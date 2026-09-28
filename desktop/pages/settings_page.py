from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from api_client import ApiError, api
from widgets.animated_button import AnimatedButton

# (campo de la API, etiqueta) del tarifario institucional (PDF punto 3).
TARIFFS = [
    ("registration_full_fee", "Matrícula"),
    ("registration_promo_fee", "Promo-Matrícula 50% OFF"),
    ("tuition_group_fee", "Colegiatura Plan Grupal"),
    ("tuition_private_fee", "Colegiatura Plan Privado"),
    ("tuition_online_fee", "Colegiatura Plan On-line"),
]


def _money_input() -> QDoubleSpinBox:
    spin = QDoubleSpinBox()
    spin.setRange(0, 10000)
    spin.setDecimals(2)
    spin.setPrefix("$ ")
    return spin


class SettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        header = QLabel("Configuración")
        header.setObjectName("PageTitle")
        sub = QLabel("Políticas de cobro, tarifario y datos de la sesión activa · cada cambio queda en la bitácora")
        sub.setObjectName("PageSubtitle")
        layout.addWidget(header)
        layout.addWidget(sub)

        self.session_label = QLabel()
        layout.addWidget(self.session_label)

        columns = QHBoxLayout()
        policies = QGroupBox("Políticas de cobro")
        form = QFormLayout(policies)
        self.institution = QLineEdit()
        self.institution.setMaxLength(150)
        self.late_fee = _money_input()
        self.cycle_days = QSpinBox()
        self.cycle_days.setRange(1, 365)
        self.cycle_days.setSuffix(" días")
        self.alert_days = QSpinBox()
        self.alert_days.setRange(0, 60)
        self.alert_days.setSuffix(" días antes")
        form.addRow("Institución", self.institution)
        form.addRow("Recargo por mora", self.late_fee)
        form.addRow("Ciclo de pago", self.cycle_days)
        form.addRow("Aviso de vencimiento", self.alert_days)
        columns.addWidget(policies)

        tariffs = QGroupBox("Tarifario")
        tariff_form = QFormLayout(tariffs)
        self.tariffs = {}
        for key, label in TARIFFS:
            self.tariffs[key] = _money_input()
            tariff_form.addRow(label, self.tariffs[key])
        note = QLabel("Matrícula gratis: siempre $0.00.\nLos cobros ya registrados conservan su monto.")
        note.setObjectName("PaymentHint")
        tariff_form.addRow(note)
        columns.addWidget(tariffs)
        layout.addLayout(columns)

        save = AnimatedButton("Guardar configuración")
        save.setProperty("class", "primary")
        save.clicked.connect(self.save)
        layout.addWidget(save)
        layout.addStretch()
        self.reload()

    def reload(self):
        self.session_label.setText(
            f"Sesión: {api.full_name or '—'} ({api.user_email or '—'}) · Rol: {api.user_role or '—'}"
        )
        try:
            config = api.get("/config/")
        except ApiError as exc:
            QMessageBox.critical(self, "Error", str(exc))
            return
        self.institution.setText(config["institution_name"])
        self.late_fee.setValue(float(config["late_fee"]))
        self.cycle_days.setValue(int(config["payment_cycle_days"]))
        self.alert_days.setValue(int(config["alert_days_before"]))
        for key, spin in self.tariffs.items():
            spin.setValue(float(config[key]))

    def save(self):
        body = {
            "institution_name": self.institution.text().strip(),
            "late_fee": self.late_fee.value(),
            "payment_cycle_days": self.cycle_days.value(),
            "alert_days_before": self.alert_days.value(),
            **{key: spin.value() for key, spin in self.tariffs.items()},
        }
        try:
            api.put("/config/", json=body)
        except ApiError as exc:
            QMessageBox.critical(self, "No se pudo guardar", str(exc))
            return
        QMessageBox.information(self, "Configuración guardada", "Las políticas y el tarifario fueron actualizados.")
