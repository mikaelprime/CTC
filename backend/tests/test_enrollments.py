import calendar
from datetime import date
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
