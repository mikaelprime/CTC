from tests.conftest import client

def test_get_students():
    response = client.get("/students/")

    assert response.status_code == 200

def test_get_student_by_id():
    response = client.get("/students/6")

    data = response.json()

    assert data["id"] == 6
    assert "full_name" in data
    assert "email" in data

    assert response.status_code == 200

def test_create_student():

    response = client.post(
        "/students/",
        json={
            "full_name": "Pytest Student",
            "birth_date": "2007-01-01",
            "email": "pyteststudent@ctc.edu.sv",
            "phone": "7777-7777",
            "address": "Santa Ana",
            "education_level": "Bachillerato",
            "guardian_name": "Padre Pytest",
            "guardian_dui": "01090300-8",
            "guardian_relationship": "Padre",
            "guardian_email": "padre@ctc.edu.sv",
            "guardian_whatsapp": "7777-8888",
            "observations": "Creado automáticamente"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert "id" in data
    assert data["full_name"] == "Pytest Student"
    assert data["email"] == "pyteststudent@ctc.edu.sv"

def test_student_not_found():
    response = client.get("/students/9999999999")

    assert response.status_code == 404

def test_create_student_invalid_email():

    response = client.post(
        "/students/",
        json={
            "full_name": "Error Test",
            "birth_date": "2007-01-01",
            "email": "correo-invalido",
            "phone": "7777-7777",
            "address": "Santa Ana",
            "education_level": "Bachillerato",
            "guardian_name": "Padre",
            "guardian_dui": "11111111-1",
            "guardian_relationship": "Padre",
            "guardian_email": "correo",
            "guardian_whatsapp": "7777-7777",
            "observations": ""
        }
    )

    assert response.status_code == 422