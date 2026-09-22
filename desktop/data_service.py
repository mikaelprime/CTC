"""Aggregation logic for the dashboard, backed by the real FastAPI endpoints."""

from datetime import date, datetime

from api_client import api

MESES_ES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def _parse_date(value) -> date:
    if isinstance(value, date):
        return value
    return datetime.strptime(value, "%Y-%m-%d").date()


def get_students() -> list[dict]:
    return api.get("/students/") or []


def get_payments() -> list[dict]:
    return api.get("/payments/") or []


def get_enrollments() -> list[dict]:
    return api.get("/enrollments/") or []


def get_diplomas() -> list[dict]:
    return api.get("/diplomas/") or []


def get_schedules() -> list[dict]:
    return api.get("/schedules/") or []


def load_dashboard_data() -> dict:
    """Trae todo lo que necesita el panel en una sola ronda de peticiones.

    Antes cada función de abajo (kpis, ingresos, distribución, actividad)
    volvía a pedir /payments/ y /enrollments/ por su cuenta: un reload del
    panel disparaba la misma petición 3 veces. Ahora se trae una vez y se
    reparte, además de correr en un hilo aparte para no congelar la ventana.
    """
    return {
        "students": get_students(),
        "payments": get_payments(),
        "enrollments": get_enrollments(),
    }


def kpis_generales(data: dict) -> dict:
    students = data["students"]
    payments = data["payments"]
    enrollments = data["enrollments"]

    today = date.today()

    # El modelo de estudiante no tiene un campo is_active (no hay baja lógica,
    # solo eliminación), así que todo estudiante devuelto por la API cuenta
    # como activo.
    estudiantes_activos = len(students)

    inscripciones_mes = sum(
        1
        for e in enrollments
        if _parse_date(e["enrollment_date"]).year == today.year
        and _parse_date(e["enrollment_date"]).month == today.month
    )

    pendientes = [p for p in payments if p["status"] == "PENDIENTE"]
    pagos_pendientes = sum(float(p["total"]) for p in pendientes)
    vencidos = [p for p in pendientes if _parse_date(p["due_date"]) < today]

    matriculas_criticas = sum(
        1
        for e in enrollments
        if e.get("status") == "ACTIVA"
        and 0 <= (_parse_date(e["end_date"]) - today).days <= 2
    )

    return {
        "estudiantes_activos": estudiantes_activos,
        "inscripciones_mes": inscripciones_mes,
        "pagos_pendientes": round(pagos_pendientes, 2),
        "cuotas_por_auditar": len(pendientes),
        "vencimientos": len(vencidos),
        "matriculas_criticas": matriculas_criticas,
    }


def ingresos_mensuales(data: dict, count: int = 6) -> dict:
    payments = data["payments"]

    today = date.today()
    months: list[tuple[int, int]] = []
    y, m = today.year, today.month
    for _ in range(count):
        months.append((y, m))
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    months.reverse()

    cobrado = dict.fromkeys(months, 0.0)
    proyectado = dict.fromkeys(months, 0.0)

    for p in payments:
        due_key = (_parse_date(p["due_date"]).year, _parse_date(p["due_date"]).month)
        if due_key in proyectado:
            proyectado[due_key] += float(p["total"])

        if p["status"] == "PAGADO":
            paid_key = (_parse_date(p["payment_date"]).year, _parse_date(p["payment_date"]).month)
            if paid_key in cobrado:
                cobrado[paid_key] += float(p["total"])

    return {
        "meses": [MESES_ES[m - 1] for _, m in months],
        "cobrado": [round(cobrado[key], 2) for key in months],
        "proyectado": [round(proyectado[key], 2) for key in months],
    }


def distribucion_academica(data: dict) -> dict:
    enrollments = data["enrollments"]

    counts: dict[str, int] = {}
    for e in enrollments:
        name = e["diploma"]["name"]
        counts[name] = counts.get(name, 0) + 1

    return {"programas": list(counts.keys()), "estudiantes": list(counts.values())}


def actividad_reciente(data: dict, limit: int = 8) -> list[dict]:
    payments = data["payments"]
    enrollments_by_id = {e["id"]: e for e in data["enrollments"]}

    today = date.today()
    recientes = sorted(payments, key=lambda p: p["payment_date"], reverse=True)[:limit]

    rows = []
    for p in recientes:
        enrollment = enrollments_by_id.get(p["enrollment_id"])
        if p["status"] == "PAGADO":
            estado, kind = "Pagado", "success"
        elif _parse_date(p["due_date"]) < today:
            estado, kind = "Vencido", "error"
        else:
            estado, kind = "Pendiente", "warning"

        rows.append(
            {
                "tipo": p["payment_type"] or "Pago de Cuota",
                "estudiante": enrollment["student"]["full_name"] if enrollment else "—",
                "id": f"PAG-{p['id']:04d}",
                "programa": enrollment["diploma"]["name"] if enrollment else "—",
                "monto": float(p["total"]),
                "fecha": p["payment_date"],
                "estado": estado,
                "estado_kind": kind,
            }
        )

    return rows
