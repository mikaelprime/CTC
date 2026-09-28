from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QFormLayout, QGraphicsOpacityEffect, QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QWidget

from api_client import api
from widgets import transitions
from widgets.animated_button import AnimatedButton
from widgets.async_worker import AsyncWorker


class LoginWindow(QWidget):
    def __init__(self, on_success):
        super().__init__()
        self.on_login_success = on_success
        self._submitting = False
        self.setWindowTitle("CTC Campus · Iniciar sesión")
        self.setObjectName("LoginShell")
        self.setMinimumSize(900, 600)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setAlignment(Qt.AlignCenter)

        card = QWidget()
        card.setObjectName("LoginCard")
        card.setMaximumWidth(480)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(42, 38, 42, 42)
        card_layout.setSpacing(14)

        eyebrow = QLabel("CENTRO TÉCNICO DE CAPACITACIÓN")
        eyebrow.setObjectName("LoginEyebrow")
        title = QLabel("CTC Campus")
        title.setObjectName("LoginTitle")
        subtitle = QLabel("Gestiona matrículas, colegiaturas y cajas desde un solo lugar.")
        subtitle.setObjectName("LoginSubtitle")
        subtitle.setWordWrap(True)
        card_layout.addWidget(eyebrow)
        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(12)

        form = QFormLayout()
        form.setVerticalSpacing(12)
        self.email_input = QLineEdit()
        self.email_input.setObjectName("LoginInput")
        self.email_input.setPlaceholderText("correo@ctc.edu.sv")
        self.password_input = QLineEdit()
        self.password_input.setObjectName("LoginInput")
        self.password_input.setPlaceholderText("Tu contraseña")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.returnPressed.connect(self.handle_login)
        form.addRow("Correo", self.email_input)
        form.addRow("Contraseña", self.password_input)
        card_layout.addLayout(form)

        self.login_button = AnimatedButton("Iniciar sesión")
        self.login_button.setObjectName("LoginButton")
        self.login_button.setProperty("class", "primary")
        self.login_button.clicked.connect(self.handle_login)
        card_layout.addSpacing(8)
        card_layout.addWidget(self.login_button)

        exit_button = QPushButton("Salir del programa")
        exit_button.setObjectName("LoginExitButton")
        exit_button.clicked.connect(QApplication.instance().quit)
        card_layout.addWidget(exit_button)

        footer = QLabel("Acceso seguro para administradores y cajeros")
        footer.setObjectName("LoginFooter")
        footer.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(footer)
        layout.addWidget(card)

        self.opacity_effect = QGraphicsOpacityEffect(card)
        card.setGraphicsEffect(self.opacity_effect)
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity", self)
        self.fade_animation.setDuration(650)
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.setEasingCurve(QEasingCurve.OutCubic)

    def show_on_current_screen(self):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        self.setGeometry(screen)
        transitions.fade_in_window(self, self.showFullScreen)
        self.fade_animation.start()

    def handle_login(self):
        if self._submitting:
            return
        email = self.email_input.text().strip()
        password = self.password_input.text()
        if not email or not password or "@" not in email:
            QMessageBox.warning(self, "Validación", "Ingresa un correo válido y tu contraseña.")
            return
        self._submitting = True
        self.login_button.setEnabled(False)
        self.login_button.setText("Conectando…")
        QApplication.setOverrideCursor(Qt.WaitCursor)

        # La autenticación corre en un hilo aparte: si se hiciera en el hilo
        # de la interfaz, Windows puede llegar a marcar la ventana como "(No
        # responde)" mientras se espera al backend (hasta 60s si Render
        # estaba dormido), aunque técnicamente siga funcionando.
        def do_login():
            api.login(email, password)

        worker = AsyncWorker(do_login, self)
        self._login_worker = worker
        worker.succeeded.connect(lambda _result: self._on_login_finished(success=True))
        worker.failed.connect(lambda message: self._on_login_finished(success=False, message=message))
        worker.start()

    def _on_login_finished(self, success: bool, message: str = "") -> None:
        self._submitting = False
        self.login_button.setEnabled(True)
        self.login_button.setText("Iniciar sesión")
        QApplication.restoreOverrideCursor()
        if not success:
            QMessageBox.critical(self, "No se pudo iniciar sesión", message)
            return
        self.on_login_success()