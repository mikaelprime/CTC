from sqlalchemy import Column, Integer, String, Time, Boolean
from sqlalchemy.orm import relationship
from app.database.base import Base

class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(100), nullable=False)

    start_time = Column(Time, nullable=False)

    end_time = Column(Time, nullable=False)

    active = Column(Boolean, default=True)

    # Sin cascade delete a propósito: borrar un turno no debe arrastrar en
    # silencio las inscripciones (y pagos) de los estudiantes que lo cursan.
    # El service verifica esto explícitamente antes de borrar (mismo criterio
    # que Diploma).
    enrollments = relationship(
        "Enrollment",
        back_populates="schedule",
    )