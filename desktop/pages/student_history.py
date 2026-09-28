"""Estado de cuenta de un estudiante: sus inscripciones con cuotas pagadas,
vencidas y saldo por pagar del diplomado, y cada cobro (incluidos los
anulados), con totales y exportación a Excel/PDF para entregarlo."""

from widgets.receipt_view import fmt_date
from widgets.report_dialog import ReportDialog
from widgets.report_export import Report, Section

from api_client import api

_KIND = {"MATRICULA": "Matrícula", "COLEGIATURA": "Colegiatura"}
_PLAN = {"GRUPAL": "Grupal", "PRIVADO": "Privado", "ONLINE": "On-line"}

ENROLLMENT_HEADERS = [
    "#", "Programa", "Horario", "Plan", "Inicio", "Estado", "Cuotas pagadas",
    "Cuotas vencidas", "Saldo vencido", "Saldo por pagar", "Próximo pago",
]
ENROLLMENT_MONEY_COLUMNS = {8, 9}
PAYMENT_HEADERS = [
    "Comprobante", "Programa", "Concepto", "Fecha de pago", "Cuota del", "Monto", "Recargo",
    "Total", "Método", "Estado", "Atendió", "Observaciones",
]
PAYMENT_MONEY_COLUMNS = {5, 6, 7}


def enrollment_rows(data: dict) -> list[list]:
    rows = []
    for e in data["enrollments"]:
        next_payment = fmt_date(e.get("next_payment_date")) if e.get("next_payment_date") else "—"
        if e.get("is_overdue"):
            next_payment = f"{next_payment} (atrasado)"
        installments = (
            f"{e['installments_paid']} de {e['installments_total']}" if "installments_total" in e else "—"
        )
        rows.append([
            e["id"], e["diploma_name"], e["schedule_name"], _PLAN.get(e["tuition_plan"], e["tuition_plan"]),
            fmt_date(e["start_date"]), e["status"], installments, e.get("overdue_installments", 0),
            float(e.get("amount_overdue", 0)), float(e.get("remaining_balance", 0)), next_payment,
        ])
    return rows


def payment_rows(data: dict) -> list[list]:
    return [
        [
            p.get("receipt_number") or f"PAGO-{p['id']:06d}", p["diploma_name"], _KIND.get(p["kind"], p["kind"]),
            fmt_date(p["payment_date"]), fmt_date(p["due_date"]), p["amount"], p["surcharge"], p["total"],
            p["payment_type"], p["status"], p.get("cashier_name") or "—", p.get("observations") or "",
        ]
        for p in data["payments"]
    ]


def summary(data: dict) -> list[tuple[str, object]]:
    t = data["totals"]
    return [
        ("Total pagado", float(t["paid"])),
        ("Matrículas", float(t["registration"])),
        ("Colegiaturas", float(t["tuition"])),
        ("Recargos por mora", float(t["surcharges"])),
        ("Saldo vencido (con recargo)", float(t.get("amount_overdue", 0))),
        ("Saldo por pagar del diplomado", float(t.get("remaining_balance", 0))),
        ("Cuotas de colegiatura pagadas", int(t["tuition_installments_paid"])),
        ("Inscripciones atrasadas", int(t["overdue_enrollments"])),
        ("Pagos anulados", float(t["voided"])),
    ]


def build_report(data: dict) -> Report:
    student = data["student"]
    contact = " · ".join(filter(None, [
        student.get("email"), student.get("contact_phone"),
        f"Responsable: {student['responsible_name']}" if student.get("responsible_name") else None,
        f"Generado: {data['generated_at']}" if data.get("generated_at") else None,
    ]))
    return Report(
        title=f"Estado de cuenta — {student['full_name']}",
        subtitle=contact,
        summary=summary(data),
        sections=[
            Section("Inscripciones", ENROLLMENT_HEADERS, enrollment_rows(data), money=ENROLLMENT_MONEY_COLUMNS),
            Section("Pagos", PAYMENT_HEADERS, payment_rows(data), money=PAYMENT_MONEY_COLUMNS),
        ],
    )


class StudentHistoryDialog(ReportDialog):
    def __init__(self, student_id: int, parent=None):
        self.data = api.get(f"/reports/student-history/{student_id}")
        super().__init__(build_report(self.data), f"Estado de cuenta {self.data['student']['full_name']}", parent)
