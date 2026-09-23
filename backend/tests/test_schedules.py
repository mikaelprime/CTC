from uuid import uuid4

from tests.conftest import client, student_payload


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


def create_schedule(**overrides):
    payload = {
        "name": f"Turno Pytest {uuid4().hex[:8]}",
        "start_time": "08:00:00",
        "end_time": "12:00:00",
    }
    payload.update(overrides)
    return client.post("/schedules/", headers=auth_headers(), json=payload)


def test_create_and_list_schedule():
    created = create_schedule()

    assert created.status_code == 200
    data = created.json()
    assert data["start_time"] == "08:00:00"

    response = client.get("/schedules/", headers=auth_headers())

    assert response.status_code == 200
    assert any(item["id"] == data["id"] for item in response.json())


def test_update_schedule():
    created = create_schedule().json()

    response = client.put(
        f"/schedules/{created['id']}",
        headers=auth_headers(),
        json={"end_time": "13:30:00", "active": False},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["end_time"] == "13:30:00"
    assert data["active"] is False


def test_update_schedule_not_found():
    response = client.put(
        "/schedules/9999999999",
        headers=auth_headers(),
        json={"active": False},
    )

    assert response.status_code == 404


def test_delete_schedule():
    created = create_schedule().json()

    response = client.delete(f"/schedules/{created['id']}", headers=auth_headers())

    assert response.status_code == 200


def test_deleting_schedule_with_enrollments_is_rejected_not_a_500():
    """Antes de este fix, `Schedule.enrollments` tenía cascade="all,
    delete-orphan": borrar un turno arrastraba en silencio las inscripciones
    (y sus pagos) de los estudiantes que lo cursan, igual que pasaba con
    Diploma antes de corregirse. Debe rechazarse con un mensaje claro."""
    headers = auth_headers()
    schedule = create_schedule().json()

    student = client.post(
        "/students/",
        headers=headers,
        json=student_payload(full_name="Estudiante Turno", email=f"turno-{uuid4().hex[:8]}@ctc.edu.sv"),
    )
    assert student.status_code == 200

    diploma = client.post(
        "/diplomas/",
        headers=headers,
        json={
            "name": f"Diplomado Turno {uuid4().hex[:8]}",
            "duration_months": 6,
            "registration_fee": 25,
            "monthly_fee": 40,
        },
    )
    assert diploma.status_code == 200

    from datetime import date

    enrollment = client.post(
        "/enrollments/",
        headers=headers,
        json={
            "student_id": student.json()["id"],
            "diploma_id": diploma.json()["id"],
            "schedule_id": schedule["id"],
            "enrollment_date": date.today().isoformat(),
        },
    )
    assert enrollment.status_code == 200

    response = client.delete(f"/schedules/{schedule['id']}", headers=headers)
    assert response.status_code == 409

    still_there = client.get("/schedules/", headers=headers)
    assert any(item["id"] == schedule["id"] for item in still_there.json())

    enrollment_still_there = client.get(f"/enrollments/{enrollment.json()['id']}", headers=headers)
    assert enrollment_still_there.status_code == 200
