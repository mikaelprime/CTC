"""Evidencia de cada punto de la propuesta del proyecto ("Propuesta - Proyecto
Software.pdf"), en el mismo orden del documento, más las mejoras
recomendadas y las "otras" mejoras que agrega el sistema.

Ver también docs/TRAZABILIDAD.md (requisito → pantalla → endpoint → prueba).
"""

from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from app.core import clock
from app.core.rate_limit import _failed_attempts
from app.database.database import SessionLocal
from app.models.student import Student
from app.models.user import User
from app.services.email_service import EmailService
from app.services.payment_service import PaymentService
from tests.conftest import client, student_payload, unique_surname
from tests.test_cashier import cashier_headers, ensure_register_closed
from tests.test_payments import MONTHLY_FEE, auth_headers, create_enrollment

TODAY = date.today()


def _catalog(headers, duration_months=6):
    diploma = client.post("/diplomas/", headers=headers, json={
        "name": f"Diplomado PDF {uuid4().hex[:6]}", "duration_months": duration_months,
    }).json()
    schedule = client.post("/schedules/", headers=headers, json={
        "name": f"Sábados PDF {uuid4().hex[:6]}", "start_time": "08:00:00", "end_time": "10:15:00",
    }).json()
    return diploma["id"], schedule["id"]


def _open_cashier_register(initial=0):
    headers = cashier_headers()
    ensure_register_closed(headers)
    assert client.post("/cashier/register/open", headers=headers, json={"initial_amount": initial}).status_code == 200
    return headers


def _enroll(headers, start=TODAY, **extra):
    diploma_id, schedule_id = _catalog(auth_headers())
    body = {
        "student": student_payload(),
        "diploma_id": diploma_id,
        "schedule_id": schedule_id,
        "enrollment_date": min(start, TODAY).isoformat(),
        "start_date": start.isoformat(),
        **extra,
    }
    return client.post("/enrollments/", headers=headers, json=body)


# ------------------------------------------------ 1. Registro de matrícula

def test_1_matricula_en_un_solo_formulario_con_todos_los_datos_del_pdf():
    """Página 2 del PDF: datos del estudiante, del responsable, servicio,
    horario, fecha de inicio y observaciones, en un solo registro."""
    headers = _open_cashier_register()
    minor_birth = (TODAY - timedelta(days=365 * 16)).isoformat()
    response = _enroll(
        headers,
        student=student_payload(
            birth_date=minor_birth,
            responsible_name="María López",
            responsible_dui="00016297-5",
            responsible_kinship="Madre",
            responsible_email=f"madre-{uuid4().hex[:6]}@correo.com",
            responsible_whatsapp="7777-1234",
        ),
        observations="Prefiere turno de mañana",
        cash_received=20,
    )
    assert response.status_code == 200, response.json()
    data = response.json()
    student = client.get(f"/students/{data['student_id']}", headers=headers).json()
    assert student["age"] == 15 or student["age"] == 16
    assert student["responsible_kinship"] == "Madre"
    assert data["observations"] == "Prefiere turno de mañana"
    assert data["start_date"] == TODAY.isoformat()


def test_1_matricula_es_atomica_si_falla_el_cobro_no_queda_el_estudiante():
    headers = _open_cashier_register()
    payload = student_payload()
    response = _enroll(headers, student=payload, cash_received=5)  # faltan $15
    assert response.status_code == 400
    names = {s["full_name"] for s in client.get("/students/", headers=headers).json()}
    assert payload["full_name"] not in names


def test_1_no_se_registra_dos_veces_al_mismo_estudiante():
    headers = auth_headers()
    payload = student_payload()
    assert client.post("/students/", headers=headers, json=payload).status_code == 200
    again = dict(payload, email=f"otro-{uuid4().hex[:6]}@ctc.edu.sv")
    duplicated = client.post("/students/", headers=headers, json=again)
    assert duplicated.status_code == 409
    assert "Ya existe un estudiante" in duplicated.json()["detail"]


