"""El sistema solo acepta datos reales: fechas posibles, nombres sin números,
teléfonos y DUI salvadoreños válidos. También cubre el ticket de matrícula
(efectivo/cambio), la anulación en vez del borrado y el cron de avisos."""

from datetime import date, timedelta
from uuid import uuid4

import pytest

from app.core import validators
from tests.conftest import VALID_DUI, client, student_payload
from tests.test_payments import auth_headers, create_enrollment


def cashier_payload(**overrides):
    payload = {
        "full_name": "Carla Méndez",
        "email": f"cajera-{uuid4().hex[:8]}@ctc.edu.sv",
        "password": "Caja2026",
        "birth_date": "1995-03-15",
    }
    payload.update(overrides)
    return payload


def post_student(**overrides):
    return client.post("/students/", headers=auth_headers(), json=student_payload(**overrides))


# ---------------------------------------------------------------- cajeros

@pytest.mark.parametrize(
    "birth_date",
    [
        date.today().isoformat(),                               # "nació hoy"
        (date.today() + timedelta(days=30)).isoformat(),        # futuro
        (date.today() - timedelta(days=365 * 15)).isoformat(),  # menor de edad
        "1900-01-01",                                           # 126 años
    ],
)
def test_cashier_with_impossible_birth_date_is_rejected(birth_date):
    response = client.post("/users/cashiers", headers=auth_headers(), json=cashier_payload(birth_date=birth_date))
    assert response.status_code == 422
    assert "fecha de nacimiento" in response.json()["detail"].lower()


@pytest.mark.parametrize(
    "overrides",
    [
        {"full_name": "C4rla 123"},
        {"full_name": "."},
        {"full_name": "Carla"},              # sin apellido
        {"password": "abcdefgh"},            # sin números
        {"password": "12345678"},            # sin letras
        {"email": "no-es-correo"},
    ],
)
def test_cashier_invalid_fields_are_rejected(overrides):
    response = client.post("/users/cashiers", headers=auth_headers(), json=cashier_payload(**overrides))
    assert response.status_code == 422


def test_valid_cashier_is_created():
    response = client.post("/users/cashiers", headers=auth_headers(), json=cashier_payload())
    assert response.status_code == 201


# ---------------------------------------------------------------- estudiantes

@pytest.mark.parametrize(
    "overrides",
    [
        {"contact_phone": "7777-abcd"},
        {"contact_phone": "."},
        {"contact_phone": "1234-5678"},       # no empieza con 2, 6 o 7
        {"contact_phone": "7777-777"},        # 7 dígitos
        {"full_name": "Juan 23"},
        {"full_name": "..."},
        {"address": "."},
        {"address": "12345"},                 # sin letras
        {"schooling": "xyz"},
        {"birth_date": date.today().isoformat()},
        {"birth_date": (date.today() + timedelta(days=1)).isoformat()},
        {"dui": "12345678-9"},                # dígito verificador incorrecto
        {"dui": "abc"},
        {"email": "sin-arroba"},
        {"age": 40},                          # no coincide con la fecha de nacimiento
    ],
)
def test_student_invalid_fields_are_rejected(overrides):
    response = post_student(**overrides)
    assert response.status_code == 422, response.json()
    # El mensaje llega en español y como texto, no como una lista técnica.
    assert isinstance(response.json()["detail"], str)


@pytest.mark.parametrize("field", ["full_name", "birth_date", "address", "email", "contact_phone", "schooling"])
def test_student_required_fields(field):
    payload = student_payload()
    payload.pop(field)
    response = client.post("/students/", headers=auth_headers(), json=payload)
    assert response.status_code == 422
    assert "obligatorio" in response.json()["detail"]


@pytest.mark.parametrize("field", ["address", "contact_phone", "schooling"])
def test_student_required_fields_cannot_be_blank(field):
    response = post_student(**{field: "   "})
    assert response.status_code == 422
    assert "obligatori" in response.json()["detail"]
    created = post_student().json()
    blank = client.put(f"/students/{created['id']}", headers=auth_headers(), json={field: ""})
    assert blank.status_code == 422


def test_student_phone_is_normalized_and_age_is_computed():
    birth = date.today().replace(year=date.today().year - 25) - timedelta(days=1)
    response = post_student(contact_phone="+503 7777 8888", birth_date=birth.isoformat(), dui=VALID_DUI.replace("-", ""))
    assert response.status_code == 200, response.json()
    data = response.json()
    assert data["contact_phone"] == "7777-8888"
    assert data["age"] == 25
    assert data["dui"] == VALID_DUI


def test_minor_student_requires_responsible_data():
    minor_birth = (date.today() - timedelta(days=365 * 15)).isoformat()
    missing = post_student(birth_date=minor_birth)
    assert missing.status_code == 422
    assert "menor de edad" in missing.json()["detail"]

    complete = post_student(
        birth_date=minor_birth,
        responsible_name="María López",
        responsible_dui=VALID_DUI,
        responsible_kinship="madre",
        responsible_whatsapp="+1 (213) 555-0199",  # responsable en el extranjero
    )
    assert complete.status_code == 200, complete.json()
    assert complete.json()["responsible_kinship"] == "Madre"
    assert complete.json()["responsible_whatsapp"] == "+12135550199"


def test_update_rejects_invalid_phone_and_keeps_old_value():
    created = post_student()
    student_id = created.json()["id"]
    bad = client.put(f"/students/{student_id}", headers=auth_headers(), json={"contact_phone": "77a7-8888"})
    assert bad.status_code == 422
    current = client.get(f"/students/{student_id}", headers=auth_headers()).json()
    assert current["contact_phone"] == "7777-8888"


