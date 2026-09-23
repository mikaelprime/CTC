"""Lo que solo el administrador puede hacer, y que la API lo haga cumplir
(no solo el menú del escritorio): anular pagos, catálogos, gestión de
cajeros y contraseñas."""

from datetime import date
from uuid import uuid4

import pytest

from tests.conftest import client
from tests.test_cashier import cashier_headers
from tests.test_payments import MONTHLY_FEE, auth_headers, create_enrollment


def login(email, password):
    return client.post("/auth/login", json={"email": email, "password": password})


def new_cashier(password="Caja2026"):
    email = f"cajero-{uuid4().hex[:8]}@ctc.edu.sv"
    response = client.post("/users/cashiers", headers=auth_headers(), json={
        "full_name": "Pedro Ramírez", "email": email, "password": password, "birth_date": "1990-06-01",
    })
    assert response.status_code == 201
    return response.json()["id"], email


@pytest.mark.parametrize(
    "method, path, body",
    [
        ("delete", "/payments/1", None),
        ("put", "/payments/1", {"status": "PAGADO"}),
        ("post", "/payments/1/void", {"reason": "Intento de cajero"}),
        ("post", "/diplomas/", {"name": "Programa Cajero", "duration_months": 6, "registration_fee": 20, "monthly_fee": 25}),
        ("delete", "/diplomas/1", None),
        ("post", "/schedules/", {"name": "Turno Cajero", "start_time": "08:00:00", "end_time": "10:00:00"}),
        ("delete", "/schedules/1", None),
        ("delete", "/students/1", None),
        ("delete", "/enrollments/1", None),
        ("get", "/reports/cashier-monthly?year=2026&month=1", None),
        ("patch", "/users/cashiers/1", {"is_active": False}),
    ],
)
def test_cashier_cannot_use_admin_endpoints(method, path, body):
    kwargs = {"headers": cashier_headers()}
    if body is not None:
        kwargs["json"] = body
    response = getattr(client, method)(path, **kwargs)
    assert response.status_code == 403


def test_voided_payment_stays_in_history_and_installment_is_owed_again():
    headers = auth_headers()
    enrollment = create_enrollment(headers, date.today())
    paid = client.post("/payments/collect", headers=headers, json={
        "enrollment_id": enrollment["id"], "payment_date": date.today().isoformat(), "cash_received": MONTHLY_FEE,
    }).json()
    payment_id = paid["payment_ids"][0]

    # Un pago cobrado no se borra...
    assert client.delete(f"/payments/{payment_id}", headers=headers).status_code == 409
    # ...se anula con motivo.
    voided = client.post(f"/payments/{payment_id}/void", headers=headers, json={"reason": "Error de digitación"})
    assert voided.status_code == 200
    assert voided.json()["status"] == "ANULADO"
    assert "Error de digitación" in voided.json()["observations"]
    assert client.post(f"/payments/{payment_id}/void", headers=headers, json={"reason": "Otra vez"}).status_code == 400

    # La cuota vuelve a deberse desde la fecha de inicio.
    info = client.get(f"/payments/next/{enrollment['id']}", headers=headers).json()
    assert info["due_date"] == date.today().isoformat()


def test_admin_can_deactivate_and_reactivate_cashier():
    cashier_id, email = new_cashier()
    assert login(email, "Caja2026").status_code == 200

    off = client.patch(f"/users/cashiers/{cashier_id}", headers=auth_headers(), json={"is_active": False})
    assert off.status_code == 200 and off.json()["is_active"] is False
    assert login(email, "Caja2026").status_code == 401

    on = client.patch(f"/users/cashiers/{cashier_id}", headers=auth_headers(), json={"is_active": True})
    assert on.json()["is_active"] is True
    assert login(email, "Caja2026").status_code == 200


def test_deactivated_cashier_token_stops_working_immediately():
    cashier_id, email = new_cashier()
    token = login(email, "Caja2026").json()["access_token"]
    client.patch(f"/users/cashiers/{cashier_id}", headers=auth_headers(), json={"is_active": False})
    assert client.get("/students/", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_admin_resets_cashier_password():
    cashier_id, email = new_cashier()
    weak = client.post(f"/users/cashiers/{cashier_id}/reset-password", headers=auth_headers(), json={"new_password": "123"})
    assert weak.status_code == 422
    ok = client.post(f"/users/cashiers/{cashier_id}/reset-password", headers=auth_headers(), json={"new_password": "Nueva2026"})
    assert ok.status_code == 200
    assert login(email, "Caja2026").status_code == 401
    assert login(email, "Nueva2026").status_code == 200


def test_user_changes_own_password():
    cashier_id, email = new_cashier()
    headers = {"Authorization": f"Bearer {login(email, 'Caja2026').json()['access_token']}"}
    wrong = client.post("/auth/change-password", headers=headers, json={"current_password": "otra123", "new_password": "Propia2026"})
    assert wrong.status_code == 400
    ok = client.post("/auth/change-password", headers=headers, json={"current_password": "Caja2026", "new_password": "Propia2026"})
    assert ok.status_code == 200
    assert login(email, "Propia2026").status_code == 200
