from uuid import uuid4

from tests.conftest import client, student_payload


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


def test_deleting_diploma_with_enrollments_is_rejected_not_a_500():
    """Regresión: borrar un diplomado con estudiantes inscritos llegó a
    devolver un 500 sin explicación y a veces arrastraba en cascada las
    inscripciones y pagos de esos estudiantes. Debe rechazarse con un
    mensaje claro, y el diplomado debe seguir existiendo."""
    headers = auth_headers()
    diploma = create_diploma().json()

    student = client.post(
        "/students/",
        headers=headers,
        json=student_payload(full_name="Estudiante Dependencia", email=f"dep-{uuid4().hex[:8]}@ctc.edu.sv"),
    )
    assert student.status_code == 200

    schedule = client.post(
        "/schedules/",
        headers=headers,
        json={"name": f"Turno Dependencia {uuid4().hex[:8]}", "start_time": "08:00:00", "end_time": "10:00:00"},
    )
    assert schedule.status_code == 200

    from datetime import date

    enrollment = client.post(
        "/enrollments/",
        headers=headers,
        json={
            "student_id": student.json()["id"],
            "diploma_id": diploma["id"],
            "schedule_id": schedule.json()["id"],
            "enrollment_date": date.today().isoformat(),
        },
    )
    assert enrollment.status_code == 200

    response = client.delete(f"/diplomas/{diploma['id']}", headers=headers)
    assert response.status_code == 409

    still_there = client.get(f"/diplomas/{diploma['id']}", headers=headers)
    assert still_there.status_code == 200
