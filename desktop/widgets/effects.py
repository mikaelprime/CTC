"""QSS no soporta box-shadow; esto añade una sombra suave vía Qt Graphics Effects.

Un QGraphicsEffect activo hace que el widget se componga en un buffer aparte
en cada repintado (por ejemplo, en cada frame de scroll), y el costo de ese
blur crece con el radio. Se usan radios moderados a propósito: se nota lo
suficiente sin volverse pesado en páginas con varias tarjetas a la vez.
"""

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget


def apply_card_shadow(widget: QWidget, blur: int = 16, y_offset: int = 6, alpha: int = 70) -> None:
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur)
    shadow.setXOffset(0)
    shadow.setYOffset(y_offset)
    shadow.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(shadow)
