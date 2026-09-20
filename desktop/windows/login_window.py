from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QFormLayout, QGraphicsOpacityEffect, QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QWidget

from api_client import ApiError, api


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

        button = QPushButton("Iniciar sesión")
        button.setObjectName("LoginButton")
        button.setProperty("class", "primary")
        button.clicked.connect(self.handle_login)
        card_layout.addSpacing(8)
        card_layout.addWidget(button)

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
        self.showFullScreen()
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
        try:
            api.login(email, password)
        except ApiError as exc:
            self._submitting = False
            QMessageBox.critical(self, "No se pudo iniciar sesión", str(exc))
            return
        self._submitting = False
        self.on_login_success()