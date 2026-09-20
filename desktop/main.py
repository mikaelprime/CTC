import sys

from PySide6.QtWidgets import QApplication

from theme_manager import ThemeManager
from windows.login_window import LoginWindow
from windows.main_window import MainWindow


class App:
    def __init__(self):
        self.qapp = QApplication(sys.argv)
        self.theme_manager = ThemeManager(self.qapp)
        self.main_window = None
        self.login_window = None
        self.show_login()

    def show_login(self) -> None:
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
    sys.exit(App().run())
