from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.base import Base

class Diploma(Base):
    __tablename__ = "diplomas"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(100), nullable=False, unique=True)

    description = Column(String(255))

    duration_months = Column(Integer, nullable=False)

    registration_fee = Column(Integer, nullable=False)

    monthly_fee = Column(Integer, nullable=False)

    active = Column(Boolean, default=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Sin cascade delete a propósito: borrar un diplomado no debe arrastrar
    # en silencio las inscripciones (y pagos) de los estudiantes que lo
    # cursan. El service verifica esto explícitamente antes de borrar.
    enrollments = relationship(
        "Enrollment",
        back_populates="diploma",
    )