from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from api_client import ApiError, api
from theme import BORDER, SURFACE
from window_utils import show_maximized_on_current_screen


class LoginWindow(QWidget):
    def __init__(self, on_success):
        super().__init__()
        self.on_success = on_success
        self.setWindowTitle("CTC Campus · Iniciar sesión")

        outer = QVBoxLayout(self)
        outer.addStretch()
        centered_row = QHBoxLayout()
        centered_row.addStretch()

        card = QWidget()
        card.setFixedWidth(380)
        card.setStyleSheet(f"background-color: {SURFACE}; border: 1px solid {BORDER}; border-radius: 14px;")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(32, 32, 32, 32)

        title = QLabel("🏫 CTC Campus")
        title.setStyleSheet("font-size: 20px; font-weight: 700; border: none;")
        title.setAlignment(Qt.AlignCenter)
        subtitle = QLabel("Admin Console")
        subtitle.setStyleSheet("color: #6bd8cb; font-size: 11px; letter-spacing: 1px; border: none;")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(16)

        form = QFormLayout()
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("admin@ctc.edu.sv")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        form.addRow("Correo", self.email_input)
        form.addRow("Contraseña", self.password_input)
        layout.addLayout(form)

        self.login_btn = QPushButton("Ingresar")
        self.login_btn.setProperty("class", "primary")
        self.login_btn.clicked.connect(self.handle_login)
        layout.addWidget(self.login_btn)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #ef4444; border: none;")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

        centered_row.addWidget(card)
        centered_row.addStretch()
        outer.addLayout(centered_row)
        outer.addStretch()

        self.password_input.returnPressed.connect(self.handle_login)
        self.email_input.setFocus()

    def show_on_current_screen(self) -> None:
        show_maximized_on_current_screen(self)

    def handle_login(self) -> None:
        email = self.email_input.text().strip()
        password = self.password_input.text()
        if not email or not password:
            self.error_label.setText("Ingresa correo y contraseña.")
            return

        self.login_btn.setEnabled(False)
        self.login_btn.setText("Ingresando...")
        try:
            api.login(email, password)
        except ApiError as exc:
            self.error_label.setText(str(exc))
        else:
            self.on_success()
        finally:
            self.login_btn.setEnabled(True)
            self.login_btn.setText("Ingresar")
