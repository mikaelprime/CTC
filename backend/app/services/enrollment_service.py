from sqlalchemy.orm import Session
from app.models.enrollment import Enrollment
from app.repositories.enrollment_repository import EnrollmentRepository

class EnrollmentService:

    @staticmethod
    def create(db: Session, data):
        enrollment = Enrollment(**data.model_dump())
        return EnrollmentRepository.create(db, enrollment)

    @staticmethod
    def get_all(db: Session):
        return EnrollmentRepository.get_all(db)

    @staticmethod
    def get_by_id(db: Session, enrollment_id: int):
        return EnrollmentRepository.get_by_id(db, enrollment_id)

    @staticmethod
    def delete(db: Session, enrollment_id: int):
        enrollment = EnrollmentRepository.get_by_id(db, enrollment_id)

        if enrollment:
            EnrollmentRepository.delete(db, enrollment)

        return enrollment