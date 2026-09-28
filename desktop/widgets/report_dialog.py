"""Ver un reporte en pantalla (resumen + tablas) con botones para imprimirlo
o exportarlo a Excel/PDF. Lo usan los cierres de caja (diario, por caja y
mensual) y el estado de cuenta."""

from PySide6.QtCore import QMarginsF
from PySide6.QtGui import QPageLayout, QPageSize, QTextDocument
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QHeaderView,
    QLabel,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from widgets.animated_button import AnimatedButton
from widgets.report_export import Report, export_report, report_html


def _cell(value, money: bool) -> str:
    if money:
        try:
            return f"${float(value):,.2f}"
        except (TypeError, ValueError):
            return "" if value is None else str(value)
    return "" if value is None else str(value)


def print_report(parent: QWidget, report: Report) -> None:
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setPageLayout(QPageLayout(
        QPageSize(QPageSize.PageSizeId.Letter), QPageLayout.Orientation.Landscape,
        QMarginsF(12, 12, 12, 12), QPageLayout.Unit.Millimeter,
    ))
    dialog = QPrintDialog(printer, parent)
    dialog.setWindowTitle("Imprimir reporte")
    if dialog.exec() != QPrintDialog.DialogCode.Accepted:
        return
    document = QTextDocument()
    document.setHtml(report_html(report))
    document.print_(printer)


class ReportDialog(QDialog):
    def __init__(self, report: Report, file_stem: str, parent=None):
        super().__init__(parent)
        self.report = report
        self.file_stem = file_stem
        self.setWindowTitle(report.title)
        self.setMinimumSize(960, 620)
        layout = QVBoxLayout(self)

        title = QLabel(report.title)
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        if report.subtitle:
            subtitle = QLabel(report.subtitle)
            subtitle.setObjectName("PageSubtitle")
            subtitle.setWordWrap(True)
            layout.addWidget(subtitle)

        grid = QGridLayout()
        per_row = 4
        for index, (label, value) in enumerate(report.summary):
            caption = QLabel(label)
            caption.setObjectName("SummaryCaption")
            shown = QLabel(f"${value:,.2f}" if isinstance(value, float) else str(value))
            shown.setObjectName("SummaryValue")
            row, col = divmod(index, per_row)
            grid.addWidget(caption, row * 2, col)
            grid.addWidget(shown, row * 2 + 1, col)
        layout.addLayout(grid)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        for section in report.sections:
            heading = QLabel(section.title)
            heading.setObjectName("SectionTitle")
            body_layout.addWidget(heading)
            table = QTableWidget(len(section.rows), len(section.headers))
            table.setHorizontalHeaderLabels(section.headers)
            table.verticalHeader().setVisible(False)
            table.setEditTriggers(QTableWidget.NoEditTriggers)
            for r, row in enumerate(section.rows):
                for c, value in enumerate(row):
                    table.setItem(r, c, QTableWidgetItem(_cell(value, c in section.money)))
            table.resizeColumnsToContents()
            table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
            table.horizontalHeader().setStretchLastSection(True)
            table.setMinimumHeight(min(80 + 32 * len(section.rows), 320))
            if not section.rows:
                empty = QLabel("Sin registros")
                empty.setObjectName("PageSubtitle")
                body_layout.addWidget(empty)
            else:
                body_layout.addWidget(table)
        body_layout.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(body)
        layout.addWidget(scroll, stretch=1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        print_button = AnimatedButton("Imprimir")
        print_button.clicked.connect(lambda: print_report(self, self.report))
        export_button = AnimatedButton("Exportar Excel / PDF")
        export_button.setProperty("class", "primary")
        export_button.clicked.connect(lambda: export_report(self, self.report, self.file_stem))
        buttons.addButton(print_button, QDialogButtonBox.ActionRole)
        buttons.addButton(export_button, QDialogButtonBox.ActionRole)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


def show_report(parent: QWidget, report: Report, file_stem: str) -> None:
    ReportDialog(report, file_stem, parent).exec()