def test_1_diplomados_y_horarios_oficiales_del_pdf_estan_cargados():
    headers = auth_headers()
    diplomas = {d["name"] for d in client.get("/diplomas/", headers=headers).json()}
    assert {"Secretariado en Informática", "Operador en Sistemas Informáticos",
            "Marketing Digital", "Soporte Técnico"} <= diplomas
    schedules = {s["name"] for s in client.get("/schedules/", headers=headers).json()}
    assert {"Sábados 8:00 - 10:15", "Sábados 10:00 - 12:15", "Sábados 1:00 - 3:15",
            "Domingos 8:00 - 10:15", "Domingos 10:00 - 12:15"} <= schedules


# ------------------------------------------------ 2. Cobro cada 28 días

def test_2_ejemplo_literal_del_pdf_inicio_01_08_2026():
    """"Si el inicio de clases está programado para el 01/08/2026, el primer
    pago de colegiatura será la misma fecha y el próximo el 29/08/2026"."""
    start = date(2026, 8, 1)
    assert PaymentService.due_date(start, 0, 28) == date(2026, 8, 1)
    assert PaymentService.due_date(start, 1, 28) == date(2026, 8, 29)
    assert PaymentService.due_date(start, 2, 28) == date(2026, 9, 26)


def test_2_primer_cobro_el_dia_de_inicio_y_siguiente_28_dias_despues():
    headers = _open_cashier_register()
    enrollment = _enroll(headers, cash_received=20).json()
    assert enrollment["next_payment_date"] == TODAY.isoformat()
    paid = client.post("/payments/collect", headers=headers, json={
        "enrollment_id": enrollment["id"], "cash_received": 25,
    }).json()
    assert paid["first_due_date"] == TODAY.isoformat()
    assert paid["next_payment_date"] == (TODAY + timedelta(days=28)).isoformat()


def test_2_el_diplomado_tiene_un_numero_fijo_de_cuotas():
    """6 meses = 7 cuotas de 28 días. No se puede cobrar de más, y al pagar
    todas y terminar el diplomado la matrícula queda FINALIZADA."""
    headers = _open_cashier_register()
    enrollment = _enroll(headers, start=TODAY - timedelta(days=200), cash_received=20).json()
    assert enrollment["installments_total"] == 7
    too_many = client.post("/payments/collect", headers=headers, json={
        "enrollment_id": enrollment["id"], "months": 8, "cash_received": 500,
    })
    assert too_many.status_code == 400
    assert "le quedan 7" in too_many.json()["detail"]
    all_paid = client.post("/payments/collect", headers=headers, json={
        "enrollment_id": enrollment["id"], "months": 7, "cash_received": 500, "apply_late_fee": False,
    })
    assert all_paid.status_code == 200, all_paid.json()
    assert all_paid.json()["next_payment_date"] is None
    data = client.get(f"/enrollments/{enrollment['id']}", headers=headers).json()
    assert data["status"] == "FINALIZADA"
    again = client.post("/payments/collect", headers=headers, json={
        "enrollment_id": enrollment["id"], "cash_received": 25,
    })
    assert again.status_code == 400


# ------------------------------------------------ 3. Tarifas

def test_3_tarifas_del_pdf_por_defecto():
    config = client.get("/config/", headers=auth_headers()).json()
    assert (config["registration_full_fee"], config["registration_promo_fee"]) == (20.0, 10.0)
    assert (config["tuition_group_fee"], config["tuition_private_fee"], config["tuition_online_fee"]) == (25.0, 55.0, 70.0)


def test_3_matricula_gratis_no_genera_cobro_ni_pide_caja():
    headers = cashier_headers()
    ensure_register_closed(headers)
    response = _enroll(headers, registration_type="GRATIS")
    assert response.status_code == 200
    assert float(response.json()["registration_fee"]) == 0
    assert response.json()["receipt_number"] is None


