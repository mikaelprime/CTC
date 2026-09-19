from api_client import api
from widgets.crud_page import Column, CrudPage, Field


def _fetch():
    return api.get("/payments/")


def _enrollment_options():
    enrollments = api.get("/enrollments/") or []
    return [
        (f"#{e['id']} — {e['student']['full_name']} ({e['diploma']['name']})", e["id"])
        for e in enrollments
    ]


_STATUS_OPTIONS = [("Pendiente", "PENDIENTE"), ("Pagado", "PAGADO")]
_TYPE_OPTIONS = [("Efectivo", "Efectivo"), ("Tarjeta", "Tarjeta"), ("Transferencia", "Transferencia")]


def _create(payload: dict):
    amount = payload["amount"]
    surcharge = payload["surcharge"]
    body = {
        "enrollment_id": payload["enrollment_id"],
        "payment_date": payload["payment_date"],
        "due_date": payload["due_date"],
        "amount": amount,
        "surcharge": surcharge,
        "total": round(amount + surcharge, 2),
        "payment_type": payload["payment_type"],
        "status": payload["status"],
    }
    return api.post("/payments/", json=body)


def _delete(row: dict):
    return api.delete(f"/payments/{row['id']}")


class PaymentsPage(CrudPage):
    def __init__(self, parent=None):
        columns = [
            Column("id", "ID"),
            Column("enrollment_id", "Matrícula", formatter=lambda r: f"#{r['enrollment_id']}"),
            Column("total", "Total", formatter=lambda r: f"${float(r['total']):,.2f}"),
            Column("payment_type", "Método"),
            Column("due_date", "Vencimiento"),
            Column("status", "Estado"),
        ]
        create_spec = [
            Field("enrollment_id", "Matrícula", kind="combo", options=_enrollment_options),
            Field("payment_date", "Fecha de pago", kind="date"),
            Field("due_date", "Fecha de vencimiento", kind="date"),
            Field("amount", "Monto (USD)", kind="float", default=0.0, maximum=100_000),
            Field("surcharge", "Recargo (USD)", kind="float", default=0.0, maximum=10_000),
            Field("payment_type", "Método de pago", kind="combo", options=lambda: _TYPE_OPTIONS),
            Field("status", "Estado", kind="combo", options=lambda: _STATUS_OPTIONS),
        ]
        super().__init__(
            title="Gestión de Pagos",
            subtitle="Cobranza, conciliación y estado de cuotas",
            columns=columns,
            fetch_fn=_fetch,
            create_spec=create_spec,
            create_fn=_create,
            create_label="Registrar pago",
            delete_fn=_delete,
            empty_message="No hay pagos registrados todavía. Crea primero una inscripción.",
            parent=parent,
        )

# Lista de precios de CTC El Salvador 
PRICING_OPTIONS = {
    "matricula": {
        "Matrícula Regular": 20.00,
        "Promo-Matrícula (50% OFF)": 10.00,
        "Matrícula Gratis": 0.00
    },
    "colegiatura": {
        "Plan Grupal": 25.00,
        "Plan Privado": 55.00,
        "Plan On-line": 70.00
    },
    "recargo_mora": 3.00 # Recargo por pasarse de 28 días
}

def calculate_cash_change(total_to_pay: float, cash_received: float) -> dict:
    if cash_received < total_to_pay:
        return {
            "is_valid": False,
            "change": 0.0,
            "error": "El efectivo ingresado es menor al total a pagar."
        }
    
    change = cash_received - total_to_pay
    return {
        "is_valid": True,
        "change": round(change, 2),
        "error": None
    }