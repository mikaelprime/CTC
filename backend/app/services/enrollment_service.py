import calendar
from datetime import date
from typing import Any, List
from sqlalchemy.orm import Session, joinedload
from app.models.enrollment import Enrollment
from app.models.diploma import Diploma
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
    def create(db: Session, enrollment: Any) -> Any:
        data = enrollment.model_dump(exclude_unset=True)
        diploma = db.query(Diploma).filter(Diploma.id == data["diploma_id"]).first()
        if diploma is None:
            raise ValueError("El diplomado seleccionado no existe")

        start_date = data.get("start_date") or data["enrollment_date"]
        end_date = data.get("end_date") or EnrollmentService._add_months(
            start_date, diploma.duration_months
        )
        data.update(start_date=start_date, end_date=end_date)
        db_enrollment = Enrollment(**data)
        db.add(db_enrollment)
        db.commit()
        db.refresh(db_enrollment)
        EmailService.send_enrollment_confirmation(db_enrollment)
        return db_enrollment

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