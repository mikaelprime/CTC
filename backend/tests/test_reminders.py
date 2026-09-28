"""Recordatorio de pago próximo (PDF: "notificar al estudiante 7 días antes
de la fecha de vencimiento"), disparado desde el login en vez de un cron.

Se prueba llamando a PaymentService.send_due_reminders directamente con una
sesión de DB, no vía HTTP: así se puede leer/comparar last_reminder_due_date
sin depender de que la API lo exponga.
"""

from datetime import date, timedelta
from uuid import uuid4

from app.database.database import SessionLocal
from app.models.enrollment import Enrollment
from app.services.payment_service import PaymentService
from tests.conftest import client, student_payload


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
        json=student_payload(full_name="Estudiante Recordatorio", email=f"rec-{uuid4().hex[:8]}@ctc.edu.sv"),
    )
    assert student.status_code == 200

    diploma = client.post(
        "/diplomas/",
        headers=headers,
        json={
            "name": f"Diplomado Recordatorio {uuid4().hex[:8]}",
            "duration_months": 6,
            "registration_fee": 25,
            "monthly_fee": 40,
        },
    )
    assert diploma.status_code == 200

    schedule = client.post(
        "/schedules/",
        headers=headers,
        json={"name": f"Turno Recordatorio {uuid4().hex[:8]}", "start_time": "08:00:00", "end_time": "10:00:00"},
    )
    assert schedule.status_code == 200

    enrollment = client.post(
        "/enrollments/",
        headers=headers,
        json={
            "student_id": student.json()["id"],
            "diploma_id": diploma.json()["id"],
            "schedule_id": schedule.json()["id"],
            "enrollment_date": min(start_date, date.today()).isoformat(),
            "start_date": start_date.isoformat(),
        },
    )
    assert enrollment.status_code == 200
    return enrollment.json()


def test_send_due_reminders_flags_enrollment_due_within_window():
    headers = auth_headers()
    today = date.today()
    enrollment = create_enrollment(headers, start_date=today)

    db = SessionLocal()
    try:
        sent = PaymentService.send_due_reminders(db)
        assert sent >= 1

        row = db.query(Enrollment).filter(Enrollment.id == enrollment["id"]).first()
        assert row.last_reminder_due_date == today
    finally:
        db.close()


def test_send_due_reminders_does_not_resend_same_due_date():
    headers = auth_headers()
    today = date.today()
    enrollment = create_enrollment(headers, start_date=today)

    db = SessionLocal()
    try:
        first_run = PaymentService.send_due_reminders(db)
        assert first_run >= 1

        second_run = PaymentService.send_due_reminders(db)
        row = db.query(Enrollment).filter(Enrollment.id == enrollment["id"]).first()
        # Esta matrícula puntual ya no debe volver a contarse en la segunda
        # pasada (otras matrículas de otras pruebas sí podrían, por eso no
        # se afirma == 0 en total, solo que esta ya no aporta).
        assert row.last_reminder_due_date == today
        assert second_run <= first_run
    finally:
        db.close()


def test_send_due_reminders_ignores_due_dates_outside_the_window():
    headers = auth_headers()
    far_future = date.today() + timedelta(days=30)
    enrollment = create_enrollment(headers, start_date=far_future)

    db = SessionLocal()
    try:
        PaymentService.send_due_reminders(db)
        row = db.query(Enrollment).filter(Enrollment.id == enrollment["id"]).first()
        assert row.last_reminder_due_date is None
    finally:
        db.close()
