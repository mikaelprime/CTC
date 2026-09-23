from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from tests.conftest import client


# Coincide con TUITION_PLANS["GRUPAL"] (app.core.pricing): el precio ya no
# sale de Diploma.monthly_fee, sino del plan de colegiatura elegido al
# inscribir, y estas matrículas no especifican tuition_plan (usan el
# default "GRUPAL").
MONTHLY_FEE = 25


def auth_headers():
    response = client.post(
        "/auth/login",
        json={"email": "admin@ctc.edu.sv", "password": "123456"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_enrollment(headers, start_date: date):
    student = client.post(
        "/students/",
        headers=headers,
        json={"full_name": "Estudiante Pagos", "email": f"pagos-{uuid4().hex[:8]}@ctc.edu.sv"},
    )
    assert student.status_code == 200

    diploma = client.post(
        "/diplomas/",
        headers=headers,
        json={
            "name": f"Diplomado Pagos {uuid4().hex[:8]}",
            "duration_months": 6,
            "registration_fee": 25,
            "monthly_fee": MONTHLY_FEE,
        },
    )
    assert diploma.status_code == 200

    schedule = client.post(
        "/schedules/",
        headers=headers,
        json={"name": f"Turno Pagos {uuid4().hex[:8]}", "start_time": "08:00:00", "end_time": "10:00:00"},
    )
    assert schedule.status_code == 200

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


def test_collect_payment_on_time_has_no_surcharge():
    headers = auth_headers()
    today = date.today()
    enrollment = create_enrollment(headers, start_date=today)

    response = client.post(
        "/payments/collect",
        headers=headers,
        json={
            "enrollment_id": enrollment["id"],
            "payment_date": today.isoformat(),
            "cash_received": str(MONTHLY_FEE),
            "months": 1,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert Decimal(data["surcharge"]) == Decimal("0.00")
    assert Decimal(data["total"]) == Decimal(MONTHLY_FEE)
    assert Decimal(data["change"]) == Decimal("0.00")
    assert data["next_payment_date"] == (today + timedelta(days=28)).isoformat()


def test_collect_payment_overdue_applies_surcharge():
    headers = auth_headers()
    overdue_start = date.today() - timedelta(days=40)
    enrollment = create_enrollment(headers, start_date=overdue_start)

    response = client.post(
        "/payments/collect",
        headers=headers,
        json={
            "enrollment_id": enrollment["id"],
            "payment_date": date.today().isoformat(),
            "cash_received": str(MONTHLY_FEE + 3),
            "months": 1,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert Decimal(data["surcharge"]) == Decimal("3.00")
    assert Decimal(data["total"]) == Decimal(MONTHLY_FEE) + Decimal("3.00")
    assert data["late"] is True


def test_collect_payment_overdue_can_waive_surcharge():
    """El cajero puede destildar el recargo por mora (ej. excepción
    autorizada) en vez de que se aplique siempre automáticamente."""
    headers = auth_headers()
    overdue_start = date.today() - timedelta(days=40)
    enrollment = create_enrollment(headers, start_date=overdue_start)

    response = client.post(
        "/payments/collect",
        headers=headers,
        json={
            "enrollment_id": enrollment["id"],
            "payment_date": date.today().isoformat(),
            "cash_received": str(MONTHLY_FEE),
            "months": 1,
            "apply_late_fee": False,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert Decimal(data["surcharge"]) == Decimal("0.00")
    assert Decimal(data["total"]) == Decimal(MONTHLY_FEE)
    assert data["late"] is False


def test_collect_payment_rejects_insufficient_cash():
    headers = auth_headers()
    today = date.today()
    enrollment = create_enrollment(headers, start_date=today)

    response = client.post(
        "/payments/collect",
        headers=headers,
        json={
            "enrollment_id": enrollment["id"],
            "payment_date": today.isoformat(),
            "cash_received": "1.00",
            "months": 1,
        },
    )

    assert response.status_code == 400


def test_concurrent_collect_does_not_double_book_the_same_due_date():
    """Regresión: dos cobros simultáneos sobre la misma matrícula (dos
    cajeros, o un doble clic) no deben generar dos cuotas para el mismo mes.
    Antes del lock de fila, ambas peticiones leían el mismo "último pago" y
    calculaban la misma fecha de vencimiento."""
    headers = auth_headers()
    today = date.today()
    enrollment = create_enrollment(headers, start_date=today)

    def collect_one_month():
        return client.post(
            "/payments/collect",
            headers=headers,
            json={
                "enrollment_id": enrollment["id"],
                "payment_date": today.isoformat(),
                "cash_received": str(MONTHLY_FEE),
                "months": 1,
            },
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: collect_one_month(), range(2)))

    assert all(r.status_code == 200 for r in results)
    due_dates = [r.json()["first_due_date"] for r in results]
    assert due_dates[0] != due_dates[1], (
        f"ambos cobros quedaron con la misma fecha de vencimiento {due_dates}: "
        "se duplicó la cuota del mismo mes"
    )


def test_collect_payment_unknown_enrollment_returns_404():
    headers = auth_headers()

    response = client.post(
        "/payments/collect",
        headers=headers,
        json={
            "enrollment_id": 9999999999,
            "payment_date": date.today().isoformat(),
            "cash_received": "40.00",
            "months": 1,
        },
    )

    assert response.status_code == 404
