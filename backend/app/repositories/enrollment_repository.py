from sqlalchemy.orm import Session, joinedload
from app.models.enrollment import Enrollment


class EnrollmentRepository:
    @staticmethod
    def get_by_id(db: Session, enrollment_id: int):
        return (
            db.query(Enrollment)
            .options(
                joinedload(Enrollment.student),
                joinedload(Enrollment.diploma),
                joinedload(Enrollment.schedule),
            )
            .filter(Enrollment.id == enrollment_id)
            .first()
        )
