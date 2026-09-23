"""Historial de pagos por estudiante y edición de inscripciones."""

from datetime import date, timedelta
from uuid import uuid4

from tests.conftest import client
from tests.test_cashier import cashier_headers
from tests.test_payments import MONTHLY_FEE, auth_headers, create_enrollment


def collect(headers, enrollment_id, months=1, cash=100):
    response = client.post("/payments/collect", headers=headers, json={
        "enrollment_id": enrollment_id, "payment_date": date.today().isoformat(),
        "cash_received": cash, "months": months,
    })
    assert response.status_code == 200, response.json()
    return response.json()


def new_schedule(headers):
    response = client.post("/schedules/", headers=headers, json={
        "name": f"Turno Edición {uuid4().hex[:6]}", "start_time": "13:00:00", "end_time": "15:15:00",
    })
    assert response.status_code == 200
    return response.json()["id"]


# ---------------------------------------------------------------- historial

def test_student_history_lists_payments_and_totals():
    headers = auth_headers()
    enrollment = create_enrollment(headers, date.today())
    paid = collect(headers, enrollment["id"], months=2)
    client.post(f"/payments/{paid['payment_ids'][1]}/void", headers=headers, json={"reason": "Cobro duplicado"})

    response = client.get(f"/reports/student-history/{enrollment['student_id']}", headers=cashier_headers())
    assert response.status_code == 200
    data = response.json()

    kinds = [(p["kind"], p["status"]) for p in data["payments"]]
    assert kinds == [("MATRICULA", "PAGADO"), ("COLEGIATURA", "PAGADO"), ("COLEGIATURA", "ANULADO")]
    # Quién registró el cobro (la matrícula la cobró el admin al inscribir).
    assert data["payments"][0]["cashier_name"]
    totals = data["totals"]
    assert totals["registration"] == 20
    assert totals["tuition"] == MONTHLY_FEE
    assert totals["paid"] == 20 + MONTHLY_FEE
    assert totals["voided"] == MONTHLY_FEE
    assert totals["tuition_installments_paid"] == 1
    assert data["enrollments"][0]["next_payment_date"] == (date.today() + timedelta(days=28)).isoformat()


def test_student_history_unknown_student_is_404():
    assert client.get("/reports/student-history/999999", headers=auth_headers()).status_code == 404


# ---------------------------------------------------------------- editar inscripción

def test_admin_changes_schedule_plan_and_observations():
    headers = auth_headers()
    enrollment = create_enrollment(headers, date.today())
    schedule_id = new_schedule(headers)
    response = client.put(f"/enrollments/{enrollment['id']}", headers=headers, json={
        "schedule_id": schedule_id, "tuition_plan": "PRIVADO", "observations": "Pasa a turno de la tarde",
    })
    assert response.status_code == 200, response.json()
    data = response.json()
    assert data["schedule"]["id"] == schedule_id
    assert data["tuition_plan"] == "PRIVADO"
    assert data["observations"] == "Pasa a turno de la tarde"
    # El nuevo plan se cobra desde la siguiente cuota.
    info = client.get(f"/payments/next/{enrollment['id']}", headers=headers).json()
    assert float(info["monthly_amount"]) == 55


def test_start_date_can_move_until_first_tuition_is_paid():
    headers = auth_headers()
    enrollment = create_enrollment(headers, date.today())
    new_start = date.today() + timedelta(days=14)
    moved = client.put(f"/enrollments/{enrollment['id']}", headers=headers, json={"start_date": new_start.isoformat()})
    assert moved.status_code == 200
    assert moved.json()["start_date"] == new_start.isoformat()
    assert moved.json()["next_payment_date"] == new_start.isoformat()
    assert moved.json()["end_date"] > moved.json()["start_date"]

    collect(headers, enrollment["id"])
    locked = client.put(f"/enrollments/{enrollment['id']}", headers=headers, json={
        "start_date": (date.today() + timedelta(days=20)).isoformat(),
    })
    assert locked.status_code == 409


def test_edit_rejects_invalid_values_and_cancelled_enrollments():
    headers = auth_headers()
    enrollment = create_enrollment(headers, date.today())
    url = f"/enrollments/{enrollment['id']}"
    assert client.put(url, headers=headers, json={"tuition_plan": "VIP"}).status_code == 400
    assert client.put(url, headers=headers, json={"schedule_id": 999999}).status_code == 404
    assert client.put(url, headers=headers, json={
        "start_date": (date.today() + timedelta(days=400)).isoformat(),
    }).status_code == 422
    assert client.put(url, headers=cashier_headers(), json={"observations": "Hola"}).status_code == 403

    client.post(f"{url}/cancel", headers=headers, json={"reason": "Retiro del estudiante"})
    assert client.put(url, headers=headers, json={"observations": "Cambio"}).status_code == 400
