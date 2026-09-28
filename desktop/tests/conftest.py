import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Estas pruebas ejercitan solo funciones puras de cálculo (no abren ventanas
# ni hacen peticiones de red), pero importar api_client sí instancia Qt-less
# módulos de red; con QT_QPA_PLATFORM=offscreen cualquier import accidental
# de PySide6 no revienta por falta de display.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


import pytest


@pytest.fixture(scope="session")
def qapp():
    """QApplication para las pruebas que usan Qt sin ventanas (p. ej. el PDF)."""
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])
