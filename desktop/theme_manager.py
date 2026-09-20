from PySide6.QtWidgets import QApplication

from theme import stylesheet_for


class ThemeManager:
    """Applies the selected visual theme to the desktop application."""

    DARK = "dark"
    LIGHT = "light"

    def __init__(self, application: QApplication):
        self.application = application
        self.mode = self.DARK
        self.apply(self.mode)

    def apply(self, mode: str) -> None:
        self.mode = self.LIGHT if mode == self.LIGHT else self.DARK
        self.application.setStyleSheet(stylesheet_for(self.mode))

    def toggle(self) -> str:
        self.apply(self.LIGHT if self.mode == self.DARK else self.DARK)
        return self.mode
