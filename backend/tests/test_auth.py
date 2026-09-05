from tests.conftest import client

def test_login_endpoint_exists():
    response = client.post(
        "/auth/login",
        json={
            "email": "admin@ctc.edu.sv",
            "password": "123456"
        }
    )

    assert response.status_code != 404

def test_login_invalid_credentials():
    response = client.post(
        "/auth/login",
        json={
            "email": "correo@inexistente.com",
            "password": "123456"
        }
    )

    assert response.status_code == 401

def test_login_success():
    response = client.post(
        "/auth/login",
        json={
            "email": "admin@ctc.edu.sv",
            "password": "123456"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert "token_type" in data

    assert data["token_type"] == "bearer"