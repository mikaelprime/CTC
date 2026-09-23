import calendar
from datetime import date
from decimal import Decimal
from typing import Any, List
from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload
from app.core.pricing import REGISTRATION_LABELS, REGISTRATION_TYPES, TUITION_PLANS
from app.models.enrollment import Enrollment
from app.models.diploma import Diploma
from app.models.payment import Payment
from app.services.email_service import EmailService

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
    def get_all(db: Session) -> List[Any]:
        return db.query(Enrollment).options(*_WITH_RELATIONS).all()

    @staticmethod
    def create(db: Session, enrollment: Any, cashier_id: int | None = None) -> Any:
        data = enrollment.model_dump(exclude_unset=True)
        diploma = db.query(Diploma).filter(Diploma.id == data["diploma_id"]).first()
        if diploma is None:
            raise ValueError("El diplomado seleccionado no existe")

        registration_type = data.get("registration_type", "COMPLETA")
        tuition_plan = data.get("tuition_plan", "GRUPAL")
        if registration_type not in REGISTRATION_TYPES:
            raise HTTPException(status_code=400, detail=f"Tipo de matrícula inválido: {registration_type}")
        if tuition_plan not in TUITION_PLANS:
            raise HTTPException(status_code=400, detail=f"Plan de colegiatura inválido: {tuition_plan}")

        start_date = data.get("start_date") or data["enrollment_date"]
        end_date = data.get("end_date") or EnrollmentService._add_months(
            start_date, diploma.duration_months
        )
        data.update(start_date=start_date, end_date=end_date)
        db_enrollment = Enrollment(**data)
        db.add(db_enrollment)
        db.commit()
        db.refresh(db_enrollment)

        EnrollmentService._charge_registration_fee(db, db_enrollment, registration_type, cashier_id)
        EmailService.send_enrollment_confirmation(db_enrollment)
        return db_enrollment

    @staticmethod
    def _charge_registration_fee(
        db: Session, enrollment: Enrollment, registration_type: str, cashier_id: int | None
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
            cash_received=amount,
            change=Decimal("0.00"),
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
        return (
            db.query(Enrollment)
            .options(*_WITH_RELATIONS)
            .filter(Enrollment.id == enrollment_id)
            .first()
        )

    @staticmethod
    def delete(db: Session, enrollment_id: int) -> Any:
        db_enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
        if db_enrollment:
            db.delete(db_enrollment)
            db.commit()
        return db_enrollment
