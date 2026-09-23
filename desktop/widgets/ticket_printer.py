"""Ticket de cobro imprimible (mejora recomendada del PDF de la propuesta:
"El sistema imprime y/o envía comprobante Ticket"). El envío por correo ya
existe (email_service.py en el backend); esto cubre la parte de "imprime".

Dos caminos:
- print_ticket: abre el diálogo de impresión de Windows (impresora térmica,
  de tinta, etc.).
- save_ticket_pdf: guarda el ticket como PDF directamente con el motor PDF de
  Qt, sin pasar por las impresoras de Windows. Sirve aunque el equipo no
  tenga impresora (solo "Microsoft Print to PDF") y para enviar el
  comprobante por WhatsApp.

Colores y tamaños propios de impresión: antes el ticket usaba los colores del
tema oscuro de la app (texto #e6ebff, casi blanco) y tamaños en píxeles, así
que en papel salía prácticamente en blanco y con letra diminuta.
"""

from datetime import datetime
from html import escape
from pathlib import Path

from PySide6.QtCore import QMarginsF, QSizeF, QStandardPaths
from PySide6.QtGui import QPageLayout, QPageSize, QTextDocument
from PySide6.QtPrintSupport import QPrintDialog, QPrinter, QPrinterInfo
from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

_INK = "#111827"
_MUTED = "#4b5563"
_ACCENT = "#0f766e"
_RULE = "#9ca3af"

# Rollo térmico estándar de 80 mm; el alto se ajusta al contenido.
_TICKET_WIDTH_MM = 80.0
_MARGIN_MM = 4.0
_MM_PER_PX = 25.4 / 96  # QTextDocument trabaja en píxeles lógicos de 96 dpi


def _ticket_document(title: str, rows: list[tuple[str, str]], footer: str) -> QTextDocument:
    rows_html = "".join(
        f"<tr><td style='color:{_MUTED};padding:2pt 6pt 2pt 0'>{escape(label)}</td>"
        f"<td align='right' style='font-weight:bold;padding:2pt 0'>{escape(value)}</td></tr>"
        for label, value in rows
    )
    html = f"""
    <html><body style="font-family:Arial;color:{_INK};font-size:9pt">
      <p align="center" style="margin:0;font-size:8pt;letter-spacing:2pt;color:{_ACCENT};font-weight:bold">CTC EL SALVADOR</p>
      <p align="center" style="margin:3pt 0 0 0;font-size:12pt;font-weight:bold">{escape(title)}</p>
      <p align="center" style="margin:1pt 0 6pt 0;font-size:8pt;color:{_MUTED}">{datetime.now():%d/%m/%Y %H:%M}</p>
      <hr style="color:{_ACCENT}"/>
      <table width="100%" cellspacing="0">{rows_html}</table>
      <hr style="color:{_RULE}"/>
      <p align="center" style="margin:4pt 0 0 0;font-size:8pt;color:{_MUTED}">{escape(footer)}</p>
    </body></html>
    """
    document = QTextDocument()
    document.setDocumentMargin(0)
    document.setHtml(html)
    return document


def _fit_to_roll(document: QTextDocument, printer: QPrinter) -> None:
    """Ancho de 80 mm y alto justo al contenido (no una hoja carta con el
    ticket perdido en una esquina)."""
    content_width_px = (_TICKET_WIDTH_MM - 2 * _MARGIN_MM) / _MM_PER_PX
    document.setTextWidth(content_width_px)
    height_px = document.size().height()
    document.setPageSize(QSizeF(content_width_px, height_px))
    printer.setPageLayout(QPageLayout(
        QPageSize(QSizeF(_TICKET_WIDTH_MM, height_px * _MM_PER_PX + 2 * _MARGIN_MM),
                  QPageSize.Unit.Millimeter, "Ticket CTC"),
        QPageLayout.Orientation.Portrait,
        QMarginsF(_MARGIN_MM, _MARGIN_MM, _MARGIN_MM, _MARGIN_MM),
        QPageLayout.Unit.Millimeter,
    ))


def print_ticket(parent: QWidget, title: str, rows: list[tuple[str, str]], footer: str = "") -> None:
    """Abre el diálogo de impresión de Windows con el ticket.

    `rows` es una lista de (etiqueta, valor) que se muestran como una tabla
    de dos columnas, en el orden dado.
    """
    if not QPrinterInfo.availablePrinters():
        answer = QMessageBox.question(
            parent,
            "Sin impresora",
            "Este equipo no tiene ninguna impresora instalada.\n¿Guardar el ticket como PDF?",
        )
        if answer == QMessageBox.Yes:
            save_ticket_pdf(parent, title, rows, footer)
        return

    document = _ticket_document(title, rows, footer)
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    dialog = QPrintDialog(printer, parent)
    dialog.setWindowTitle("Imprimir ticket")
    if dialog.exec() != QPrintDialog.DialogCode.Accepted:
        return
    # El tamaño de papel lo decide la impresora elegida (rollo o carta); el
    # ticket se imprime arriba, con su ancho de 80 mm.
    content_width_px = (_TICKET_WIDTH_MM - 2 * _MARGIN_MM) / _MM_PER_PX
    document.setTextWidth(content_width_px)
    document.setPageSize(QSizeF(content_width_px, max(document.size().height(), 1)))
    document.print_(printer)
    if printer.printerState() == QPrinter.PrinterState.Error:
        answer = QMessageBox.question(
            parent,
            "No se pudo imprimir",
            f"La impresora «{printer.printerName()}» no aceptó el trabajo "
            "(puede estar desconectada o no ser compatible).\n\n¿Guardar el ticket como PDF?",
        )
        if answer == QMessageBox.Yes:
            save_ticket_pdf(parent, title, rows, footer)


def write_ticket_pdf(path: str, title: str, rows: list[tuple[str, str]], footer: str = "") -> bool:
    """Escribe el ticket en `path` (PDF de rollo de 80 mm). True si salió bien."""
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(path)
    document = _ticket_document(title, rows, footer)
    _fit_to_roll(document, printer)
    document.print_(printer)
    return printer.printerState() != QPrinter.PrinterState.Error


def save_ticket_pdf(parent: QWidget, title: str, rows: list[tuple[str, str]], footer: str = "") -> None:
    """Pregunta dónde guardar y guarda el ticket como PDF, sin usar impresoras."""
    folder = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
    suggested = str(Path(folder) / f"Ticket_{datetime.now():%Y%m%d_%H%M%S}.pdf")
    path, _ = QFileDialog.getSaveFileName(parent, "Guardar ticket", suggested, "PDF (*.pdf)")
    if not path:
        return
    if not path.lower().endswith(".pdf"):
        path += ".pdf"
    try:
        ok = write_ticket_pdf(path, title, rows, footer)
    except Exception as exc:  # noqa: BLE001 - se informa al usuario
        QMessageBox.critical(parent, "No se pudo guardar el ticket", str(exc))
        return
    if not ok:
        QMessageBox.critical(parent, "No se pudo guardar el ticket", "Revisa que el archivo no esté abierto en otro programa.")
        return
    QMessageBox.information(parent, "Ticket guardado", f"Se guardó en:\n{path}")
