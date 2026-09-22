from PySide6.QtWidgets import QDoubleSpinBox, QFormLayout, QLabel, QLineEdit, QMessageBox, QSpinBox, QVBoxLayout, QWidget

from api_client import ApiError, api
from widgets.animated_button import AnimatedButton


class SettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        header = QLabel("Configuración")
        header.setObjectName("PageTitle")
        sub = QLabel("Políticas de cobro y datos de la sesión activa")
        sub.setObjectName("PageSubtitle")
        layout.addWidget(header)
        layout.addWidget(sub)

        self.session_label = QLabel()
        layout.addWidget(self.session_label)
        form = QFormLayout()
        self.institution = QLineEdit()
        self.late_fee = QDoubleSpinBox()
        self.late_fee.setRange(0, 100000)
        self.late_fee.setDecimals(2)
        self.cycle_days = QSpinBox()
        self.cycle_days.setRange(1, 365)
        self.alert_days = QSpinBox()
        self.alert_days.setRange(0, 60)
        form.addRow("Institución", self.institution)
        form.addRow("Recargo por mora", self.late_fee)
        form.addRow("Ciclo de pago (días)", self.cycle_days)
        form.addRow("Avisar antes (días)", self.alert_days)
        layout.addLayout(form)
        save = AnimatedButton("Guardar configuración")
        save.setProperty("class", "primary")
        save.clicked.connect(self.save)
        layout.addWidget(save)
        layout.addStretch()
        self.reload()

    def reload(self):
        self.session_label.setText(f"Sesión: {api.user_email or '—'} · Rol: {api.user_role or '—'}")
        try:
            config = api.get("/config/")
        except ApiError as exc:
            QMessageBox.critical(self, "Error", str(exc))
            return
        self.institution.setText(config["institution_name"])
        self.late_fee.setValue(float(config["late_fee"]))
        self.cycle_days.setValue(int(config["payment_cycle_days"]))
        self.alert_days.setValue(int(config["alert_days_before"]))

    def save(self):
        try:
            api.put("/config/", json={"institution_name": self.institution.text().strip(), "late_fee": self.late_fee.value(), "payment_cycle_days": self.cycle_days.value(), "alert_days_before": self.alert_days.value()})
        except ApiError as exc:
            QMessageBox.critical(self, "No se pudo guardar", str(exc))
            return
        QMessageBox.information(self, "Configuración guardada", "Las políticas fueron actualizadas.")
