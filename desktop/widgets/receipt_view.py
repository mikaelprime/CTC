"""Comprobante de un cobro: resumen en pantalla y acciones (imprimir, guardar
PDF, enviar por WhatsApp).

Los datos vienen del servidor (/receipts/{id} o /payments/{id}/ticket), así
el ticket del momento del cobro y una reimpresión posterior son idénticos:
mismo número correlativo, mismas cuotas y mismo cajero.
"""

from urllib.parse import quote

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox, QWidget

from api_client import ApiError, api
from widgets.ticket_printer import print_ticket, save_ticket_pdf


def money(value) -> str:
    return f"${float(value or 0):,.2f}"


def fmt_date(value) -> str:
    """"2026-08-29" → "29/08/2026" (formato de El Salvador)."""
    if not value:
        return "—"
    text = str(value)[:10]
    parts = text.split("-")
    return f"{parts[2]}/{parts[1]}/{parts[0]}" if len(parts) == 3 else text


def ticket_rows(ticket: dict) -> list[tuple[str, str]]:
    rows = [
        ("Comprobante", ticket["receipt_number"]),
        ("Estudiante", ticket["student_name"]),
        ("Programa", ticket["diploma_name"]),
        ("Horario", ticket["schedule_name"]),
        ("Plan", ticket["tuition_plan"]),
    ]
    for line in ticket["lines"]:
        rows.append((line["concept"], money(line["amount"])))
    if float(ticket.get("surcharge") or 0) > 0:
        rows.append(("Recargo por mora", money(ticket["surcharge"])))
    rows += [
        ("TOTAL", money(ticket["total"])),
        ("Método de pago", ticket["payment_type"]),
        ("Efectivo recibido", money(ticket["cash_received"])),
        ("Cambio", money(ticket["change"])),
        ("Cuotas pagadas", f"{ticket['installments_paid']} de {ticket['installments_total']}"),
        ("Próximo pago", fmt_date(ticket["next_payment_date"]) if ticket.get("next_payment_date") else "Colegiaturas completas"),
        ("Atendió", ticket.get("cashier_name") or "—"),
    ]
    return rows


def _title(ticket: dict) -> str:
    base = "Comprobante de matrícula" if ticket.get("kind") == "MATRICULA" else "Comprobante de pago"
    return f"{base} — ANULADO" if ticket.get("status") == "ANULADO" else base


def _style(ticket: dict) -> dict:
    return {"header": ticket.get("institution_name") or "CTC El Salvador", "stamp": ticket.get("issued_at")}


def whatsapp_message(ticket: dict) -> str:
    next_payment = (
        f"Próximo pago: {fmt_date(ticket['next_payment_date'])}."
        if ticket.get("next_payment_date") else "Ya completó todas sus colegiaturas."
    )
    return (
        f"{ticket.get('institution_name') or 'CTC El Salvador'} — {_title(ticket)} {ticket['receipt_number']}\n"
        f"Estudiante: {ticket['student_name']}\n"
        f"Programa: {ticket['diploma_name']}\n"
        f"Total pagado: {money(ticket['total'])} ({ticket['payment_type']})\n"
        f"{next_payment}\n¡Gracias por su pago!"
    )


def whatsapp_url(phone: str | None, text: str) -> str | None:
    """wa.me con el mensaje ya escrito (gratis, sin API). Números de 8
    dígitos se toman como de El Salvador (+503)."""
    if not phone:
        return None
    digits = "".join(ch for ch in phone if ch.isdigit())
    if not phone.strip().startswith("+"):
        if len(digits) != 8:
            return None
        digits = f"503{digits}"
    return f"https://wa.me/{digits}?text={quote(text)}"


def open_url(url: str) -> None:
    QDesktopServices.openUrl(QUrl(url))


def show_ticket(parent: QWidget, ticket: dict, intro: str = "") -> None:
    """Muestra el resumen del comprobante con sus acciones."""
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Information)
    box.setWindowTitle(f"{_title(ticket)} {ticket['receipt_number']}")
    summary = (
        f"{intro}\n\n" if intro else ""
    ) + (
        f"Comprobante: {ticket['receipt_number']}\n"
        f"Total: {money(ticket['total'])} ({ticket['payment_type']})\n"
        f"Efectivo: {money(ticket['cash_received'])}   Cambio: {money(ticket['change'])}\n"
        f"Próximo pago: {fmt_date(ticket.get('next_payment_date')) if ticket.get('next_payment_date') else 'Colegiaturas completas'}"
    )
    box.setText(summary)
    print_button = box.addButton("Imprimir ticket", QMessageBox.ActionRole)
    pdf_button = box.addButton("Guardar PDF", QMessageBox.ActionRole)
    url = whatsapp_url(ticket.get("whatsapp"), whatsapp_message(ticket))
    whatsapp_button = box.addButton("Enviar por WhatsApp", QMessageBox.ActionRole) if url else None
    box.addButton("Cerrar", QMessageBox.RejectRole)
    box.exec()
    clicked = box.clickedButton()
    if clicked is print_button:
        print_ticket(parent, _title(ticket), ticket_rows(ticket), "Conserve este comprobante.", **_style(ticket))
    elif clicked is pdf_button:
        save_ticket_pdf(parent, _title(ticket), ticket_rows(ticket), "Conserve este comprobante.",
                        file_stem=f"Comprobante_{ticket['receipt_number']}", **_style(ticket))
    elif whatsapp_button is not None and clicked is whatsapp_button:
        open_url(url)


def show_receipt(parent: QWidget, receipt_id: int, intro: str = "") -> None:
    try:
        ticket = api.get(f"/receipts/{receipt_id}")
    except ApiError as exc:
        QMessageBox.critical(parent, "No se pudo cargar el comprobante", str(exc))
        return
    show_ticket(parent, ticket, intro)


def show_payment_ticket(parent: QWidget, payment_id: int) -> None:
    try:
        ticket = api.get(f"/payments/{payment_id}/ticket")
    except ApiError as exc:
        QMessageBox.critical(parent, "No se pudo cargar el comprobante", str(exc))
        return
    show_ticket(parent, ticket)
