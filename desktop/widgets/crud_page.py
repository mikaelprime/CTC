from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from PySide6.QtCore import QDate, QTime, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from api_client import ApiError


@dataclass
class Column:
    key: str
    label: str
    formatter: Optional[Callable[[dict], str]] = None


@dataclass
class Field:
    name: str
    label: str
    kind: str = "text"  # text, int, float, date, time, combo, bool
    options: Optional[Callable[[], list]] = None  # combo: () -> list[(label, value)]
    default: Any = None
    minimum: float = 0
    maximum: float = 10_000_000


class RecordDialog(QDialog):
    def __init__(self, title: str, fields: list[Field], parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(360)
        self.fields = fields
        self.inputs: dict[str, QWidget] = {}

        layout = QFormLayout(self)
        for f in fields:
            widget = self._build_widget(f)
            self.inputs[f.name] = widget
            layout.addRow(f.label, widget)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _build_widget(self, f: Field) -> QWidget:
        if f.kind == "int":
            w = QSpinBox()
            w.setRange(int(f.minimum), int(f.maximum))
            w.setValue(int(f.default) if f.default is not None else 0)
            return w
        if f.kind == "float":
            w = QDoubleSpinBox()
            w.setRange(f.minimum, f.maximum)
            w.setDecimals(2)
            w.setValue(float(f.default) if f.default is not None else 0.0)
            return w
        if f.kind == "date":
            w = QDateEdit()
            w.setCalendarPopup(True)
            w.setDate(QDate.currentDate())
            return w
        if f.kind == "time":
            w = QTimeEdit()
            w.setTime(QTime(8, 0))
            return w
        if f.kind == "combo":
            w = QComboBox()
            for label, value in (f.options() if f.options else []):
                w.addItem(label, value)
            return w
        if f.kind == "bool":
            w = QComboBox()
            w.addItem("Sí", True)
            w.addItem("No", False)
            return w
        w = QLineEdit()
        if f.default is not None:
            w.setText(str(f.default))
        return w

    def values(self) -> dict:
        result: dict[str, Any] = {}
        for f in self.fields:
            w = self.inputs[f.name]
            if f.kind == "int":
                result[f.name] = w.value()
            elif f.kind == "float":
                result[f.name] = w.value()
            elif f.kind == "date":
                result[f.name] = w.date().toString("yyyy-MM-dd")
            elif f.kind == "time":
                result[f.name] = w.time().toString("HH:mm:ss")
            elif f.kind in ("combo", "bool"):
                result[f.name] = w.currentData()
            else:
                result[f.name] = w.text()
        return result


class CrudPage(QWidget):
    """A list view with an optional 'create' dialog, backed by API callables."""

    def __init__(
        self,
        title: str,
        subtitle: str,
        columns: list[Column],
        fetch_fn: Callable[[], list],
        create_spec: Optional[list[Field]] = None,
        create_fn: Optional[Callable[[dict], Any]] = None,
        create_label: str = "Nuevo",
        delete_fn: Optional[Callable[[dict], Any]] = None,
        empty_message: str = "No hay registros todavía.",
        parent=None,
    ):
        super().__init__(parent)
        self.columns = columns
        self.fetch_fn = fetch_fn
        self.create_spec = create_spec
        self.create_fn = create_fn
        self.delete_fn = delete_fn
        self.empty_message = empty_message
        self._rows: list[dict] = []

        layout = QVBoxLayout(self)
        header = QLabel(title)
        header.setObjectName("PageTitle")
        sub = QLabel(subtitle)
        sub.setObjectName("PageSubtitle")
        layout.addWidget(header)
        layout.addWidget(sub)

        toolbar = QHBoxLayout()
        refresh_btn = QPushButton("⟳ Actualizar")
        refresh_btn.clicked.connect(self.reload)
        toolbar.addWidget(refresh_btn)
        toolbar.addStretch()
        if create_spec and create_fn:
            add_btn = QPushButton(f"➕ {create_label}")
            add_btn.setProperty("class", "primary")
            add_btn.clicked.connect(self.on_create)
            toolbar.addWidget(add_btn)
        layout.addLayout(toolbar)

        extra_cols = 1 if delete_fn else 0
        self.table = QTableWidget()
        self.table.setColumnCount(len(columns) + extra_cols)
        self.table.setHorizontalHeaderLabels([c.label for c in columns] + (["Acciones"] if delete_fn else []))
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

        self.status_label = QLabel("")
        self.status_label.setObjectName("PageSubtitle")
        layout.addWidget(self.status_label)

        self.reload()

    def reload(self) -> None:
        try:
            self._rows = self.fetch_fn() or []
            self.status_label.setText(self.empty_message if not self._rows else "")
        except ApiError as exc:
            QMessageBox.critical(self, "Error", str(exc))
            self._rows = []
            self.status_label.setText(str(exc))
        self._render_rows()

    def _render_rows(self) -> None:
        self.table.setRowCount(len(self._rows))
        self.table.verticalHeader().setDefaultSectionSize(40)
        for r, row in enumerate(self._rows):
            for c, col in enumerate(self.columns):
                text = col.formatter(row) if col.formatter else str(row.get(col.key, ""))
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(r, c, item)
            if self.delete_fn:
                btn = QPushButton("Eliminar")
                btn.setStyleSheet("padding: 3px 10px;")
                btn.clicked.connect(lambda _checked=False, row=row: self.on_delete(row))
                self.table.setCellWidget(r, len(self.columns), btn)

    def on_create(self) -> None:
        dialog = RecordDialog(f"Registrar", self.create_spec, self)
        if dialog.exec() != QDialog.Accepted:
            return
        payload = dialog.values()
        try:
            self.create_fn(payload)
        except ApiError as exc:
            QMessageBox.critical(self, "Error", str(exc))
            return
        self.reload()

    def on_delete(self, row: dict) -> None:
        if QMessageBox.question(self, "Confirmar", "¿Eliminar este registro?") != QMessageBox.Yes:
            return
        try:
            self.delete_fn(row)
        except ApiError as exc:
            QMessageBox.critical(self, "Error", str(exc))
            return
        self.reload()
