from uuid import uuid4

from tests.conftest import client


def auth_headers():
    response = client.post(
        "/auth/login",
        json={"email": "admin@ctc.edu.sv", "password": "123456"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}

def test_get_students():
    response = client.get("/students/", headers=auth_headers())

    assert response.status_code == 200

def test_get_student_by_id():
    email = f"lookup-{uuid4().hex[:8]}@ctc.edu.sv"
    created = client.post(
        "/students/",
        headers=auth_headers(),
        json={"full_name": "Lookup Student", "email": email},
    )
    assert created.status_code == 200
    response = client.get(
        f"/students/{created.json()['id']}",
        headers=auth_headers(),
    )

    data = response.json()

    assert data["id"] == created.json()["id"]
    assert "full_name" in data
    assert "email" in data

    assert response.status_code == 200

def test_create_student():
    email = f"pyteststudent-{uuid4().hex[:8]}@ctc.edu.sv"

    response = client.post(
        "/students/",
        headers=auth_headers(),
        json={
            "full_name": "Pytest Student",
            "birth_date": "2007-01-01",
            "email": email,
            "contact_phone": "7777-7777",
            "address": "Santa Ana",
            "schooling": "Bachillerato",
            "responsible_name": "Padre Pytest",
            "responsible_dui": "01090300-8",
            "responsible_kinship": "Padre",
            "responsible_email": "padre@ctc.edu.sv",
            "responsible_whatsapp": "7777-8888",
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert "id" in data
    assert data["full_name"] == "Pytest Student"
    assert data["email"] == email
    # Los datos del responsable deben persistir tal cual se enviaron,
    # no descartarse silenciosamente por un esquema desalineado.
    assert data["contact_phone"] == "7777-7777"
    assert data["responsible_name"] == "Padre Pytest"
    assert data["responsible_dui"] == "01090300-8"

def test_student_not_found():
    response = client.get("/students/9999999999", headers=auth_headers())

    assert response.status_code == 404

def test_create_student_invalid_email():

    response = client.post(
        "/students/",
        headers=auth_headers(),
        json={
            "full_name": "Error Test",
            "birth_date": "2007-01-01",
            "email": "correo-invalido",
            "contact_phone": "7777-7777",
            "address": "Santa Ana",
            "schooling": "Bachillerato",
            "responsible_name": "Padre",
            "responsible_dui": "11111111-1",
            "responsible_kinship": "Padre",
            "responsible_email": "correo",
            "responsible_whatsapp": "7777-7777",
        }
    )

    assert response.status_code == 422

def test_students_requires_auth():
    response = client.get("/students/")

    assert response.status_code == 401
