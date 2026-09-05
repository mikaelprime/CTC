from fastapi import HTTPException
from app.repositories.student_repository import get_by_id as get_student_by_id
from app.repositories.diploma_repository import get_by_id as get_diploma_by_id
from app.repositories.schedule_repository import get_by_id as get_schedule_by_id
from sqlalchemy.orm import Session
from app.models.enrollment import Enrollment
from app.repositories.enrollment_repository import EnrollmentRepository

class EnrollmentService:

    @staticmethod
    def create(db: Session, data):

        # Validar fechas
        if data.start_date > data.end_date:
            raise HTTPException(
                status_code=400,
                detail="La fecha de inicio no puede ser posterior a la fecha de finalización"
            )

        # Validar estado
        estados_validos = ["ACTIVA", "FINALIZADA", "CANCELADA"]

        if data.status not in estados_validos:
            raise HTTPException(
                status_code=400,
                detail=f"Estado invalido. Estados permitidos: {', '.join(estados_validos)}"
            )

        # Validar estudiante
        student = get_student_by_id(db, data.student_id)

        if not student:
            raise HTTPException(
                status_code=404,
                detail="El estudiante no existe"
            )

        # Validar diploma
        diploma = get_diploma_by_id(db, data.diploma_id)

        if not diploma:
            raise HTTPException(
                status_code=404,
                detail="El diploma no existe"
            )

        # Validar horario
        schedule = get_schedule_by_id(db, data.schedule_id)

        if not schedule:
            raise HTTPException(
                status_code=404,
                detail="El horario no existe"
            )

        # Crear matricula
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