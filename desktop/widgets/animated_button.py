"""QPushButton con una animación de hover/press sutil.

QSS no soporta transiciones (los ':hover'/':pressed' cambian de golpe), así
que esto anima un resplandor (QGraphicsDropShadowEffect.blurRadius) con
QPropertyAnimation. Solo se usa en botones prominentes (acciones primarias,
navegación) y no en botones repetidos dentro de tablas: un QGraphicsEffect
por fila en una tabla de decenas de filas sí se nota en el rendimiento.

El efecto se crea al primer hover y se destruye en cuanto termina de
desvanecerse, en vez de vivir permanentemente en el botón: un widget con un
QGraphicsEffect activo siempre se compone en un buffer aparte, así que
mantenerlo solo mientras realmente se usa evita ese costo constante en
botones que pasan la mayor parte del tiempo en reposo.
"""

from PySide6.QtCore import QEasingCurve, QPropertyAnimation
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QPushButton

_GLOW_COLOR = QColor(20, 184, 166, 150)


class AnimatedButton(QPushButton):
    def __init__(self, *args, glow_color: QColor = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._glow_color = glow_color or _GLOW_COLOR
        self._shadow = None
        self._anim = None

    def _ensure_effect(self) -> None:
        if self._shadow is not None:
            return
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setOffset(0, 2)
        self._shadow.setColor(self._glow_color)
        self._shadow.setBlurRadius(0)
        self.setGraphicsEffect(self._shadow)

        self._anim = QPropertyAnimation(self._shadow, b"blurRadius", self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.finished.connect(self._drop_effect_if_idle)

    def _drop_effect_if_idle(self) -> None:
        if self._shadow is not None and self._shadow.blurRadius() <= 0:
            self.setGraphicsEffect(None)  # también libera self._shadow
            self._shadow = None
            self._anim = None

    def _animate_glow(self, target: int) -> None:
        self._ensure_effect()
        self._anim.stop()
        self._anim.setStartValue(self._shadow.blurRadius())
        self._anim.setEndValue(target)
        self._anim.start()

    def enterEvent(self, event) -> None:
        if self.isEnabled():
            self._animate_glow(20)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._animate_glow(0)
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        self._animate_glow(6)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self.isEnabled():
            self._animate_glow(20 if self.underMouse() else 0)
        super().mouseReleaseEvent(event)
