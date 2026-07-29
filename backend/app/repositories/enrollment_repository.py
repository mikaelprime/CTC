from sqlalchemy.orm import Session
from app.models.enrollment import Enrollment
from sqlalchemy.orm import joinedload

class EnrollmentRepository:

    @staticmethod
    def create(db: Session, enrollment: Enrollment):
        db.add(enrollment)
        db.commit()
        db.refresh(enrollment)
        return enrollment

    @staticmethod
    def get_all(db: Session):
        return (
            db.query(Enrollment)
            .options(
            joinedload(Enrollment.student),
            joinedload(Enrollment.diploma),
            joinedload(Enrollment.schedule),
        )
        .all()
    )

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

    @staticmethod
    def delete(db: Session, enrollment: Enrollment):
        db.delete(enrollment)
        db.commit()