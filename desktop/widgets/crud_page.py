from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from PySide6.QtCore import QDate, QTime, Qt, QTimer
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
from widgets.animated_button import AnimatedButton
from widgets.async_worker import AsyncWorker


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
        self._search_cache: list[str] = []
        self._load_worker: Optional[AsyncWorker] = None

        # Recalcular y reconstruir la tabla en cada tecla se siente pesado con
        # varias decenas de filas. Se espera una pausa corta antes de filtrar,
        # igual que hacen la mayoría de buscadores.
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(200)
        self._search_timer.timeout.connect(self._render_rows)

        layout = QVBoxLayout(self)
        header = QLabel(title)
        header.setObjectName("PageTitle")
        sub = QLabel(subtitle)
        sub.setObjectName("PageSubtitle")
        layout.addWidget(header)
        layout.addWidget(sub)

        toolbar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar por nombre, correo o cualquier dato...")
        self.search_input.textChanged.connect(self._search_timer.start)
        toolbar.addWidget(self.search_input, stretch=1)
        refresh_btn = AnimatedButton("⟳ Actualizar")
        refresh_btn.clicked.connect(self.reload)
        toolbar.addWidget(refresh_btn)
        toolbar.addStretch()
        if create_spec and create_fn:
            add_btn = AnimatedButton(f"➕ {create_label}")
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
        # La petición corre en un hilo aparte para no congelar la ventana
        # mientras se espera la respuesta del backend.
        self.status_label.setText("Cargando…")
        worker = AsyncWorker(self.fetch_fn, self)
        self._load_worker = worker
        worker.succeeded.connect(lambda rows: self._on_loaded(worker, rows))
        worker.failed.connect(lambda message: self._on_load_failed(worker, message))
        worker.start()

    def _on_loaded(self, worker: AsyncWorker, rows) -> None:
        if worker is not self._load_worker:
            return  # una carga más reciente ya está en curso o terminó
        self._rows = rows or []
        self.status_label.setText(self.empty_message if not self._rows else "")
        # El texto de búsqueda de cada fila se calcula una sola vez aquí en
        # vez de en cada tecla presionada en el buscador.
        self._search_cache = [self._search_text(row).lower() for row in self._rows]
        self._render_rows()

    def _on_load_failed(self, worker: AsyncWorker, message: str) -> None:
        if worker is not self._load_worker:
            return
        QMessageBox.critical(self, "Error", message)
        self._rows = []
        self._search_cache = []
        self.status_label.setText(message)
        self._render_rows()

    def _render_rows(self) -> None:
        query = self.search_input.text().strip().lower()
        rows = [
            row
            for row, haystack in zip(self._rows, self._search_cache)
            if not query or query in haystack
        ]
        self.table.setUpdatesEnabled(False)
        try:
            self.table.setRowCount(len(rows))
            self.table.verticalHeader().setDefaultSectionSize(40)
            for r, row in enumerate(rows):
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
        finally:
            self.table.setUpdatesEnabled(True)

    def _search_text(self, value: Any) -> str:
        if isinstance(value, dict):
            return " ".join(self._search_text(item) for item in value.values())
        if isinstance(value, (list, tuple)):
            return " ".join(self._search_text(item) for item in value)
        return str(value)

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