def test_3_las_tarifas_se_pueden_actualizar_sin_reprogramar():
    admin = auth_headers()
    config = client.get("/config/", headers=admin).json()
    try:
        assert client.put("/config/", headers=admin, json={**config, "tuition_online_fee": 75}).status_code == 200
        headers = _open_cashier_register()
        enrollment = _enroll(headers, tuition_plan="ONLINE", cash_received=20).json()
        info = client.get(f"/payments/next/{enrollment['id']}", headers=headers).json()
        assert float(info["monthly_amount"]) == 75
        # Queda en la bitácora con el valor anterior y el nuevo.
        log = client.get("/audit/?action=CAMBIO_CONFIGURACION", headers=admin).json()
        assert "tuition_online_fee: 70" in log[0]["detail"]
    finally:
        client.put("/config/", headers=admin, json=config)


# ------------------------------------------------ 4. Efectivo y cambio

def test_4_efectivo_y_cambio_calculado_por_el_sistema():
    headers = _open_cashier_register()
    enrollment = _enroll(headers, cash_received=50).json()
    assert float(enrollment["change"]) == 30  # matrícula $20 con $50
    paid = client.post("/payments/collect", headers=headers, json={
        "enrollment_id": enrollment["id"], "cash_received": 40,
    }).json()
    assert float(paid["change"]) == 15  # colegiatura $25 con $40
    short = client.post("/payments/collect", headers=headers, json={
        "enrollment_id": enrollment["id"], "cash_received": 10,
    })
    assert short.status_code == 400


def test_4_con_tarjeta_no_hay_efectivo_ni_cambio():
    headers = _open_cashier_register()
    enrollment = _enroll(headers, payment_type="Tarjeta").json()
    assert float(enrollment["change"]) == 0
    paid = client.post("/payments/collect", headers=headers, json={
        "enrollment_id": enrollment["id"], "payment_type": "Transferencia",
    }).json()
    assert float(paid["cash_received"]) == float(paid["total"])
    assert float(paid["change"]) == 0


# ------------------------------------------------ 5. Cierre de caja diario / mensual

