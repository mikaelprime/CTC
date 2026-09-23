import calendar
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, List
from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload
from app.core.pricing import REGISTRATION_LABELS, REGISTRATION_TYPES, TUITION_PLANS
from app.models.enrollment import Enrollment
from app.models.diploma import Diploma
from app.models.payment import Payment
from app.models.schedule import Schedule
from app.models.student import Student
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

    # --- MÉTODOS CRUD QUE FALTABAN ---

    @staticmethod
    def _with_next_payment(db: Session, enrollments: List[Enrollment]) -> List[Enrollment]:
        # Recalcula ACTIVA/PENDIENTE y adjunta el próximo vencimiento real
        # (lo expone EnrollmentResponse.next_payment_date).
        due_dates = PaymentService.refresh_enrollment_statuses(db, enrollments)
        for enrollment in enrollments:
            enrollment.next_payment_date = due_dates.get(enrollment.id)
        return enrollments

    @staticmethod
    def get_all(db: Session) -> List[Any]:
        enrollments = db.query(Enrollment).options(*_WITH_RELATIONS).all()
        return EnrollmentService._with_next_payment(db, enrollments)

    @staticmethod
    def create(db: Session, enrollment: Any, cashier_id: int | None = None) -> Any:
        data = enrollment.model_dump(exclude_unset=True)
        cash_received = data.pop("cash_received", None)
        # El estado lo maneja el sistema (ACTIVA/PENDIENTE/ANULADA), no el cliente.
        data["status"] = "ACTIVA"
        diploma = db.query(Diploma).filter(Diploma.id == data["diploma_id"]).first()
        if diploma is None:
            raise ValueError("El diplomado seleccionado no existe")
        if db.query(Student.id).filter(Student.id == data["student_id"]).first() is None:
            raise ValueError("El estudiante seleccionado no existe")
        if db.query(Schedule.id).filter(Schedule.id == data["schedule_id"]).first() is None:
            raise ValueError("El horario seleccionado no existe")

        registration_type = data.get("registration_type", "COMPLETA")
        tuition_plan = data.get("tuition_plan", "GRUPAL")
        if registration_type not in REGISTRATION_TYPES:
            raise HTTPException(status_code=400, detail=f"Tipo de matrícula inválido: {registration_type}")
        if tuition_plan not in TUITION_PLANS:
            raise HTTPException(status_code=400, detail=f"Plan de colegiatura inválido: {tuition_plan}")

        duplicate = db.query(Enrollment.id).filter(
            Enrollment.student_id == data["student_id"],
            Enrollment.diploma_id == data["diploma_id"],
            Enrollment.status.in_(("ACTIVA", "PENDIENTE")),
        ).first()
        if duplicate:
            raise HTTPException(
                status_code=409,
                detail=f"El estudiante ya tiene una matrícula vigente en este programa (#{duplicate.id})",
            )

        fee = REGISTRATION_TYPES[registration_type]
        if cash_received is None:
            cash_received = fee
        if cash_received < fee:
            raise HTTPException(
                status_code=400, detail=f"El efectivo debe ser de al menos ${fee:.2f}"
            )

        start_date = data.get("start_date") or data["enrollment_date"]
        end_date = data.get("end_date") or EnrollmentService._add_months(
            start_date, diploma.duration_months
        )
        data.update(start_date=start_date, end_date=end_date)
        db_enrollment = Enrollment(**data)
        db.add(db_enrollment)
        db.commit()
        db.refresh(db_enrollment)

        EnrollmentService._charge_registration_fee(
            db, db_enrollment, registration_type, cashier_id, cash_received
        )
        EnrollmentService._with_next_payment(db, [db_enrollment])
        # Datos para el ticket de matrícula (no son columnas del modelo).
        db_enrollment.registration_fee = fee
        db_enrollment.cash_received = cash_received
        db_enrollment.change = cash_received - fee
        EmailService.send_enrollment_confirmation(
            db_enrollment, fee=fee, cash_received=cash_received, change=cash_received - fee
        )
        return db_enrollment

    @staticmethod
    def _charge_registration_fee(
        db: Session,
        enrollment: Enrollment,
        registration_type: str,
        cashier_id: int | None,
        cash_received: Decimal,
    ) -> None:
        amount = REGISTRATION_TYPES[registration_type]
        if amount <= 0:
            return  # Matrícula gratis: no hay cobro que registrar.
        payment = Payment(
            enrollment_id=enrollment.id,
            cashier_id=cashier_id,
            payment_date=enrollment.enrollment_date,
            due_date=enrollment.enrollment_date,
            amount=amount,
            surcharge=Decimal("0.00"),
            total=amount,
            payment_type="Efectivo",
            status="PAGADO",
            kind="MATRICULA",
            cash_received=cash_received,
            change=cash_received - amount,
            observations=REGISTRATION_LABELS[registration_type],
        )
        db.add(payment)
        db.commit()

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
            EnrollmentService._with_next_payment(db, [enrollment])
        return enrollment

    @staticmethod
    def delete(db: Session, enrollment_id: int) -> Any:
        db_enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
        if db_enrollment:
            # Borrar la matrícula borraba en cascada sus pagos cobrados y
            # descuadraba arqueos de caja ya cerrados. Con dinero registrado
            # solo se puede anular (queda el historial de pagos).
            has_paid = db.query(Payment.id).filter(
                Payment.enrollment_id == enrollment_id, Payment.status == "PAGADO"
            ).first()
            if has_paid:
                raise HTTPException(
                    status_code=409,
                    detail="No se puede eliminar: la matrícula tiene pagos cobrados. Anúlala en su lugar.",
                )
            db.delete(db_enrollment)
            db.commit()
        return db_enrollment

    @staticmethod
    def update(db: Session, enrollment_id: int, changes: dict) -> Any:
        db_enrollment = EnrollmentService.get_by_id(db, enrollment_id)
        if db_enrollment is None:
            return None
        if db_enrollment.status == "ANULADA":
            raise HTTPException(status_code=400, detail="La inscripción está anulada; no se puede editar")

        if changes.get("schedule_id") is not None:
            if db.query(Schedule.id).filter(Schedule.id == changes["schedule_id"]).first() is None:
                raise HTTPException(status_code=404, detail="El horario seleccionado no existe")
            db_enrollment.schedule_id = changes["schedule_id"]

        if changes.get("tuition_plan") is not None:
            if changes["tuition_plan"] not in TUITION_PLANS:
                raise HTTPException(status_code=400, detail=f"Plan de colegiatura inválido: {changes['tuition_plan']}")
            # Solo afecta cobros futuros: las cuotas ya pagadas guardan su monto.
            db_enrollment.tuition_plan = changes["tuition_plan"]

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

        if "observations" in changes:
            db_enrollment.observations = changes["observations"]

        db.commit()
        return EnrollmentService.get_by_id(db, enrollment_id)

    @staticmethod
    def cancel(db: Session, enrollment_id: int, reason: str) -> Any:
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
        db.query(Payment).filter(
            Payment.enrollment_id == enrollment_id, Payment.status == "PENDIENTE"
        ).delete(synchronize_session=False)
        db.commit()
        db.refresh(db_enrollment)
        db_enrollment.next_payment_date = None
        return db_enrollment
