from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from tests.conftest import client

DEFAULT_CONFIG = {
    "institution_name": "CTC El Salvador",
    "late_fee": 3.00,
    "payment_cycle_days": 28,
    "alert_days_before": 7,
}


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


def create_enrollment(headers, start_date: date, monthly_fee: int = 40):
    student = client.post(
        "/students/",
        headers=headers,
        json={"full_name": "Estudiante Config", "email": f"config-{uuid4().hex[:8]}@ctc.edu.sv"},
    )
    diploma = client.post(
        "/diplomas/",
        headers=headers,
        json={
            "name": f"Diplomado Config {uuid4().hex[:8]}",
            "duration_months": 6,
            "registration_fee": 25,
            "monthly_fee": monthly_fee,
        },
    )
    schedule = client.post(
        "/schedules/",
        headers=headers,
        json={"name": f"Turno Config {uuid4().hex[:8]}", "start_time": "08:00:00", "end_time": "10:00:00"},
    )
    enrollment = client.post(
        "/enrollments/",
        headers=headers,
        json={
            "student_id": student.json()["id"],
            "diploma_id": diploma.json()["id"],
            "schedule_id": schedule.json()["id"],
            "enrollment_date": start_date.isoformat(),
            "start_date": start_date.isoformat(),
        },
    )
    assert enrollment.status_code == 200
    return enrollment.json()


def test_config_requires_admin_to_update():
    response = client.put("/config/", headers=cashier_headers(), json=DEFAULT_CONFIG)

    assert response.status_code == 403


def test_updating_late_fee_and_cycle_changes_payment_math():
    headers = admin_headers()
    try:
        updated = client.put(
            "/config/",
            headers=headers,
            json={
                "institution_name": "CTC El Salvador",
                "late_fee": 5.00,
                "payment_cycle_days": 30,
                "alert_days_before": 7,
            },
        )
        assert updated.status_code == 200

        fetched = client.get("/config/", headers=headers)
        assert fetched.status_code == 200
        assert fetched.json()["late_fee"] == 5.00
        assert fetched.json()["payment_cycle_days"] == 30

        overdue_start = date.today() - timedelta(days=40)
        enrollment = create_enrollment(headers, start_date=overdue_start)

        payment = client.post(
            "/payments/collect",
            headers=headers,
            json={
                "enrollment_id": enrollment["id"],
                "payment_date": date.today().isoformat(),
                "cash_received": "45.00",
                "months": 1,
            },
        )
        assert payment.status_code == 200
        data = payment.json()
        # El recargo y el ciclo deben reflejar la nueva configuración, no
        # los valores por defecto de $3.00 / 28 días.
        assert Decimal(data["surcharge"]) == Decimal("5.00")
        assert data["next_payment_date"] == (
            date.fromisoformat(data["first_due_date"]) + timedelta(days=30)
        ).isoformat()
    finally:
        # Restaurar los valores por defecto para no afectar otras pruebas
        # que asumen el recargo/ciclo estándar de CTC.
        client.put("/config/", headers=headers, json=DEFAULT_CONFIG)
