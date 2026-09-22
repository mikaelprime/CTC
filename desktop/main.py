import logging
import os
import sys
import traceback
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from theme_manager import ThemeManager
from windows.login_window import LoginWindow
from windows.main_window import MainWindow
from windows.splash_screen import SplashScreen

logger = logging.getLogger("ctc_campus")


def _setup_logging() -> None:
    """Registra los eventos también en un archivo, no solo en consola.

    El .exe distribuido corre sin consola (console=False en el spec de
    PyInstaller), así que si algo falla ahí afuera, un archivo de log es la
    única forma de que la persona que lo usa pueda mandarnos qué pasó.
    """
    handlers = [logging.StreamHandler()]
    try:
        log_dir = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "CTC Campus" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_dir / "app.log", encoding="utf-8"))
    except OSError:
        pass  # sin permisos de escritura ahí: seguimos solo con consola
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
    )


def _install_global_error_handler() -> None:
    """Evita que un error inesperado cierre la app sin ninguna explicación.

    Sin esto, cualquier excepción no capturada en un slot de Qt simplemente
    termina el proceso (o lo deja en un estado roto) sin que quien usa el
    programa entienda qué pasó. Con esto, se registra el error y se muestra
    un aviso comprensible; la persona puede seguir usando el resto de la app.
    """

    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.error("Error no controlado:\n%s", "".join(
            traceback.format_exception(exc_type, exc_value, exc_traceback)
        ))
        try:
            QMessageBox.critical(
                None,
                "Ocurrió un error inesperado",
                "CTC Campus encontró un problema inesperado y pudo seguir funcionando.\n\n"
                f"Detalle técnico: {exc_value}\n\n"
                "Si el problema persiste, cierra y vuelve a abrir el programa.",
            )
        except Exception:
            pass

    sys.excepthook = handle_exception


class App:
    def __init__(self):
        self.qapp = QApplication(sys.argv)
        self.theme_manager = ThemeManager(self.qapp)
        self.main_window = None
        self.login_window = None
        self.splash = SplashScreen(on_ready=self.show_login)
        self.splash.show_on_current_screen()

    def show_login(self) -> None:
        if self.splash:
            self.splash.close()
            self.splash.deleteLater()
            self.splash = None
        if self.main_window:
            self.main_window.close()
            self.main_window.deleteLater()
        self.main_window = None
        if self.login_window:
            self.login_window.close()
            self.login_window.deleteLater()
        self.login_window = LoginWindow(on_success=self.show_main)
        self.login_window.show_on_current_screen()

    def show_main(self) -> None:
        if self.login_window:
            self.login_window.close()
            self.login_window.deleteLater()
            self.login_window = None
        self.main_window = MainWindow(
            on_logout=self.show_login,
            on_exit=self.qapp.quit,
            theme_manager=self.theme_manager,
        )
        self.main_window.show_on_current_screen()

    def run(self) -> int:
        return self.qapp.exec()


if __name__ == "__main__":
    _setup_logging()
    _install_global_error_handler()
    sys.exit(App().run())