def test_dui_checksum():
    assert validators.dui("00016297-5") == "00016297-5"
    with pytest.raises(ValueError):
        validators.dui("00016297-4")


# ---------------------------------------------------------------- matrículas, horarios y pagos

def _enrollment_ids(headers):
    student = post_student().json()
    diploma = client.post(
        "/diplomas/", headers=headers,
        json={"name": f"Diplomado Validación {uuid4().hex[:6]}", "duration_months": 6, "registration_fee": 20, "monthly_fee": 25},
    ).json()
    schedule = client.post(
        "/schedules/", headers=headers,
        json={"name": f"Turno Validación {uuid4().hex[:6]}", "start_time": "08:00:00", "end_time": "10:15:00"},
    ).json()
    return {"student_id": student["id"], "diploma_id": diploma["id"], "schedule_id": schedule["id"]}


@pytest.mark.parametrize(
    "dates",
    [
        {"enrollment_date": (date.today() + timedelta(days=1)).isoformat()},    # matrícula futura
        {"enrollment_date": (date.today() - timedelta(days=800)).isoformat()},  # demasiado antigua
        {"enrollment_date": date.today().isoformat(),
         "start_date": (date.today() + timedelta(days=500)).isoformat()},       # inicio absurdo
    ],
)
def test_enrollment_with_impossible_dates_is_rejected(dates):
    headers = auth_headers()
    response = client.post("/enrollments/", headers=headers, json={**_enrollment_ids(headers), **dates})
    assert response.status_code == 422


def test_schedule_end_must_be_after_start():
    response = client.post(
        "/schedules/", headers=auth_headers(),
        json={"name": "Turno al revés", "start_time": "10:00:00", "end_time": "08:00:00"},
    )
    assert response.status_code == 422


def test_payment_in_the_future_or_with_unknown_method_is_rejected():
    headers = auth_headers()
    enrollment = create_enrollment(headers, date.today())
    future = client.post("/payments/collect", headers=headers, json={
        "enrollment_id": enrollment["id"],
        "payment_date": (date.today() + timedelta(days=3)).isoformat(),
        "cash_received": 50,
    })
    assert future.status_code == 422
    unknown = client.post("/payments/collect", headers=headers, json={
        "enrollment_id": enrollment["id"],
        "payment_date": date.today().isoformat(),
        "payment_type": "Bitcoin",
        "cash_received": 50,
    })
    assert unknown.status_code == 422


def test_enrollment_returns_cash_and_change_for_the_ticket():
    headers = auth_headers()
    ids = _enrollment_ids(headers)
    response = client.post("/enrollments/", headers=headers, json={
        **ids, "enrollment_date": date.today().isoformat(), "cash_received": 50,
    })
    assert response.status_code == 200, response.json()
    data = response.json()
    assert float(data["registration_fee"]) == 20
    assert float(data["change"]) == 30

    short = client.post("/enrollments/", headers=headers, json={
        **_enrollment_ids(headers), "enrollment_date": date.today().isoformat(), "cash_received": 5,
    })
    assert short.status_code == 400


def test_duplicate_active_enrollment_is_rejected():
    headers = auth_headers()
    ids = _enrollment_ids(headers)
    body = {**ids, "enrollment_date": date.today().isoformat()}
    assert client.post("/enrollments/", headers=headers, json=body).status_code == 200
    assert client.post("/enrollments/", headers=headers, json=body).status_code == 409


def test_enrollment_with_payments_is_cancelled_not_deleted():
    headers = auth_headers()
    enrollment = create_enrollment(headers, date.today())  # cobra $20 de matrícula
    deleted = client.delete(f"/enrollments/{enrollment['id']}", headers=headers)
    assert deleted.status_code == 409

    cancelled = client.post(
        f"/enrollments/{enrollment['id']}/cancel", headers=headers, json={"reason": "Retiro voluntario del estudiante"}
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "ANULADA"

    payments = [p for p in client.get("/payments/", headers=headers).json() if p["enrollment_id"] == enrollment["id"]]
    assert payments and all(p["status"] == "PAGADO" for p in payments)

    blocked = client.post("/payments/collect", headers=headers, json={
        "enrollment_id": enrollment["id"], "payment_date": date.today().isoformat(), "cash_received": 50,
    })
    assert blocked.status_code == 400


def test_free_enrollment_without_payments_can_still_be_deleted():
    headers = auth_headers()
    response = client.post("/enrollments/", headers=headers, json={
        **_enrollment_ids(headers), "enrollment_date": date.today().isoformat(), "registration_type": "GRATIS",
    })
    assert response.status_code == 200
    assert client.delete(f"/enrollments/{response.json()['id']}", headers=headers).status_code == 200


# ---------------------------------------------------------------- cron de recordatorios

def test_cron_endpoint_requires_secret(monkeypatch):
    monkeypatch.delenv("CRON_SECRET", raising=False)
    assert client.post("/api/cron/reminders").status_code == 403

    monkeypatch.setenv("CRON_SECRET", "secreto-de-prueba")
    assert client.post("/api/cron/reminders", headers={"X-Cron-Secret": "otro"}).status_code == 403
    ok = client.post("/api/cron/reminders", headers={"X-Cron-Secret": "secreto-de-prueba"})
    assert ok.status_code == 200
    assert "reminders_sent" in ok.json()