def test_5_todo_cobro_exige_caja_abierta_tambien_para_el_administrador():
    """Si el administrador cobrara sin caja, ese dinero quedaría fuera del
    arqueo. Aquí se usa un administrador nuevo, sin caja abierta."""
    email = f"admin-{uuid4().hex[:6]}@ctc.edu.sv"
    with SessionLocal() as db:
        admin = db.query(User).filter(User.email == "admin@ctc.edu.sv").one()
        db.add(User(full_name="Admin Temporal", email=email, password=admin.password,
                    birth_date=date(1990, 1, 1), role_id=admin.role_id))
        db.commit()
    token = client.post("/auth/login", json={"email": email, "password": "123456"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    enrollment = create_enrollment(auth_headers(), TODAY)
    blocked = client.post("/payments/collect", headers=headers, json={
        "enrollment_id": enrollment["id"], "cash_received": 25,
    })
    assert blocked.status_code == 403


def test_5_reporte_de_cierre_diario_con_detalle_por_concepto_y_arqueo_por_denominacion():
    headers = _open_cashier_register(initial=10)
    enrollment = _enroll(headers, cash_received=20).json()                     # matrícula $20
    client.post("/payments/collect", headers=headers, json={                    # colegiatura $25
        "enrollment_id": enrollment["id"], "cash_received": 25,
    })
    current = client.get("/cashier/register/current", headers=headers).json()
    assert current["expected_amount"] == 55  # 10 de fondo + 45 cobrados

    # Arqueo: 2 billetes de $20, 1 de $10, 1 de $5 = $55.
    closed = client.post("/cashier/register/close", headers=headers, json={
        "cash_count": {"20.00": 2, "10.00": 1, "5.00": 1},
    })
    assert closed.status_code == 200, closed.json()
    assert closed.json()["diferencia"] == 0

    report = client.get(f"/cashier/registers/{closed.json()['register_id']}/report", headers=headers).json()
    concepts = {row["concept"]: row["amount"] for row in report["summary"]["by_concept"]}
    assert concepts == {"Matrícula completa": 20, "Colegiatura Plan Grupal": 25}
    assert report["cash_count"] == {"20.00": 2, "10.00": 1, "5.00": 1}
    assert len(report["payments"]) == 2
    assert all(row["receipt_number"].startswith("R-") for row in report["payments"])


def test_5_descuadre_exige_justificacion_y_queda_en_bitacora():
    headers = _open_cashier_register(initial=10)
    missing = client.post("/cashier/register/close", headers=headers, json={"physical_amount": 8})
    assert missing.status_code == 400
    closed = client.post("/cashier/register/close", headers=headers, json={
        "physical_amount": 8, "explanation": "Se dio cambio de más",
    })
    assert closed.json()["diferencia"] == -2
    log = client.get("/audit/?action=CIERRE_CAJA", headers=auth_headers()).json()
    assert "Se dio cambio de más" in log[0]["detail"]


def test_5_una_caja_solo_suma_sus_propios_cobros():
    """Antes la caja sumaba "lo cobrado desde que abrió": un cobro de otra
    caja del mismo cajero se podía mezclar. Ahora cada cobro sabe su caja."""
    headers = _open_cashier_register()
    enrollment = _enroll(headers, cash_received=20).json()
    first = client.post("/cashier/register/close", headers=headers, json={"physical_amount": 20}).json()
    headers = _open_cashier_register()
    client.post("/payments/collect", headers=headers, json={"enrollment_id": enrollment["id"], "cash_received": 25})
    assert client.get("/cashier/register/current", headers=headers).json()["collected_amount"] == 25
    report = client.get(f"/cashier/registers/{first['register_id']}/report", headers=headers).json()
    assert report["summary"]["total"] == 20


def test_5_cierre_diario_general_y_mensual_por_dia():
    headers = _open_cashier_register()
    _enroll(headers, cash_received=20)
    daily = client.get("/cashier/daily", headers=auth_headers()).json()
    assert daily["summary"]["total"] >= 20
    assert daily["summary"]["by_method"]
    monthly = client.get(f"/cashier/monthly?year={TODAY.year}&month={TODAY.month}", headers=auth_headers()).json()
    assert monthly["by_day"][-1]["total"] >= 20
    assert monthly["summary"]["by_concept"]


def test_5_un_cajero_no_ve_cierres_de_otro():
    headers = cashier_headers()
    assert client.get("/cashier/daily?cashier_id=1", headers=headers).status_code == 403


# ------------------------------------------------ 6. Alerta de estado

def test_6_estado_pendiente_al_pasar_28_dias_sin_cobro():
    headers = _open_cashier_register()
    enrollment = _enroll(headers, start=TODAY - timedelta(days=30), cash_received=20).json()
    assert enrollment["status"] == "PENDIENTE"
    assert enrollment["overdue_installments"] == 2  # cuotas del día 0 y del día 28


def test_6_aviso_7_dias_antes_llega_al_estudiante_y_al_responsable(monkeypatch):
    sent = []
    monkeypatch.setattr(EmailService, "_send_email", staticmethod(lambda to, subject, *a, **k: sent.append((to, subject))))
    headers = _open_cashier_register()
    responsible_email = f"papa-{uuid4().hex[:6]}@correo.com"
    enrollment = _enroll(
        headers, start=TODAY + timedelta(days=7), cash_received=20,
        student=student_payload(responsible_name="José Pérez", responsible_email=responsible_email),
    ).json()
    sent.clear()
    with SessionLocal() as db:
        PaymentService.send_due_reminders(db)
    reminders = [to for to, subject in sent if f"#{enrollment['id']}" in subject and "Recordatorio" in subject]
    assert len(reminders) == 1
    assert responsible_email in reminders[0]


def test_6_lista_de_cobros_proximos_con_whatsapp_y_monto_adeudado():
    headers = _open_cashier_register()
    soon = _enroll(headers, start=TODAY + timedelta(days=3), cash_received=20,
                   student=student_payload(responsible_name="Ana Gómez", responsible_whatsapp="7123-4567")).json()
    late = _enroll(headers, start=TODAY - timedelta(days=30), cash_received=20).json()
    rows = {r["enrollment_id"]: r for r in client.get("/reports/upcoming-payments?days=7", headers=headers).json()}
    assert rows[soon["id"]]["days_remaining"] == 3
    assert rows[soon["id"]]["whatsapp_url"].startswith("https://wa.me/50371234567?text=")
    assert rows[late["id"]]["overdue_installments"] == 2
    assert float(rows[late["id"]]["amount_owed"]) == 2 * MONTHLY_FEE + 3  # dos cuotas + recargo


# ------------------------------------------------ Mejoras recomendadas

def test_mejora_ticket_con_numero_correlativo_y_reimpresion():
    headers = _open_cashier_register()
    enrollment = _enroll(headers, cash_received=20).json()
    first = client.post("/payments/collect", headers=headers, json={"enrollment_id": enrollment["id"], "cash_received": 25}).json()
    second = client.post("/payments/collect", headers=headers, json={"enrollment_id": enrollment["id"], "cash_received": 25}).json()
    assert second["receipt_id"] > first["receipt_id"] > enrollment["receipt_id"]
    ticket = client.get(f"/payments/{first['payment_ids'][0]}/ticket", headers=headers).json()
    assert ticket["receipt_number"] == first["receipt_number"]
    assert ticket["cashier_name"] == "Cajero CTC"
    assert ticket["student_name"] == enrollment["student"]["full_name"]
    assert ticket["lines"][0]["concept"].startswith("Colegiatura cuota 1 de 7")


def test_mejora_recargo_opcional_de_3_dolares():
    headers = _open_cashier_register()
    enrollment = _enroll(headers, start=TODAY - timedelta(days=3), cash_received=20).json()
    info = client.get(f"/payments/next/{enrollment['id']}", headers=headers).json()
    assert float(info["automatic_surcharge"]) == 3
    waived = client.post("/payments/collect", headers=headers, json={
        "enrollment_id": enrollment["id"], "cash_received": 25, "apply_late_fee": False,
    }).json()
    assert float(waived["surcharge"]) == 0


# ------------------------------------------------ Otras mejoras

def test_otra_bitacora_registra_cobros_y_anulaciones():
    headers = _open_cashier_register()
    enrollment = _enroll(headers, cash_received=20).json()
    paid = client.post("/payments/collect", headers=headers, json={"enrollment_id": enrollment["id"], "cash_received": 25}).json()
    admin = auth_headers()
    client.post(f"/payments/{paid['payment_ids'][0]}/void", headers=admin, json={"reason": "Prueba de bitácora"})
    log = client.get("/audit/", headers=admin).json()
    actions = [row["action"] for row in log[:6]]
    assert "ANULACION_PAGO" in actions and "COBRO" in actions and "INSCRIPCION" in actions
    assert any(paid["receipt_number"] in (row["detail"] or "") for row in log[:6])


def test_otra_contrasena_temporal_obliga_a_cambiarla():
    admin = auth_headers()
    email = f"nuevo-{uuid4().hex[:6]}@ctc.edu.sv"
    client.post("/users/cashiers", headers=admin, json={
        "full_name": f"Cajero {unique_surname()}", "email": email, "password": "Temporal1", "birth_date": "1995-01-01",
    })
    login = client.post("/auth/login", json={"email": email, "password": "Temporal1"}).json()
    assert login["must_change_password"] is True
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    assert client.get("/students/", headers=headers).status_code == 403
    changed = client.post("/auth/change-password", headers=headers, json={
        "current_password": "Temporal1", "new_password": "Definitiva2",
    })
    assert changed.status_code == 200
    assert client.get("/students/", headers=headers).status_code == 200


def test_otra_bloqueo_por_intentos_fallidos_sobrevive_a_un_reinicio():
    admin = auth_headers()
    email = f"bloqueo-{uuid4().hex[:6]}@ctc.edu.sv"
    client.post("/users/cashiers", headers=admin, json={
        "full_name": f"Cajero {unique_surname()}", "email": email, "password": "Correcta1", "birth_date": "1995-01-01",
    })
    for _ in range(5):
        client.post("/auth/login", json={"email": email, "password": "incorrecta"})
    _failed_attempts.clear()  # simula que Render reinició el backend
    blocked = client.post("/auth/login", json={"email": email, "password": "Correcta1"})
    assert blocked.status_code == 429


def test_otra_fecha_y_hora_oficial_de_el_salvador():
    """A las 11:30 p. m. del 28/09 en El Salvador ya es 29/09 en UTC: el
    sistema debe seguir usando el 28/09."""
    utc_instant = datetime(2026, 9, 29, 5, 30, tzinfo=timezone.utc)
    assert utc_instant.astimezone(clock.LOCAL_TZ).date() == date(2026, 9, 28)
    begin, end = clock.local_day_bounds_utc(date(2026, 9, 28), date(2026, 9, 28))
    assert (begin, end) == (datetime(2026, 9, 28, 6, 0), datetime(2026, 9, 29, 6, 0))


def test_otra_edad_siempre_actualizada_desde_la_fecha_de_nacimiento():
    headers = auth_headers()
    created = client.post("/students/", headers=headers, json=student_payload(birth_date="2000-01-15")).json()
    with SessionLocal() as db:
        db.get(Student, created["id"]).age = 3  # edad guardada vieja o errónea
        db.commit()
    assert client.get(f"/students/{created['id']}", headers=headers).json()["age"] == clock.today().year - 2000 - (
        (clock.today().month, clock.today().day) < (1, 15)
    )


def test_otra_correos_al_estudiante_y_a_su_responsable_sin_repetir():
    student = Student(email="ana@correo.com", responsible_email="ANA@correo.com")
    assert EmailService.recipients(student) == ["ana@correo.com"]
    student = Student(email="ana@correo.com", responsible_email="mama@correo.com")
    assert EmailService.recipients(student) == ["ana@correo.com", "mama@correo.com"]


def test_otra_diplomado_inactivo_no_recibe_inscripciones():
    admin = auth_headers()
    diploma_id, schedule_id = _catalog(admin)
    client.put(f"/diplomas/{diploma_id}", headers=admin, json={"active": False})
    response = client.post("/enrollments/", headers=admin, json={
        "student": student_payload(), "diploma_id": diploma_id, "schedule_id": schedule_id,
        "enrollment_date": TODAY.isoformat(), "start_date": TODAY.isoformat(), "registration_type": "GRATIS",
    })
    assert response.status_code == 400


def test_otra_solo_quedan_endpoints_de_cobro_seguros():
    """No existe alta manual de pagos, pago "adelantado" duplicado, ni
    edición o borrado de pagos: todo cobro pasa por /payments/collect o por
    la inscripción, con comprobante y caja."""
    paths = client.get("/openapi.json").json()["paths"]
    assert set(paths["/payments/"]) == {"get"}
    assert "/payments/advance" not in paths
    assert set(paths["/payments/{payment_id}"]) == {"get"}


def test_otra_sin_campos_sobrantes_en_el_modelo():
    """Los precios por diplomado nunca se usaban para cobrar (el tarifario es
    institucional) y el DUI del estudiante no está en la propuesta."""
    from app.models.diploma import Diploma

    assert {"registration_fee", "monthly_fee"}.isdisjoint(Diploma.__table__.columns.keys())
    assert "dui" not in Student.__table__.columns
