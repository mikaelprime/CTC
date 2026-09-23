"""Ejecuta una llamada a la API en un hilo aparte.

Todas las páginas llaman a `requests` de forma síncrona. Si eso corre en el
hilo principal de Qt, la ventana entera se congela mientras espera la
respuesta del backend (especialmente notorio contra el backend en Render,
con latencia de red real). Este worker corre esa llamada en un QThread y
entrega el resultado (o el error) de vuelta al hilo principal por señal,
para que la interfaz siga respondiendo mientras se espera.

El hilo NO es hijo de la página que lo pidió: antes lo era, y al cerrar
sesión (o salir) mientras una página seguía cargando, Qt destruía el QThread
en plena ejecución y abortaba todo el proceso ("QThread: Destroyed while
thread is still running", código 0xC0000409). Ahora el hilo sigue vivo hasta
terminar; si la página ya no existe, su resultado simplemente se descarta.
"""

from PySide6.QtCore import QThread, Signal

# Referencias a los hilos en curso: sin esto, Python podría recolectar un
# QThread sin padre mientras todavía corre.
_running: set["AsyncWorker"] = set()


class AsyncWorker(QThread):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, fn, parent=None):
        super().__init__()
        self._fn = fn
        _running.add(self)
        self.finished.connect(self._cleanup)
        if parent is not None:
            parent.destroyed.connect(self._orphan)

    def run(self) -> None:
        try:
            result = self._fn()
        except Exception as exc:  # se reporta al hilo principal, no debe crashear el worker
            self.failed.emit(str(exc))
        else:
            self.succeeded.emit(result)

    def _orphan(self, *_args) -> None:
        # La página se destruyó: nadie debe recibir este resultado.
        for signal in (self.succeeded, self.failed):
            try:
                signal.disconnect()
            except (RuntimeError, TypeError):
                pass

    def _cleanup(self) -> None:
        _running.discard(self)
        self.deleteLater()


def wait_for_workers(timeout_ms: int = 1500) -> None:
    """Al salir de la app: espera un momento a los hilos en curso para que
    el proceso no termine con un QThread todavía corriendo."""
    for worker in list(_running):
        _orphan_and_wait(worker, timeout_ms)


def _orphan_and_wait(worker: AsyncWorker, timeout_ms: int) -> None:
    worker._orphan()
    if not worker.wait(timeout_ms):
        # Una petición colgada (timeout de red de 20 s): al cerrar la app no
        # tiene sentido esperarla.
        worker.terminate()
        worker.wait(500)
