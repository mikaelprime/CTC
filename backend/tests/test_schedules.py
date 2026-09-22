from uuid import uuid4

from tests.conftest import client


def auth_headers():
    response = client.post(
        "/auth/login",
        json={"email": "admin@ctc.edu.sv", "password": "123456"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_schedules_require_auth():
    response = client.get("/schedules/")

    assert response.status_code == 401


def test_create_and_list_schedule():
    payload = {
        "name": f"Turno Pytest {uuid4().hex[:8]}",
        "start_time": "08:00:00",
        "end_time": "12:00:00",
    }
    created = client.post("/schedules/", headers=auth_headers(), json=payload)

    assert created.status_code == 200
    data = created.json()
    assert data["name"] == payload["name"]
    assert data["start_time"] == "08:00:00"

    response = client.get("/schedules/", headers=auth_headers())

    assert response.status_code == 200
    assert any(item["id"] == data["id"] for item in response.json())
