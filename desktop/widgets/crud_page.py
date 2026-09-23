from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from PySide6.QtCore import QDate, QRegularExpression, QTime, Qt, QTimer
from PySide6.QtGui import QRegularExpressionValidator
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
    # Texto: ayuda visible, caracteres permitidos (regex de Qt, bloquea al
    # teclear, p. ej. letras en un teléfono), máscara fija (DUI) y largo.
    placeholder: Optional[str] = None
    regex: Optional[str] = None
    input_mask: Optional[str] = None
    max_length: Optional[int] = None
    # Fecha: rango permitido en días relativos a hoy (p. ej. un nacimiento
    # no puede ser hoy ni futuro: max_days=-1). None = sin límite.
    min_days: Optional[int] = None
    max_days: Optional[int] = None
    # Fecha inicial en días relativos a hoy (por defecto, hoy).
    default_days: int = 0
    # Texto obligatorio: se avisa antes de enviar.
    required: bool = False


class RecordDialog(QDialog):
    def __init__(
        self,
        title: str,
        fields: list[Field],
        parent=None,
        initial: Optional[dict] = None,
        submit: Optional[Callable[[dict], Any]] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(360)
        self.fields = fields
        self.inputs: dict[str, QWidget] = {}
        # Si hay `submit`, el diálogo envía los datos él mismo y solo se
        # cierra si el servidor los acepta: ante un error de validación se
        # muestra el mensaje y se queda abierto para corregir, sin perder lo
        # ya escrito.
        self.submit = submit
        self.result_data: Any = None

        self.form = QFormLayout(self)
        for f in fields:
            widget = self._build_widget(f)
            if initial and f.name in initial and initial[f.name] is not None:
                self._apply_value(widget, f, initial[f.name])
            self.inputs[f.name] = widget
            self.form.addRow(f"{f.label} *" if f.required else f.label, widget)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self._on_accept)
        self.buttons.rejected.connect(self.reject)
        self.form.addRow(self.buttons)

    def add_row(self, label: str, widget: QWidget) -> None:
        """Agrega una fila extra (p. ej. "Cambio:") justo antes de los botones."""
        self.form.insertRow(self.form.rowCount() - 1, label, widget)

    def _on_accept(self) -> None:
        missing = [
            f.label for f in self.fields
            if f.required and f.kind == "text" and not self.inputs[f.name].text().strip()
        ]
        if missing:
            QMessageBox.warning(self, "Faltan datos", "Completa: " + ", ".join(missing))
            return
        if self.submit is None:
            self.accept()
            return
        try:
            self.result_data = self.submit(self.values())
        except ApiError as exc:
            QMessageBox.critical(self, "Revisa los datos", str(exc))
            return
        self.accept()

    @staticmethod
    def _apply_value(widget: QWidget, f: Field, value: Any) -> None:
        # Precarga el diálogo con los datos actuales del registro al editar,
        # en vez de mostrarlo siempre en blanco como en modo "crear".
        if f.kind == "int":
            widget.setValue(int(value))
        elif f.kind == "float":
            widget.setValue(float(value))
        elif f.kind == "date":
            widget.setDate(QDate.fromString(str(value)[:10], "yyyy-MM-dd"))
        elif f.kind == "time":
            widget.setTime(QTime.fromString(str(value)[:8], "HH:mm:ss"))
        elif f.kind in ("combo", "bool"):
            index = widget.findData(value)
            if index >= 0:
                widget.setCurrentIndex(index)
        else:
            widget.setText(str(value))

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
            w.setDisplayFormat("dd/MM/yyyy")
            today = QDate.currentDate()
            if f.min_days is not None:
                w.setMinimumDate(today.addDays(f.min_days))
            if f.max_days is not None:
                w.setMaximumDate(today.addDays(f.max_days))
            w.setDate(today.addDays(f.default_days))
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
        if f.input_mask:
            w.setInputMask(f.input_mask)
        if f.regex:
            w.setValidator(QRegularExpressionValidator(QRegularExpression(f.regex), w))
        if f.max_length:
            w.setMaxLength(f.max_length)
        if f.placeholder:
            w.setPlaceholderText(f.placeholder)
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
                text = w.text().strip()
                # Con máscara (DUI) un campo vacío devuelve solo el guion.
                if f.input_mask and not any(ch.isalnum() for ch in text):
                    text = ""
                result[f.name] = text
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
        edit_spec: Optional[list[Field]] = None,
        update_fn: Optional[Callable[[dict, dict], Any]] = None,
        empty_message: str = "No hay registros todavía.",
        extra_actions: Optional[list[tuple[str, Callable[[dict], Any], Callable[[dict], bool]]]] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.columns = columns
        self.fetch_fn = fetch_fn
        self.create_spec = create_spec
        self.create_fn = create_fn
        self.delete_fn = delete_fn
        self.edit_spec = edit_spec
        self.update_fn = update_fn
        # (texto del botón, acción(fila), visible_para(fila))
        self.extra_actions = extra_actions or []
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

        self._has_actions = bool(delete_fn or (edit_spec and update_fn) or self.extra_actions)
        extra_cols = 1 if self._has_actions else 0
        self.table = QTableWidget()
        self.table.setColumnCount(len(columns) + extra_cols)
        self.table.setHorizontalHeaderLabels([c.label for c in columns] + (["Acciones"] if self._has_actions else []))
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

    def visible_rows(self) -> list[dict]:
        """Las filas que se ven ahora (aplicando el buscador)."""
        query = self.search_input.text().strip().lower()
        return [
            row
            for row, haystack in zip(self._rows, self._search_cache)
            if not query or query in haystack
        ]

    def _render_rows(self) -> None:
        rows = self.visible_rows()
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
                if self._has_actions:
                    cell = QWidget()
                    cell_layout = QHBoxLayout(cell)
                    cell_layout.setContentsMargins(0, 0, 0, 0)
                    cell_layout.setSpacing(6)
                    if self.edit_spec and self.update_fn:
                        edit_btn = QPushButton("Editar")
                        edit_btn.setStyleSheet("padding: 3px 10px;")
                        edit_btn.clicked.connect(lambda _checked=False, row=row: self.on_edit(row))
                        cell_layout.addWidget(edit_btn)
                    for label, action, visible in self.extra_actions:
                        if not visible(row):
                            continue
                        extra_btn = QPushButton(label)
                        extra_btn.setStyleSheet("padding: 3px 10px;")
                        extra_btn.clicked.connect(lambda _checked=False, row=row, action=action: action(row))
                        cell_layout.addWidget(extra_btn)
                    if self.delete_fn:
                        del_btn = QPushButton("Eliminar")
                        del_btn.setStyleSheet("padding: 3px 10px;")
                        del_btn.clicked.connect(lambda _checked=False, row=row: self.on_delete(row))
                        cell_layout.addWidget(del_btn)
                    cell_layout.addStretch()
                    self.table.setCellWidget(r, len(self.columns), cell)
        finally:
            self.table.setUpdatesEnabled(True)

    def _search_text(self, value: Any) -> str:
        if isinstance(value, dict):
            return " ".join(self._search_text(item) for item in value.values())
        if isinstance(value, (list, tuple)):
            return " ".join(self._search_text(item) for item in value)
        return str(value)

    def prepare_dialog(self, dialog: RecordDialog) -> None:
        """Gancho para que una página agregue lógica al formulario (p. ej.
        calcular la edad o el cambio en vivo)."""

    def after_create(self, result: Any) -> None:
        """Gancho que recibe la respuesta del servidor tras crear."""

    def on_create(self) -> None:
        dialog = RecordDialog("Registrar", self.create_spec, self, submit=self.create_fn)
        self.prepare_dialog(dialog)
        if dialog.exec() != QDialog.Accepted:
            return
        self.after_create(dialog.result_data)
        self.reload()

    def on_edit(self, row: dict) -> None:
        dialog = RecordDialog(
            "Editar registro", self.edit_spec, self, initial=row,
            submit=lambda payload: self.update_fn(row, payload),
        )
        self.prepare_dialog(dialog)
        if dialog.exec() != QDialog.Accepted:
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
