from tests.conftest import client


def cashier_headers():
    response = client.post(
        "/auth/login",
        json={"email": "cajero@ctc.edu.sv", "password": "123456"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def ensure_register_closed(headers):
    current = client.get("/cashier/register/current", headers=headers)
    if current.status_code == 200:
        client.post(
            "/cashier/register/close",
            headers=headers,
            json={"physical_amount": current.json()["expected_amount"]},
        )


def test_payments_blocked_without_open_register():
    headers = cashier_headers()
    ensure_register_closed(headers)

    response = client.get("/cashier/register/current", headers=headers)
    assert response.status_code == 403


def test_open_close_register_cycle():
    headers = cashier_headers()
    ensure_register_closed(headers)

    opened = client.post(
        "/cashier/register/open", headers=headers, json={"initial_amount": 50}
    )
    assert opened.status_code == 200

    duplicate = client.post(
        "/cashier/register/open", headers=headers, json={"initial_amount": 20}
    )
    assert duplicate.status_code == 400

    current = client.get("/cashier/register/current", headers=headers)
    assert current.status_code == 200
    assert current.json()["initial_amount"] == 50

    closed = client.post(
        "/cashier/register/close",
        headers=headers,
        json={"physical_amount": 50},
    )
    assert closed.status_code == 200
    assert closed.json()["diferencia"] == 0


def test_close_register_requires_explanation_on_mismatch():
    headers = cashier_headers()
    ensure_register_closed(headers)

    client.post("/cashier/register/open", headers=headers, json={"initial_amount": 100})

    mismatched = client.post(
        "/cashier/register/close",
        headers=headers,
        json={"physical_amount": 90},
    )
    assert mismatched.status_code == 400

    resolved = client.post(
        "/cashier/register/close",
        headers=headers,
        json={"physical_amount": 90, "explanation": "Faltante por vuelto entregado de más"},
    )
    assert resolved.status_code == 200
    assert resolved.json()["diferencia"] == -10


def test_cashier_routes_require_auth():
    response = client.get("/cashier/register/current")

    assert response.status_code == 401
