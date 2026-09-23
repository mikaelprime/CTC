import calendar
from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import event

from app.database.database import engine
from tests.conftest import client


def auth_headers():
    response = client.post(
        "/auth/login",
        json={"email": "admin@ctc.edu.sv", "password": "123456"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def add_months(base_date: date, months: int) -> date:
    month_index = base_date.month - 1 + months
    year = base_date.year + month_index // 12
    month = month_index % 12 + 1
    day = min(base_date.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def create_student(headers):
    email = f"enroll-{uuid4().hex[:8]}@ctc.edu.sv"
    response = client.post(
        "/students/",
        headers=headers,
        json={"full_name": "Estudiante Matricula", "email": email},
    )
    assert response.status_code == 200
    return response.json()["id"]


def create_diploma(headers, duration_months=4):
    response = client.post(
        "/diplomas/",
        headers=headers,
        json={
            "name": f"Diplomado Matricula {uuid4().hex[:8]}",
            "duration_months": duration_months,
            "registration_fee": 25,
            "monthly_fee": 40,
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def create_schedule(headers):
    response = client.post(
        "/schedules/",
        headers=headers,
        json={
            "name": f"Turno Matricula {uuid4().hex[:8]}",
            "start_time": "18:00:00",
            "end_time": "20:00:00",
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def test_create_enrollment_calculates_end_date():
    headers = auth_headers()
    student_id = create_student(headers)
    diploma_id = create_diploma(headers, duration_months=4)
    schedule_id = create_schedule(headers)

    enrollment_date = date.today().isoformat()
    response = client.post(
        "/enrollments/",
        headers=headers,
        json={
            "student_id": student_id,
            "diploma_id": diploma_id,
            "schedule_id": schedule_id,
            "enrollment_date": enrollment_date,
        },
    )

    assert response.status_code == 200
    data = response.json()
    expected_end = add_months(date.today(), 4)
    assert data["start_date"] == enrollment_date
    assert data["end_date"] == expected_end.isoformat()
    assert data["student"]["id"] == student_id
    assert data["diploma"]["id"] == diploma_id


def test_list_enrollments_does_not_run_a_query_per_row():
    """Regresión: /enrollments/ llegó a tardar 8+ segundos con ~20 filas
    porque student/diploma/schedule se cargaban de forma perezosa (una
    consulta aparte por cada relación de cada fila). Crea varias matrículas
    y verifica que listar no dispare una consulta por fila."""
    headers = auth_headers()
    for _ in range(6):
        student_id = create_student(headers)
        diploma_id = create_diploma(headers)
        schedule_id = create_schedule(headers)
        created = client.post(
            "/enrollments/",
            headers=headers,
            json={
                "student_id": student_id,
                "diploma_id": diploma_id,
                "schedule_id": schedule_id,
                "enrollment_date": date.today().isoformat(),
            },
        )
        assert created.status_code == 200

    queries = []

    def count_query(conn, cursor, statement, parameters, context, executemany):
        queries.append(statement)

    event.listen(engine, "before_cursor_execute", count_query)
    try:
        response = client.get("/enrollments/", headers=headers)
    finally:
        event.remove(engine, "before_cursor_execute", count_query)

    assert response.status_code == 200
    total_rows = len(response.json())
    # Con eager loading esto es ~1 consulta sin importar cuántas filas haya;
    # sin eager loading sería del orden de 3 por fila. El margen es generoso
    # a propósito para no volverse frágil si se agrega alguna consulta más.
    assert len(queries) < total_rows, (
        f"{len(queries)} consultas SQL para {total_rows} filas: "
        "parece que volvió el problema N+1 en EnrollmentService"
    )


def find_payment(headers, enrollment_id, kind=None):
    payments = client.get("/payments/", headers=headers).json()
    matches = [p for p in payments if p["enrollment_id"] == enrollment_id]
    if kind:
        matches = [p for p in matches if p["kind"] == kind]
    return matches


def test_create_enrollment_charges_default_registration_fee():
    """Sin especificar tipo de matrícula, debe cobrar la Matrícula completa
    ($20) como un pago aparte, no incluido en el ciclo de colegiatura."""
    headers = auth_headers()
    student_id = create_student(headers)
    diploma_id = create_diploma(headers)
    schedule_id = create_schedule(headers)

    response = client.post(
        "/enrollments/",
        headers=headers,
        json={
            "student_id": student_id,
            "diploma_id": diploma_id,
            "schedule_id": schedule_id,
            "enrollment_date": date.today().isoformat(),
        },
    )
    assert response.status_code == 200
    enrollment = response.json()
    assert enrollment["registration_type"] == "COMPLETA"
    assert enrollment["tuition_plan"] == "GRUPAL"

    matricula_payments = find_payment(headers, enrollment["id"], kind="MATRICULA")
    assert len(matricula_payments) == 1
    assert Decimal(matricula_payments[0]["total"]) == Decimal("20.00")
    assert matricula_payments[0]["status"] == "PAGADO"


def test_create_enrollment_promo_registration_charges_ten_dollars():
    headers = auth_headers()
    student_id = create_student(headers)
    diploma_id = create_diploma(headers)
    schedule_id = create_schedule(headers)

    response = client.post(
        "/enrollments/",
        headers=headers,
        json={
            "student_id": student_id,
            "diploma_id": diploma_id,
            "schedule_id": schedule_id,
            "enrollment_date": date.today().isoformat(),
            "registration_type": "PROMO",
        },
    )
    assert response.status_code == 200
    enrollment = response.json()

    matricula_payments = find_payment(headers, enrollment["id"], kind="MATRICULA")
    assert len(matricula_payments) == 1
    assert Decimal(matricula_payments[0]["total"]) == Decimal("10.00")


def test_create_enrollment_free_registration_creates_no_payment():
    headers = auth_headers()
    student_id = create_student(headers)
    diploma_id = create_diploma(headers)
    schedule_id = create_schedule(headers)

    response = client.post(
        "/enrollments/",
        headers=headers,
        json={
            "student_id": student_id,
            "diploma_id": diploma_id,
            "schedule_id": schedule_id,
            "enrollment_date": date.today().isoformat(),
            "registration_type": "GRATIS",
        },
    )
    assert response.status_code == 200
    enrollment = response.json()

    assert find_payment(headers, enrollment["id"], kind="MATRICULA") == []


def test_create_enrollment_rejects_invalid_registration_type():
    headers = auth_headers()
    student_id = create_student(headers)
    diploma_id = create_diploma(headers)
    schedule_id = create_schedule(headers)

    response = client.post(
        "/enrollments/",
        headers=headers,
        json={
            "student_id": student_id,
            "diploma_id": diploma_id,
            "schedule_id": schedule_id,
            "enrollment_date": date.today().isoformat(),
            "registration_type": "NO_EXISTE",
        },
    )
    assert response.status_code == 400


def test_create_enrollment_rejects_invalid_tuition_plan():
    headers = auth_headers()
    student_id = create_student(headers)
    diploma_id = create_diploma(headers)
    schedule_id = create_schedule(headers)

    response = client.post(
        "/enrollments/",
        headers=headers,
        json={
            "student_id": student_id,
            "diploma_id": diploma_id,
            "schedule_id": schedule_id,
            "enrollment_date": date.today().isoformat(),
            "tuition_plan": "NO_EXISTE",
        },
    )
    assert response.status_code == 400


def test_collect_payment_uses_tuition_plan_price_not_diploma_monthly_fee():
    """El monto de la colegiatura sale de TUITION_PLANS[tuition_plan], no de
    Diploma.monthly_fee (que puede ser cualquier cosa y ya no se usa para
    calcular cobros)."""
    headers = auth_headers()
    student_id = create_student(headers)
    diploma_id = create_diploma(headers)  # monthly_fee=40, ahora irrelevante
    schedule_id = create_schedule(headers)
    today = date.today()

    enrollment = client.post(
        "/enrollments/",
        headers=headers,
        json={
            "student_id": student_id,
            "diploma_id": diploma_id,
            "schedule_id": schedule_id,
            "enrollment_date": today.isoformat(),
            "start_date": today.isoformat(),
            "tuition_plan": "PRIVADO",
        },
    ).json()

    collected = client.post(
        "/payments/collect",
        headers=headers,
        json={
            "enrollment_id": enrollment["id"],
            "payment_date": today.isoformat(),
            "cash_received": "55.00",
            "months": 1,
        },
    )

    assert collected.status_code == 200
    data = collected.json()
    assert Decimal(data["total"]) == Decimal("55.00")

    colegiatura_payments = find_payment(headers, enrollment["id"], kind="COLEGIATURA")
    assert len(colegiatura_payments) == 1
    assert Decimal(colegiatura_payments[0]["amount"]) == Decimal("55.00")


def test_registration_payment_does_not_shift_first_tuition_due_date():
    """Regresión: al agregar el cobro de matrícula como Payment,
    get_last_by_enrollment lo confundía con "la última cuota de
    colegiatura" y el primer vencimiento se corría 28 días de más."""
    headers = auth_headers()
    student_id = create_student(headers)
    diploma_id = create_diploma(headers)
    schedule_id = create_schedule(headers)
    today = date.today()

    enrollment = client.post(
        "/enrollments/",
        headers=headers,
        json={
            "student_id": student_id,
            "diploma_id": diploma_id,
            "schedule_id": schedule_id,
            "enrollment_date": today.isoformat(),
            "start_date": today.isoformat(),
        },
    ).json()

    info = client.get(f"/payments/next/{enrollment['id']}", headers=headers)
    assert info.status_code == 200
    assert info.json()["due_date"] == today.isoformat()


def test_create_enrollment_with_missing_diploma_returns_404():
    headers = auth_headers()
    student_id = create_student(headers)
    schedule_id = create_schedule(headers)

    response = client.post(
        "/enrollments/",
        headers=headers,
        json={
            "student_id": student_id,
            "diploma_id": 9999999999,
            "schedule_id": schedule_id,
            "enrollment_date": date.today().isoformat(),
        },
    )

    assert response.status_code == 404
