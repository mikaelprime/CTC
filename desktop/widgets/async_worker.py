"""Ejecuta una llamada a la API en un hilo aparte.

Todas las páginas llaman a `requests` de forma síncrona. Si eso corre en el
hilo principal de Qt, la ventana entera se congela mientras espera la
respuesta del backend (especialmente notorio contra el backend en Render,
con latencia de red real). Este worker corre esa llamada en un QThread y
entrega el resultado (o el error) de vuelta al hilo principal por señal,
para que la interfaz siga respondiendo mientras se espera.
"""

from PySide6.QtCore import QThread, Signal


class AsyncWorker(QThread):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self._fn = fn

    def run(self) -> None:
        try:
            result = self._fn()
        except Exception as exc:  # se reporta al hilo principal, no debe crashear el worker
            self.failed.emit(str(exc))
        else:
            self.succeeded.emit(result)
