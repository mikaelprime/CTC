"""Reportes de cierre de caja, ticket del comprobante y arqueo: se arman
bien a partir de las respuestas del API (sin pantalla ni red)."""

from pages.cash_reports import daily_report, monthly_report, register_report
from pages.matricula_dialog import registration_fee
from pages.payments_page import denomination_total, receipt_label
from widgets.receipt_view import fmt_date, ticket_rows, whatsapp_message, whatsapp_url

SUMMARY = {
    "total": 73.0, "cash_total": 45.0, "receipts": 2, "installments": 2, "registrations": 1,
    "by_concept": [{"concept": "Matrícula completa", "amount": 20.0},
                   {"concept": "Colegiatura Plan Grupal", "amount": 50.0},
                   {"concept": "Recargos por mora", "amount": 3.0}],
    "by_method": [{"method": "Efectivo", "amount": 45.0}, {"method": "Tarjeta", "amount": 28.0}],
    "voided_total": 0.0,
}
PAYMENT = {
    "payment_id": 5, "receipt_number": "R-000002", "time": "28/09/2026 10:15", "student_name": "Ana Pérez",
    "diploma_name": "Marketing Digital", "concept": "Colegiatura Plan Grupal", "due_date": "2026-08-29",
    "payment_type": "Efectivo", "amount": 25.0, "surcharge": 3.0, "total": 28.0, "status": "PAGADO",
    "cashier_name": "Cajero CTC",
}
REGISTER = {
    "register_id": 7, "cashier_name": "Cajero CTC", "opened_at": "28/09/2026 08:00",
    "closed_at": "28/09/2026 17:00", "is_open": False, "initial_amount": 10.0, "collected_amount": 73.0,
    "cash_amount": 45.0, "expected_amount": 55.0, "physical_amount": 55.0, "difference": 0.0,
    "audit_explanation": None, "cash_count": {"20.00": 2, "10.00": 1, "5.00": 1},
    "summary": SUMMARY, "payments": [PAYMENT],
}
TICKET = {
    "institution_name": "CTC El Salvador", "receipt_number": "R-000002", "issued_at": "28/09/2026 10:15",
    "status": "EMITIDO", "kind": "COLEGIATURA", "cashier_name": "Cajero CTC", "enrollment_id": 3,
    "student_name": "Ana Pérez", "student_email": "ana@correo.com", "whatsapp": "7123-4567",
    "diploma_name": "Marketing Digital", "schedule_name": "Sábados 8:00 - 10:15", "tuition_plan": "Plan Grupal",
    "lines": [{"payment_id": 5, "concept": "Colegiatura cuota 2 de 7 (vence 29/08/2026)", "amount": "25.00",
               "surcharge": "3.00", "total": "28.00", "status": "PAGADO"}],
    "surcharge": "3.00", "total": "28.00", "payment_type": "Efectivo", "cash_received": "30.00",
    "change": "2.00", "next_payment_date": "2026-09-26", "installments_paid": 2, "installments_total": 7,
}


def test_register_report_has_arqueo_breakdown_and_payments():
    report = register_report(REGISTER)
    assert report.title == "Cierre de caja #7 — Cajero CTC"
    assert ("Efectivo esperado en caja", 55.0) in report.summary
    assert ("Diferencia", 0.0) in report.summary
    titles = [s.title for s in report.sections]
    assert titles == ["Totales por concepto", "Totales por método de pago", "Arqueo por denominación", "Cobros de la caja"]
    count = report.sections[2]
    assert count.rows[0] == ["$20.00", 2, 40.0]
    assert report.sections[3].rows[0][0] == "R-000002"
    assert report.sections[3].rows[0][5] == "29/08/2026"


def test_open_register_report_has_no_count_or_difference():
    report = register_report({**REGISTER, "is_open": True, "cash_count": None, "physical_amount": None, "difference": None})
    labels = [label for label, _ in report.summary]
    assert "Diferencia" not in labels and "CAJA ABIERTA" in report.subtitle
    assert "Arqueo por denominación" not in [s.title for s in report.sections]


def test_daily_and_monthly_reports():
    daily = daily_report({"date": "2026-09-28", "summary": SUMMARY, "payments": [PAYMENT], "registers": []})
    assert daily.title == "Cierre diario 28/09/2026"
    assert ("Total cobrado", 73.0) in daily.summary
    monthly = monthly_report({
        "periodo": "2026-09", "cajas_cerradas": 1, "total_cobrado_mes": 73.0, "total_efectivo_mes": 45.0,
        "total_esperado_cajas": 55.0, "total_efectivo_contado": 55.0, "total_descuadres_mes": 0.0,
        "summary": SUMMARY, "by_day": [{"date": "2026-09-28", "total": 73.0, "cash": 45.0}], "registers": [],
    })
    by_day = next(s for s in monthly.sections if s.title == "Cobros por día")
    assert by_day.rows == [["28/09/2026", 73.0, 45.0]]


def test_ticket_rows_and_whatsapp():
    rows = dict(ticket_rows(TICKET))
    assert rows["Comprobante"] == "R-000002"
    assert rows["Colegiatura cuota 2 de 7 (vence 29/08/2026)"] == "$25.00"
    assert rows["Recargo por mora"] == "$3.00"
    assert rows["TOTAL"] == "$28.00" and rows["Cambio"] == "$2.00"
    assert rows["Próximo pago"] == "26/09/2026"
    url = whatsapp_url(TICKET["whatsapp"], whatsapp_message(TICKET))
    assert url.startswith("https://wa.me/50371234567?text=")
    assert whatsapp_url("+1 213 555 0199", "hola") == "https://wa.me/12135550199?text=hola"
    assert whatsapp_url("123", "hola") is None


def test_helpers():
    assert fmt_date("2026-08-29") == "29/08/2026"
    assert fmt_date(None) == "—"
    assert denomination_total({"20.00": 2, "0.25": 3}) == 40.75
    assert receipt_label({"id": 9, "receipt_id": 12}) == "R-000012"
    assert receipt_label({"id": 9, "receipt_id": None}) == "PAGO-000009"
    config = {"registration_full_fee": 20.0, "registration_promo_fee": 10.0}
    assert (registration_fee(config, "COMPLETA"), registration_fee(config, "PROMO"), registration_fee(config, "GRATIS")) == (20.0, 10.0, 0.0)
