from uuid import uuid4

from tests.conftest import client


def auth_headers():
    response = client.post(
        "/auth/login",
        json={"email": "admin@ctc.edu.sv", "password": "123456"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_diploma(**overrides):
    payload = {
        "name": f"Diplomado Pytest {uuid4().hex[:8]}",
        "description": "Creado por pruebas automatizadas",
        "duration_months": 6,
        "registration_fee": 25,
        "monthly_fee": 40,
        "active": True,
    }
    payload.update(overrides)
    return client.post("/diplomas/", headers=auth_headers(), json=payload)


def test_diplomas_require_auth():
    response = client.get("/diplomas/")

    assert response.status_code == 401


def test_create_and_get_diploma():
    created = create_diploma()

    assert created.status_code == 200
    data = created.json()
    assert data["duration_months"] == 6
    assert data["monthly_fee"] == 40

    response = client.get(f"/diplomas/{data['id']}", headers=auth_headers())

    assert response.status_code == 200
    assert response.json()["name"] == data["name"]


def test_diploma_not_found():
    response = client.get("/diplomas/9999999999", headers=auth_headers())

    assert response.status_code == 404


def test_update_diploma():
    created = create_diploma().json()

    response = client.put(
        f"/diplomas/{created['id']}",
        headers=auth_headers(),
        json={"monthly_fee": 55},
    )

    assert response.status_code == 200
    assert response.json()["monthly_fee"] == 55
