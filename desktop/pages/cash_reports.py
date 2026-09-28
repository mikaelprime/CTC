"""Reportes de cierre de caja (PDF punto 5): por caja, del día y del mes.

Funciones puras (datos del API → Report) para poder probarlas sin pantalla.
"""

from api_client import api
from widgets.receipt_view import fmt_date
from widgets.report_dialog import show_report
from widgets.report_export import Report, Section

PAYMENT_HEADERS = [
    "Comprobante", "Fecha y hora", "Estudiante", "Programa", "Concepto", "Vence",
    "Método", "Monto", "Recargo", "Total", "Estado", "Cajero",
]
PAYMENT_MONEY = {7, 8, 9}


def _payment_rows(payments: list[dict]) -> list[list]:
    return [
        [p["receipt_number"], p["time"], p["student_name"], p["diploma_name"], p["concept"],
         fmt_date(p["due_date"]), p["payment_type"], float(p["amount"]), float(p["surcharge"]),
         float(p["total"]), p["status"], p["cashier_name"]]
        for p in payments
    ]


def _breakdown_sections(summary: dict) -> list[Section]:
    return [
        Section("Totales por concepto", ["Concepto", "Monto"],
                [[row["concept"], float(row["amount"])] for row in summary["by_concept"]], money={1}),
        Section("Totales por método de pago", ["Método", "Monto"],
                [[row["method"], float(row["amount"])] for row in summary["by_method"]], money={1}),
    ]


def _count_section(cash_count: dict | None) -> list[Section]:
    if not cash_count:
        return []
    rows = [
        [f"${float(value):,.2f}", quantity, float(value) * quantity]
        for value, quantity in sorted(cash_count.items(), key=lambda item: -float(item[0]))
        if quantity
    ]
    return [Section("Arqueo por denominación", ["Denominación", "Cantidad", "Subtotal"], rows, money={2})]


def register_report(data: dict) -> Report:
    summary = data["summary"]
    items = [
        ("Fondo inicial", float(data["initial_amount"])),
        ("Cobrado (todos los métodos)", float(data["collected_amount"])),
        ("Cobrado en efectivo", float(data["cash_amount"])),
        ("Efectivo esperado en caja", float(data["expected_amount"])),
    ]
    if not data["is_open"]:
        items += [
            ("Efectivo contado", float(data["physical_amount"])),
            ("Diferencia", float(data["difference"])),
        ]
    items += [
        ("Comprobantes emitidos", int(summary["receipts"])),
        ("Anulado", float(summary["voided_total"])),
    ]
    period = f"Apertura: {data['opened_at']}" + (
        " · CAJA ABIERTA" if data["is_open"] else f" · Cierre: {data['closed_at']}"
    )
    if data.get("audit_explanation"):
        period += f" · Justificación: {data['audit_explanation']}"
    return Report(
        title=f"Cierre de caja #{data['register_id']} — {data['cashier_name']}",
        subtitle=period,
        summary=items,
        sections=_breakdown_sections(summary) + _count_section(data.get("cash_count")) + [
            Section("Cobros de la caja", PAYMENT_HEADERS, _payment_rows(data["payments"]), money=PAYMENT_MONEY),
        ],
    )


def daily_report(data: dict, cashier_label: str = "Todos los cajeros") -> Report:
    summary = data["summary"]
    registers = [
        [f"#{r['id']}", r["cashier_name"], r["opened_at"], r["closed_at"] or "Abierta",
         float(r["initial_amount"]), float(r["expected_amount"]), float(r["physical_amount"]),
         float(r["difference"]), r.get("audit_explanation") or ""]
        for r in data["registers"]
    ]
    return Report(
        title=f"Cierre diario {fmt_date(data['date'])}",
        subtitle=cashier_label,
        summary=[
            ("Total cobrado", float(summary["total"])),
            ("En efectivo", float(summary["cash_total"])),
            ("Comprobantes", int(summary["receipts"])),
            ("Matrículas", int(summary["registrations"])),
            ("Cuotas de colegiatura", int(summary["installments"])),
            ("Anulado", float(summary["voided_total"])),
        ],
        sections=_breakdown_sections(summary) + [
            Section("Cajas del día", ["Caja", "Cajero", "Apertura", "Cierre", "Fondo", "Esperado",
                                      "Contado", "Diferencia", "Justificación"], registers, money={4, 5, 6, 7}),
            Section("Cobros del día", PAYMENT_HEADERS, _payment_rows(data["payments"]), money=PAYMENT_MONEY),
        ],
    )


def monthly_report(data: dict, cashier_label: str = "Todos los cajeros") -> Report:
    summary = data["summary"]
    registers = [
        [f"#{r['id']}", r["cashier_name"], r["opened_at"], r["closed_at"], float(r["initial_amount"]),
         float(r["expected_amount"]), float(r["physical_amount"]), float(r["difference"]),
         r.get("audit_explanation") or ""]
        for r in data["registers"]
    ]
    return Report(
        title=f"Cierre mensual {data['periodo']}",
        subtitle=cashier_label,
        summary=[
            ("Total cobrado en el mes", float(data["total_cobrado_mes"])),
            ("En efectivo", float(data["total_efectivo_mes"])),
            ("Cajas cerradas", int(data["cajas_cerradas"])),
            ("Efectivo esperado en cajas", float(data["total_esperado_cajas"])),
            ("Efectivo contado", float(data["total_efectivo_contado"])),
            ("Descuadres del mes", float(data["total_descuadres_mes"])),
            ("Comprobantes", int(summary["receipts"])),
            ("Anulado", float(summary["voided_total"])),
        ],
        sections=_breakdown_sections(summary) + [
            Section("Cobros por día", ["Fecha", "Total", "En efectivo"],
                    [[fmt_date(d["date"]), float(d["total"]), float(d["cash"])] for d in data["by_day"]],
                    money={1, 2}),
            Section("Cajas cerradas", ["Caja", "Cajero", "Apertura", "Cierre", "Fondo", "Esperado",
                                       "Contado", "Diferencia", "Justificación"], registers, money={4, 5, 6, 7}),
        ],
    )


# ------------------------------------------------------------------ acciones

def open_register_report(parent, register_id: int) -> None:
    data = api.get(f"/cashier/registers/{register_id}/report")
    show_report(parent, register_report(data), f"Cierre de caja {register_id}")


def open_daily_report(parent, day: str | None = None, cashier_id: int | None = None,
                      cashier_label: str = "Todos los cajeros") -> None:
    params = []
    if day:
        params.append(f"day={day}")
    if cashier_id:
        params.append(f"cashier_id={cashier_id}")
    data = api.get("/cashier/daily" + (f"?{'&'.join(params)}" if params else ""))
    show_report(parent, daily_report(data, cashier_label), f"Cierre diario {data['date']}")


def open_monthly_report(parent, year: int, month: int, cashier_id: int | None = None,
                        cashier_label: str = "Todos los cajeros") -> None:
    suffix = f"&cashier_id={cashier_id}" if cashier_id else ""
    data = api.get(f"/cashier/monthly?year={year}&month={month}{suffix}")
    show_report(parent, monthly_report(data, cashier_label), f"Cierre mensual {data['periodo']}")
