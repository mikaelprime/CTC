from uuid import uuid4

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


def test_login_locks_out_after_repeated_failures():
    """Tras varios intentos fallidos seguidos con el mismo correo, el login
    se bloquea temporalmente (429) aunque después se manden las credenciales
    correctas: evita fuerza bruta ilimitada sobre /auth/login."""
    email = f"bruteforce-{uuid4().hex[:8]}@ctc.edu.sv"

    for _ in range(5):
        response = client.post(
            "/auth/login",
            json={"email": email, "password": "incorrecta"},
        )
        assert response.status_code == 401

    blocked = client.post(
        "/auth/login",
        json={"email": email, "password": "incorrecta"},
    )
    assert blocked.status_code == 429

    # Ni siquiera con la contraseña correcta debería pasar mientras dure el bloqueo.
    still_blocked = client.post(
        "/auth/login",
        json={"email": email, "password": "123456"},
    )
    assert still_blocked.status_code == 429