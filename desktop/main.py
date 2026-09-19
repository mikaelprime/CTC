import sys

from PySide6.QtWidgets import QApplication

from theme import STYLESHEET
from windows.login_window import LoginWindow
from windows.main_window import MainWindow


class App:
    def __init__(self):
        self.qapp = QApplication(sys.argv)
        self.qapp.setStyleSheet(STYLESHEET)
        self.main_window = None
        self.login_window = None
        self.show_login()

    def show_login(self) -> None:
        self.main_window = None
        self.login_window = LoginWindow(on_success=self.show_main)
        self.login_window.show_on_current_screen()

    def show_main(self) -> None:
        if self.login_window:
            self.login_window.close()
            self.login_window = None
        self.main_window = MainWindow(on_logout=self.show_login)
        self.main_window.show_on_current_screen()

    def run(self) -> int:
        return self.qapp.exec()


if __name__ == "__main__":
    sys.exit(App().run())
