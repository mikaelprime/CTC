"""Transiciones suaves entre ventanas y páginas.

Antes cada ventana (carga, login, panel) aparecía y desaparecía de golpe.
Aquí se animan con fundidos cortos:

- windowOpacity para ventanas completas (en Windows funciona también en
  pantalla completa);
- QGraphicsOpacityEffect para el contenido de una ventana o una página. El
  efecto se quita al terminar: dejarlo puesto obliga a Qt a componer el
  widget en un buffer aparte en cada repintado.

Las animaciones se guardan como hijas del widget animado (y se borran solas
al terminar), así no las recoge el recolector de basura a mitad de camino.
Con la variable de entorno CTC_ANIMATIONS=off se desactivan (equipos lentos
o escritorio remoto): todo aparece al instante, igual que antes.
"""

import os
from typing import Callable, Optional

from PySide6.QtCore import QAbstractAnimation, QEasingCurve, QPropertyAnimation
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget

WINDOW_IN_MS = 420
WINDOW_OUT_MS = 260
CONTENT_IN_MS = 650
PAGE_IN_MS = 220


def enabled() -> bool:
    return os.environ.get("CTC_ANIMATIONS", "on").lower() not in {"off", "0", "no"}


def _animate(
    target,
    prop: bytes,
    start: float,
    end: float,
    duration: int,
    easing: QEasingCurve.Type,
    on_done: Optional[Callable[[], None]] = None,
) -> QPropertyAnimation:
    parent = target if isinstance(target, QWidget) else target.parent()
    animation = QPropertyAnimation(target, prop, parent)
    animation.setDuration(duration)
    animation.setStartValue(start)
    animation.setEndValue(end)
    animation.setEasingCurve(easing)
    if on_done is not None:
        animation.finished.connect(on_done)
    animation.start(QAbstractAnimation.DeleteWhenStopped)
    return animation


def fade_in_window(window: QWidget, show: Callable[[], None], duration: int = WINDOW_IN_MS) -> None:
    """Muestra la ventana (con la función `show` que ya usaba, p. ej.
    showFullScreen) partiendo de transparente y la hace aparecer."""
    if not enabled():
        show()
        return
    window.setWindowOpacity(0.0)
    show()
    _animate(window, b"windowOpacity", 0.0, 1.0, duration, QEasingCurve.OutCubic)


def fade_out_window(window: QWidget, on_done: Callable[[], None], duration: int = WINDOW_OUT_MS) -> None:
    """Desvanece la ventana y luego llama a `on_done` (que la cierra, abre
    la siguiente, etc.)."""
    if not enabled() or not window.isVisible():
        on_done()
        return
    _animate(window, b"windowOpacity", window.windowOpacity(), 0.0, duration, QEasingCurve.InCubic, on_done)


def crossfade_windows(old: QWidget, new: QWidget, show_new: Callable[[], None], on_done: Callable[[], None]) -> None:
    """La ventana nueva aparece mientras la anterior se desvanece encima."""
    if not enabled():
        show_new()
        on_done()
        return
    fade_in_window(new, show_new, WINDOW_IN_MS)
    new.raise_()
    fade_out_window(old, on_done, WINDOW_IN_MS)


def fade_in_widget(widget: QWidget, duration: int = CONTENT_IN_MS) -> None:
    """Hace aparecer el contenido de un widget. Si ya tiene otro efecto
    gráfico (p. ej. una sombra) no se toca, para no quitárselo."""
    if not enabled():
        return
    current = widget.graphicsEffect()
    if current is not None and not isinstance(current, QGraphicsOpacityEffect):
        return
    effect = QGraphicsOpacityEffect(widget)
    effect.setOpacity(0.0)
    widget.setGraphicsEffect(effect)

    def cleanup():
        if widget.graphicsEffect() is effect:
            widget.setGraphicsEffect(None)

    _animate(effect, b"opacity", 0.0, 1.0, duration, QEasingCurve.OutCubic, cleanup)
