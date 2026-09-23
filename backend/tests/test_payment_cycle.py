"""Estado "PENDIENTE" tras 28 días sin cobro, reporte de cobros próximos,
cuotas PENDIENTE que el cobro debe saldar (no duplicar), pago adelantado cada
28 días y arqueo que solo compara el efectivo."""

import time
from datetime import date, timedelta

from tests.conftest import client
from tests.test_cashier import cashier_headers, ensure_register_closed
from tests.test_payments import MONTHLY_FEE, auth_headers, create_enrollment


def enrollment_status(headers, enrollment_id):
    response = client.get(f"/enrollments/{enrollment_id}", headers=headers)
    assert response.status_code == 200
    return response.json()


def test_enrollment_becomes_pending_when_cycle_passes_without_payment():
    headers = auth_headers()
    enrollment = create_enrollment(headers, date.today() - timedelta(days=30))

    data = enrollment_status(headers, enrollment["id"])
    assert data["status"] == "PENDIENTE"
    assert data["next_payment_date"] == (date.today() - timedelta(days=30)).isoformat()

    # Paga la cuota vencida y la siguiente: queda al día y vuelve a ACTIVA.
    collected = client.post(
        "/payments/collect",
        headers=headers,
        json={
            "enrollment_id": enrollment["id"],
            "payment_date": date.today().isoformat(),
            "cash_received": 100,
            "months": 2,
        },
    )
    assert collected.status_code == 200
    data = enrollment_status(headers, enrollment["id"])
    assert data["status"] == "ACTIVA"
    assert data["next_payment_date"] == (date.today() + timedelta(days=26)).isoformat()


def test_partial_payment_keeps_enrollment_pending():
    headers = auth_headers()
    enrollment = create_enrollment(headers, date.today() - timedelta(days=60))
    collected = client.post(
        "/payments/collect",
        headers=headers,
        json={
            "enrollment_id": enrollment["id"],
            "payment_date": date.today().isoformat(),
            "cash_received": 100,
        },
    )
    assert collected.status_code == 200
    # Debía dos ciclos y pagó uno: sigue atrasada.
    assert enrollment_status(headers, enrollment["id"])["status"] == "PENDIENTE"


def test_upcoming_payments_lists_enrollments_due_soon_and_overdue():
    headers = auth_headers()
    soon = create_enrollment(headers, date.today() + timedelta(days=3))
    far = create_enrollment(headers, date.today() + timedelta(days=20))
    overdue = create_enrollment(headers, date.today() - timedelta(days=5))

    response = client.get("/reports/upcoming-payments?days=7", headers=headers)
    assert response.status_code == 200
    by_id = {row["enrollment_id"]: row for row in response.json()}
    assert by_id[soon["id"]]["days_remaining"] == 3
    assert float(by_id[soon["id"]]["amount"]) == MONTHLY_FEE
    assert far["id"] not in by_id
    assert by_id[overdue["id"]]["is_overdue"] is True

    only_upcoming = client.get(
        "/reports/upcoming-payments?days=7&include_overdue=false", headers=headers
    ).json()
    assert overdue["id"] not in {row["enrollment_id"] for row in only_upcoming}


def test_collect_settles_existing_pending_installment_instead_of_duplicating():
    headers = auth_headers()
    start = date.today()
    enrollment = create_enrollment(headers, start)
    manual = client.post(
        "/payments/",
        headers=headers,
        json={
            "enrollment_id": enrollment["id"],
            "payment_date": start.isoformat(),
            "due_date": start.isoformat(),
            "amount": MONTHLY_FEE,
            "total": MONTHLY_FEE,
            "payment_type": "Efectivo",
            "status": "PENDIENTE",
        },
    )
    assert manual.status_code == 200

    collected = client.post(
        "/payments/collect",
        headers=headers,
        json={"enrollment_id": enrollment["id"], "payment_date": start.isoformat(), "cash_received": 30},
    )
    assert collected.status_code == 200
    assert collected.json()["payment_ids"] == [manual.json()["id"]]

    payments = [
        p for p in client.get("/payments/", headers=headers).json()
        if p["enrollment_id"] == enrollment["id"] and p["kind"] == "COLEGIATURA"
    ]
    assert len(payments) == 1
    assert payments[0]["status"] == "PAGADO"


def test_advance_payment_uses_28_day_cycle_and_marks_all_paid():
    headers = auth_headers()
    start = date.today()
    enrollment = create_enrollment(headers, start)
    response = client.post(
        "/payments/advance",
        headers=headers,
        json={
            "enrollment_id": enrollment["id"],
            "months": 3,
            "payment_date": start.isoformat(),
            "payment_type": "Efectivo",
            "cash_received": MONTHLY_FEE * 3,
        },
    )
    assert response.status_code == 200
    payments = response.json()
    assert [p["due_date"] for p in payments] == [
        (start + timedelta(days=28 * i)).isoformat() for i in range(3)
    ]
    assert all(p["status"] == "PAGADO" for p in payments)


def test_register_close_compares_only_cash_against_drawer():
    headers = cashier_headers()
    ensure_register_closed(headers)
    assert client.post("/cashier/register/open", headers=headers, json={"initial_amount": 10}).status_code == 200
    # SQLite guarda las marcas de tiempo al segundo: sin esta pausa el cobro
    # puede compararse como "anterior" a la apertura de caja en el mismo segundo.
    time.sleep(1.1)

    enrollment = create_enrollment(auth_headers(), date.today())
    paid = client.post(
        "/payments/collect",
        headers=headers,
        json={
            "enrollment_id": enrollment["id"],
            "payment_date": date.today().isoformat(),
            "payment_type": "Tarjeta",
            "cash_received": MONTHLY_FEE,
        },
    )
    assert paid.status_code == 200

    current = client.get("/cashier/register/current", headers=headers).json()
    assert current["collected_amount"] == MONTHLY_FEE
    assert current["expected_amount"] == 10

    closed = client.post("/cashier/register/close", headers=headers, json={"physical_amount": 10})
    assert closed.status_code == 200
    assert closed.json()["diferencia"] == 0
    assert closed.json()["cobrado_otros_metodos"] == MONTHLY_FEE


def test_cashier_cannot_charge_registration_fee_without_open_register():
    admin = auth_headers()
    headers = cashier_headers()
    ensure_register_closed(headers)
    base = create_enrollment(admin, date.today())
    response = client.post(
        "/enrollments/",
        headers=headers,
        json={
            "student_id": base["student_id"],
            "diploma_id": base["diploma_id"],
            "schedule_id": base["schedule_id"],
            "enrollment_date": date.today().isoformat(),
            "registration_type": "COMPLETA",
        },
    )
    assert response.status_code == 403


def test_config_rejects_zero_day_cycle():
    headers = auth_headers()
    response = client.put(
        "/config/",
        headers=headers,
        json={"institution_name": "CTC El Salvador", "late_fee": 3, "payment_cycle_days": 0, "alert_days_before": 7},
    )
    assert response.status_code == 422
