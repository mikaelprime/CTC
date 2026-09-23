"""Pantalla de carga inicial.

Se muestra apenas se abre la app y hace un chequeo de salud del backend en
un hilo aparte (QThread) para no congelar la interfaz. Esto es especialmente
útil porque el backend gratuito de Render puede tardar hasta un minuto en
"despertar" si nadie lo ha usado en un rato: sin esta pantalla, ese primer
tiempo de espera ocurriría recién al intentar iniciar sesión, con la ventana
de login congelada y sin ninguna explicación visible para quien la usa.
"""

import logging

from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget

from api_client import api
from widgets import transitions
from widgets.async_worker import AsyncWorker

logger = logging.getLogger("ctc_campus.splash")


class SplashScreen(QWidget):
    def __init__(self, on_ready):
        super().__init__()
        self.on_ready = on_ready
        self.setObjectName("SplashShell")
        self.setWindowTitle("CTC Campus")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(40, 40, 40, 40)
        center_layout.setSpacing(14)
        center_layout.addStretch()

        title = QLabel("CTC Campus")
        title.setObjectName("SplashTitle")
        title.setAlignment(self._center_flag())
        center_layout.addWidget(title)

        self.status_label = QLabel("Iniciando…")
        self.status_label.setObjectName("SplashStatus")
        self.status_label.setAlignment(self._center_flag())
        center_layout.addWidget(self.status_label)

        center_layout.addSpacing(10)

        bar_row = QWidget()
        bar_row.setFixedWidth(280)
        bar_layout = QVBoxLayout(bar_row)
        bar_layout.setContentsMargins(0, 0, 0, 0)
        self.progress = QProgressBar()
        self.progress.setObjectName("SplashBar")
        self.progress.setRange(0, 0)  # indeterminado: no sabemos cuánto va a tardar
        self.progress.setTextVisible(False)
        bar_layout.addWidget(self.progress)

        row_holder = QVBoxLayout()
        row_holder.setAlignment(self._center_flag())
        row_holder.addWidget(bar_row)
        center_layout.addLayout(row_holder)

        center_layout.addStretch()
        layout.addWidget(center)
        self._center = center

        self._slow_hint_timer = QTimer(self)
        self._slow_hint_timer.setSingleShot(True)
        self._slow_hint_timer.timeout.connect(self._show_slow_hint)

        # AsyncWorker (no un QThread hijo de la ventana): si la pantalla se
        # cierra mientras el servidor sigue despertando, el hilo no aborta
        # el proceso.
        self._worker = AsyncWorker(api.ping, self)
        self._worker.succeeded.connect(self._on_finished)
        self._worker.failed.connect(lambda _message: self._on_finished(False))

    @staticmethod
    def _center_flag():
        from PySide6.QtCore import Qt

        return Qt.AlignCenter

    def show_on_current_screen(self) -> None:
        logger.info("Mostrando pantalla de carga; verificando conexión con el backend…")
        screen = QGuiApplication.primaryScreen().availableGeometry()
        self.setGeometry(screen)
        # La ventana aparece con un fundido y el contenido entra un instante
        # después, en vez de mostrarse todo de golpe.
        transitions.fade_in_window(self, self.showFullScreen)
        transitions.fade_in_widget(self._center, transitions.CONTENT_IN_MS + 250)
        self.status_label.setText("Conectando con el servidor…")
        self._slow_hint_timer.start(4000)
        self._worker.start()

    def _show_slow_hint(self) -> None:
        self.status_label.setText(
            "El servidor estaba inactivo y está despertando. Esto puede tardar hasta un minuto…"
        )

    def _on_finished(self, ok: bool) -> None:
        logger.info("Backend %s", "disponible" if ok else "no respondió a tiempo")
        self._slow_hint_timer.stop()
        if not ok:
            self.status_label.setText(
                "No se pudo contactar al servidor todavía. Continuando de todas formas…"
            )
            QTimer.singleShot(1800, self._finish)
            return
        self.status_label.setText("¡Listo!")
        QTimer.singleShot(300, self._finish)

    def _finish(self) -> None:
        self.on_ready()
