from PySide6.QtWidgets import QDialog, QLabel, QLineEdit, QWidget

from api_client import api
from widgets.crud_page import Field, RecordDialog


def change_password_dialog(parent: QWidget | None, required: bool = False) -> bool:
    """Diálogo para cambiar la propia contraseña. Con `required=True` es el
    primer ingreso con una contraseña temporal: la API no deja hacer nada más
    hasta cambiarla. True si se cambió."""
    fields = [
        Field("current_password", "Contraseña actual", required=True),
        Field("new_password", "Nueva contraseña", regex=r"^\S*$", max_length=128,
              placeholder="Mínimo 6, con letras y números", required=True),
    ]
    dialog = RecordDialog(
        "Cambia tu contraseña temporal" if required else "Cambiar mi contraseña", fields, parent,
        submit=lambda values: api.post("/auth/change-password", json=values),
    )
    if required:
        notice = QLabel(
            "Tu contraseña es temporal (la asignó el administrador o es la de instalación).\n"
            "Por seguridad, elige una nueva para continuar."
        )
        notice.setWordWrap(True)
        dialog.form.insertRow(0, notice)
    for name in ("current_password", "new_password"):
        dialog.inputs[name].setEchoMode(QLineEdit.Password)
    if dialog.exec() != QDialog.Accepted:
        return False
    api.must_change_password = False
    return True
