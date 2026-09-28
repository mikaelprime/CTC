import calendar
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, List

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.core.pricing import REGISTRATION_LABELS, registration_fee, tuition_fee
from app.models.diploma import Diploma
from app.models.enrollment import Enrollment
from app.models.payment import Payment
from app.models.receipt import Receipt
from app.models.schedule import Schedule
from app.models.student import Student
from app.services import audit_service, student_service
from app.services.cashier_service import CashierService
from app.services.email_service import EmailService
from app.services.payment_service import PaymentService

# `EnrollmentResponse` serializa student/diploma/schedule anidados. Sin
# joinedload, SQLAlchemy carga cada relación de forma perezosa: con 20-30
# matrículas eso son cientos de consultas individuales (problema N+1) y el
# endpoint tarda varios segundos en vez de decenas de milisegundos.
_WITH_RELATIONS = (
    joinedload(Enrollment.student),
    joinedload(Enrollment.diploma),
    joinedload(Enrollment.schedule),
)


class EnrollmentService:

    @staticmethod
    def _with_installments(db: Session, enrollments: List[Enrollment]) -> List[Enrollment]:
        # Recalcula ACTIVA/PENDIENTE/FINALIZADA y adjunta la situación de
        # colegiaturas (la expone EnrollmentResponse).
        statuses = PaymentService.refresh_enrollment_statuses(db, enrollments)
        for enrollment in enrollments:
            info = statuses[enrollment.id]
            anulada = enrollment.status == "ANULADA"
            enrollment.next_payment_date = None if anulada else info.next_due
            enrollment.installments_total = info.total
            enrollment.installments_paid = info.paid
            enrollment.overdue_installments = 0 if anulada else info.overdue
        return enrollments

    @staticmethod
    def get_all(db: Session) -> List[Any]:
        enrollments = db.query(Enrollment).options(*_WITH_RELATIONS).order_by(Enrollment.id.desc()).all()
        return EnrollmentService._with_installments(db, enrollments)

    @staticmethod
    def create(db: Session, data, user) -> Enrollment:
        """Registro de matrícula (PDF punto 1) en una sola transacción: el
        estudiante nuevo (si viene), la inscripción, el cobro de la matrícula
        con su comprobante y la bitácora. Si algo falla no queda nada a
        medias (antes podía quedar la inscripción sin su cobro)."""
        diploma = db.get(Diploma, data.diploma_id)
        if diploma is None:
            raise HTTPException(status_code=404, detail="El diplomado seleccionado no existe")
        if not diploma.active:
            raise HTTPException(status_code=400, detail="El diplomado está inactivo y no recibe inscripciones")
        schedule = db.get(Schedule, data.schedule_id)
        if schedule is None:
            raise HTTPException(status_code=404, detail="El horario seleccionado no existe")
        if not schedule.active:
            raise HTTPException(status_code=400, detail="El horario está inactivo y no recibe inscripciones")

        fee = registration_fee(db, data.registration_type)
        # Todo dinero recibido entra a una caja abierta (de quien cobra).
        register = CashierService.verify_active_box(db, user.id) if fee > 0 else None
        cash, change = (
            PaymentService._cash_and_change(data.payment_type, data.cash_received, fee)
            if fee > 0 else (Decimal("0.00"), Decimal("0.00"))
        )

        if data.student is not None:
            student = student_service.build_student(db, data.student.model_dump(), user)
        else:
            student = db.get(Student, data.student_id)
            if student is None:
                raise HTTPException(status_code=404, detail="El estudiante seleccionado no existe")

        duplicate = db.query(Enrollment.id).filter(
            Enrollment.student_id == student.id,
            Enrollment.diploma_id == diploma.id,
            Enrollment.status.in_(("ACTIVA", "PENDIENTE")),
        ).first()
        if duplicate:
            raise HTTPException(
                status_code=409,
                detail=f"El estudiante ya tiene una matrícula vigente en este programa (#{duplicate.id})",
            )

        enrollment = Enrollment(
            student_id=student.id,
            diploma_id=diploma.id,
            schedule_id=schedule.id,
            enrollment_date=data.enrollment_date,
            start_date=data.start_date,
            end_date=EnrollmentService._add_months(data.start_date, diploma.duration_months),
            status="ACTIVA",
            registration_type=data.registration_type,
            tuition_plan=data.tuition_plan,
            observations=data.observations,
        )
        db.add(enrollment)
        db.flush()

        receipt = None
        if fee > 0:
            receipt = Receipt(
                enrollment_id=enrollment.id,
                cashier_id=user.id,
                cash_register_id=register.id,
                kind="MATRICULA",
                payment_type=data.payment_type,
                total=fee,
                cash_received=cash,
                change=change,
                status="EMITIDO",
            )
            db.add(receipt)
            db.flush()
            db.add(Payment(
                enrollment_id=enrollment.id,
                receipt_id=receipt.id,
                cash_register_id=register.id,
                cashier_id=user.id,
                payment_date=data.enrollment_date,
                due_date=data.enrollment_date,
                amount=fee,
                surcharge=Decimal("0.00"),
                total=fee,
                payment_type=data.payment_type,
                status="PAGADO",
                kind="MATRICULA",
                cash_received=cash,
                change=change,
                observations=REGISTRATION_LABELS[data.registration_type],
            ))
        audit_service.record(
            db, user, "INSCRIPCION", "enrollment", enrollment.id,
            f"{student.full_name} · {diploma.name} · {REGISTRATION_LABELS[data.registration_type]}"
            + (f" · {receipt.number} ${fee:.2f}" if receipt else ""),
        )
        db.commit()

        enrollment = EnrollmentService.get_by_id(db, enrollment.id)
        # Datos para el ticket de matrícula (no son columnas del modelo).
        enrollment.registration_fee = fee
        enrollment.cash_received = cash
        enrollment.change = change
        if receipt is not None:
            db.refresh(receipt)
            enrollment.receipt_id = receipt.id
            enrollment.receipt_number = receipt.number
        EmailService.send_enrollment_confirmation(
            enrollment, tuition_fee(db, enrollment.tuition_plan), receipt
        )
        return enrollment

    @staticmethod
    def _add_months(base_date: date, months: int) -> date:
        month_index = base_date.month - 1 + months
        year = base_date.year + month_index // 12
        month = month_index % 12 + 1
        day = min(base_date.day, calendar.monthrange(year, month)[1])
        return date(year, month, day)

    @staticmethod
    def get_by_id(db: Session, enrollment_id: int) -> Any:
        enrollment = (
            db.query(Enrollment)
            .options(*_WITH_RELATIONS)
            .filter(Enrollment.id == enrollment_id)
            .first()
        )
        if enrollment:
            EnrollmentService._with_installments(db, [enrollment])
        return enrollment

    @staticmethod
    def delete(db: Session, enrollment_id: int, user) -> Any:
        db_enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
        if db_enrollment:
            # Con dinero registrado (aunque esté anulado) solo se puede
            # anular: los pagos y comprobantes son historial contable.
            has_money = db.query(Payment.id).filter(Payment.enrollment_id == enrollment_id).first()
            if has_money:
                raise HTTPException(
                    status_code=409,
                    detail="No se puede eliminar: la matrícula tiene pagos registrados. Anúlala en su lugar.",
                )
            audit_service.record(db, user, "ELIMINACION_INSCRIPCION", "enrollment", enrollment_id,
                                 f"Inscripción sin pagos del estudiante #{db_enrollment.student_id}")
            db.delete(db_enrollment)
            db.commit()
        return db_enrollment

    @staticmethod
    def update(db: Session, enrollment_id: int, changes: dict, user) -> Any:
        db_enrollment = EnrollmentService.get_by_id(db, enrollment_id)
        if db_enrollment is None:
            return None
        if db_enrollment.status == "ANULADA":
            raise HTTPException(status_code=400, detail="La inscripción está anulada; no se puede editar")
        described = []

        if changes.get("schedule_id") is not None and changes["schedule_id"] != db_enrollment.schedule_id:
            schedule = db.get(Schedule, changes["schedule_id"])
            if schedule is None:
                raise HTTPException(status_code=404, detail="El horario seleccionado no existe")
            db_enrollment.schedule_id = schedule.id
            described.append(f"horario → {schedule.name}")

        if changes.get("tuition_plan") is not None and changes["tuition_plan"] != db_enrollment.tuition_plan:
            # Solo afecta cobros futuros: las cuotas ya pagadas guardan su monto.
            db_enrollment.tuition_plan = changes["tuition_plan"]
            described.append(f"plan → {changes['tuition_plan']}")

        new_start = changes.get("start_date")
        if new_start is not None and new_start != db_enrollment.start_date:
            # La fecha de inicio ancla el ciclo de 28 días: una vez cobrada
            # la primera colegiatura, moverla desfasaría todas las cuotas.
            paid_tuition = db.query(Payment.id).filter(
                Payment.enrollment_id == enrollment_id,
                Payment.kind == "COLEGIATURA",
                Payment.status == "PAGADO",
            ).first()
            if paid_tuition:
                raise HTTPException(
                    status_code=409,
                    detail="No se puede cambiar la fecha de inicio: ya hay colegiaturas cobradas con el ciclo actual.",
                )
            if not (
                db_enrollment.enrollment_date - timedelta(days=90)
                <= new_start
                <= db_enrollment.enrollment_date + timedelta(days=365)
            ):
                raise HTTPException(
                    status_code=422,
                    detail="La fecha de inicio debe estar entre 90 días antes y un año después de la matrícula",
                )
            db_enrollment.start_date = new_start
            db_enrollment.end_date = EnrollmentService._add_months(new_start, db_enrollment.diploma.duration_months)
            db_enrollment.last_reminder_due_date = None
            described.append(f"inicio → {new_start:%d/%m/%Y}")

        if "observations" in changes and changes["observations"] != db_enrollment.observations:
            db_enrollment.observations = changes["observations"]
            described.append("observaciones")

        if described:
            audit_service.record(db, user, "EDICION_INSCRIPCION", "enrollment", enrollment_id, ", ".join(described))
        db.commit()
        return EnrollmentService.get_by_id(db, enrollment_id)

    @staticmethod
    def cancel(db: Session, enrollment_id: int, reason: str, user) -> Any:
        """Anula la matrícula sin borrar sus pagos: deja de generar cobros,
        recordatorios y estado PENDIENTE, pero el dinero cobrado sigue en los
        reportes de caja."""
        db_enrollment = EnrollmentService.get_by_id(db, enrollment_id)
        if db_enrollment is None:
            return None
        if db_enrollment.status == "ANULADA":
            raise HTTPException(status_code=400, detail="La matrícula ya está anulada")
        db_enrollment.status = "ANULADA"
        note = f"ANULADA: {reason}"
        db_enrollment.observations = (
            f"{db_enrollment.observations} | {note}" if db_enrollment.observations else note
        )[:500]
        # Cuotas PENDIENTE heredadas de versiones anteriores: nunca se cobraron.
        db.query(Payment).filter(
            Payment.enrollment_id == enrollment_id, Payment.status == "PENDIENTE"
        ).delete(synchronize_session=False)
        audit_service.record(db, user, "ANULACION_INSCRIPCION", "enrollment", enrollment_id, reason)
        db.commit()
        return EnrollmentService.get_by_id(db, enrollment_id)
