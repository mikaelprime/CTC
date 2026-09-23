"""Ticket de cobro imprimible (mejora recomendada del PDF de la propuesta:
"El sistema imprime y/o envía comprobante Ticket"). El envío por correo ya
existe (email_service.py en el backend); esto cubre la parte de "imprime".

Usa QTextDocument + QPrinter en vez de generar un PDF aparte: es lo más
simple que soporta PySide6 sin agregar una librería nueva solo para esto, y
abre el diálogo de impresión estándar de Windows para que el cajero elija
la impresora (o "Guardar como PDF", que Windows ya trae integrado).
"""

from PySide6.QtGui import QTextDocument
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import QWidget

from theme import BORDER, PRIMARY_DARK, TEXT, TEXT_MUTED


def print_ticket(parent: QWidget, title: str, rows: list[tuple[str, str]], footer: str = "") -> None:
    """Abre el diálogo de impresión de Windows con un ticket simple.

    `rows` es una lista de (etiqueta, valor) que se muestran como una tabla
    de dos columnas, en el orden dado.
    """
    rows_html = "".join(
        f"<tr><td style='color:{TEXT_MUTED};padding:3px 0'>{label}</td>"
        f"<td style='text-align:right;font-weight:bold;padding:3px 0'>{value}</td></tr>"
        for label, value in rows
    )
    html = f"""
    <html><body style="font-family:Arial;color:{TEXT};width:280px">
      <div style="text-align:center;border-bottom:2px solid {PRIMARY_DARK};padding-bottom:8px;margin-bottom:10px">
        <div style="font-size:11px;letter-spacing:2px;color:{PRIMARY_DARK};font-weight:bold">CTC EL SALVADOR</div>
        <div style="font-size:15px;font-weight:bold;margin-top:4px">{title}</div>
      </div>
      <table style="width:100%;border-collapse:collapse;font-size:12px">{rows_html}</table>
      <div style="border-top:1px dashed {BORDER};margin-top:10px;padding-top:8px;font-size:10px;color:{TEXT_MUTED};text-align:center">
        {footer}
      </div>
    </body></html>
    """
    document = QTextDocument()
    document.setHtml(html)

    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    dialog = QPrintDialog(printer, parent)
    dialog.setWindowTitle("Imprimir ticket")
    if dialog.exec() == QPrintDialog.DialogCode.Accepted:
        document.print_(printer)
