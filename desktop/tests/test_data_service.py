"""Pruebas de la lógica de agregación del dashboard (data_service.py).

Son funciones puras: reciben los datos ya cargados (dict con listas) y
calculan KPIs/gráficas sin tocar la red, así que se prueban sin necesidad
de abrir ninguna ventana ni levantar el backend.
"""

from datetime import date, timedelta

import data_service

TODAY = date.today()


def _student(id_=1, **overrides):
    row = {"id": id_, "full_name": f"Estudiante {id_}"}
    row.update(overrides)
    return row


def _enrollment(id_, diploma_name="Diplomado Test", status="ACTIVA", **overrides):
    row = {
        "id": id_,
        "enrollment_date": TODAY.isoformat(),
        "end_date": (TODAY + timedelta(days=30)).isoformat(),
        "status": status,
        "diploma": {"id": 1, "name": diploma_name},
        "student": {"id": id_, "full_name": f"Estudiante {id_}"},
    }
    row.update(overrides)
    return row


def _payment(id_, enrollment_id=1, status="PENDIENTE", total="40.00", **overrides):
    row = {
        "id": id_,
        "enrollment_id": enrollment_id,
        "status": status,
        "total": total,
        "payment_type": "Efectivo",
        "due_date": TODAY.isoformat(),
        "payment_date": TODAY.isoformat(),
    }
    row.update(overrides)
    return row


def test_kpis_generales_counts_students_and_pending_payments():
    data = {
        "students": [_student(1), _student(2)],
        "payments": [
            _payment(1, status="PENDIENTE", total="40.00"),
            _payment(2, status="PENDIENTE", total="35.50"),
            _payment(3, status="PAGADO", total="99.00"),
        ],
        "enrollments": [_enrollment(1)],
    }

    result = data_service.kpis_generales(data)

    assert result["estudiantes_activos"] == 2
    assert result["cuotas_por_auditar"] == 2
    assert result["pagos_pendientes"] == 75.50


def test_kpis_generales_counts_overdue_and_this_months_enrollments():
    overdue_due_date = TODAY - timedelta(days=5)
    data = {
        "students": [],
        "payments": [_payment(1, status="PENDIENTE", due_date=overdue_due_date.isoformat())],
        "enrollments": [
            _enrollment(1, enrollment_date=TODAY.isoformat()),
            _enrollment(2, enrollment_date=(TODAY - timedelta(days=400)).isoformat()),
        ],
    }

    result = data_service.kpis_generales(data)

    assert result["vencimientos"] == 1
    # Solo la primera matrícula es de este mes; la segunda es de hace más de un año.
    assert result["inscripciones_mes"] == 1


def test_kpis_generales_flags_enrollments_ending_within_48h():
    data = {
        "students": [],
        "payments": [],
        "enrollments": [
            _enrollment(1, status="ACTIVA", end_date=(TODAY + timedelta(days=1)).isoformat()),
            _enrollment(2, status="ACTIVA", end_date=(TODAY + timedelta(days=10)).isoformat()),
            # Finalizada hace poco pero ya no ACTIVA: no debe contar como crítica.
            _enrollment(3, status="FINALIZADA", end_date=(TODAY + timedelta(days=1)).isoformat()),
        ],
    }

    result = data_service.kpis_generales(data)

    assert result["matriculas_criticas"] == 1


def test_ingresos_mensuales_splits_projected_and_collected_by_month():
    data = {
        "payments": [
            _payment(1, status="PAGADO", total="100.00", payment_date=TODAY.isoformat(), due_date=TODAY.isoformat()),
            _payment(2, status="PENDIENTE", total="50.00", due_date=TODAY.isoformat()),
        ],
    }

    result = data_service.ingresos_mensuales(data)

    assert len(result["meses"]) == 6
    # El mes actual es el último de la ventana de 6 meses.
    assert result["cobrado"][-1] == 100.00
    assert result["proyectado"][-1] == 150.00  # ambos pagos vencen este mes


def test_ingresos_mensuales_respects_custom_window_size():
    data = {
        "payments": [
            _payment(1, status="PAGADO", total="100.00", payment_date=TODAY.isoformat(), due_date=TODAY.isoformat()),
        ],
    }

    result = data_service.ingresos_mensuales(data, count=12)

    assert len(result["meses"]) == 12
    assert result["cobrado"][-1] == 100.00


def test_distribucion_academica_counts_students_per_program():
    data = {
        "enrollments": [
            _enrollment(1, diploma_name="Programación Web"),
            _enrollment(2, diploma_name="Programación Web"),
            _enrollment(3, diploma_name="Diseño Gráfico"),
        ],
    }

    result = data_service.distribucion_academica(data)

    programas = dict(zip(result["programas"], result["estudiantes"]))
    assert programas["Programación Web"] == 2
    assert programas["Diseño Gráfico"] == 1


def test_actividad_reciente_orders_by_date_and_respects_limit():
    data = {
        "payments": [
            _payment(1, enrollment_id=1, payment_date=(TODAY - timedelta(days=2)).isoformat()),
            _payment(2, enrollment_id=1, payment_date=TODAY.isoformat()),
            _payment(3, enrollment_id=1, payment_date=(TODAY - timedelta(days=1)).isoformat()),
        ],
        "enrollments": [_enrollment(1)],
    }

    result = data_service.actividad_reciente(data, limit=2)

    assert len(result) == 2
    assert result[0]["id"] == "PAG-0002"  # el más reciente primero
    assert result[1]["id"] == "PAG-0003"


def test_actividad_reciente_classifies_status():
    data = {
        "payments": [
            _payment(1, enrollment_id=1, status="PAGADO"),
            _payment(2, enrollment_id=1, status="PENDIENTE", due_date=(TODAY - timedelta(days=3)).isoformat()),
            _payment(3, enrollment_id=1, status="PENDIENTE", due_date=(TODAY + timedelta(days=3)).isoformat()),
        ],
        "enrollments": [_enrollment(1)],
    }

    result = {row["id"]: row for row in data_service.actividad_reciente(data)}

    assert result["PAG-0001"]["estado"] == "Pagado"
    assert result["PAG-0002"]["estado"] == "Vencido"
    assert result["PAG-0003"]["estado"] == "Pendiente"


def test_actividad_reciente_handles_missing_enrollment_gracefully():
    """Un pago cuya matrícula ya no existe (se borró) no debe romper el panel."""
    data = {
        "payments": [_payment(1, enrollment_id=999)],
        "enrollments": [],
    }

    result = data_service.actividad_reciente(data)

    assert result[0]["estudiante"] == "—"
    assert result[0]["programa"] == "—"
