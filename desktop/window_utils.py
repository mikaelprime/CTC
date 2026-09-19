from PySide6.QtGui import QCursor, QGuiApplication
from PySide6.QtWidgets import QWidget


def show_maximized_on_current_screen(widget: QWidget) -> None:
    """Shows a window maximized on whichever screen it's being opened on
    (the one under the cursor), instead of always defaulting to the primary
    monitor with a fixed size.
    """
    screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
    geo = screen.availableGeometry()
    widget.move(geo.topLeft())
    widget.resize(geo.size())
    widget.showMaximized()
