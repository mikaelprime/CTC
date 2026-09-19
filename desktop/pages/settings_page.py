from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from api_client import api


class SettingsPage(QWidget):
    """No backend endpoints exist yet for institutional settings — read-only info page."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        header = QLabel("Configuración")
        header.setObjectName("PageTitle")
        sub = QLabel("Parámetros generales y sesión activa")
        sub.setObjectName("PageSubtitle")
        layout.addWidget(header)
        layout.addWidget(sub)

        user_label = QLabel(f"Sesión iniciada como: {api.user_email or '—'}")
        layout.addWidget(user_label)

        notice = QLabel(
            "⚠ El backend aún no expone endpoints de configuración institucional, "
            "usuarios/roles o notificaciones. Esta sección se conectará cuando esa API exista."
        )
        notice.setWordWrap(True)
        notice.setStyleSheet("color: #f59e0b;")
        layout.addWidget(notice)
        layout.addStretch()
