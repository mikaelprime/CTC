from uuid import uuid4

from tests.conftest import client


def admin_headers():
    response = client.post(
        "/auth/login",
        json={"email": "admin@ctc.edu.sv", "password": "123456"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def cashier_headers():
    response = client.post(
        "/auth/login",
        json={"email": "cajero@ctc.edu.sv", "password": "123456"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_create_cashier_requires_admin():
    response = client.post(
        "/users/cashiers",
        headers=cashier_headers(),
        json={
            "full_name": "Intento no autorizado",
            "email": f"noauth-{uuid4().hex[:8]}@ctc.edu.sv",
            "password": "123456",
            "birth_date": "1999-01-01",
        },
    )

    assert response.status_code == 403


def test_list_cashiers_never_exposes_password_hash():
    headers = admin_headers()
    created = client.post(
        "/users/cashiers",
        headers=headers,
        json={
            "full_name": "Cajero Pytest",
            "email": f"cajero-{uuid4().hex[:8]}@ctc.edu.sv",
            "password": "123456",
            "birth_date": "1999-01-01",
        },
    )
    assert created.status_code == 201
    assert "password" not in created.json()

    listed = client.get("/users/cashiers", headers=headers)
    assert listed.status_code == 200
    assert all("password" not in row for row in listed.json())
