from sqlalchemy import Column, Integer, ForeignKey, Date, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.base import Base

class Enrollment(Base):
    __tablename__ = "enrollments"

    id = Column(Integer, primary_key=True, index=True)

    student_id = Column(
        Integer,
        ForeignKey("students.id"),
        nullable=False
    )

    diploma_id = Column(
        Integer,
        ForeignKey("diplomas.id"),
        nullable=False
    )

    schedule_id = Column(
        Integer,
        ForeignKey("schedules.id"),
        nullable=False
    )

    enrollment_date = Column(
        Date,
        nullable=False
    )

    status = Column(
        String(30),
        default="ACTIVA"
    )

    # Tipo de matrícula (COMPLETA $20 / PROMO $10 / GRATIS $0) y plan de
    # colegiatura (GRUPAL $25 / PRIVADO $55 / ONLINE $70) elegidos al
    # inscribir. Los montos viven en app.core.pricing, no en la BD: son
    # fijos institucionales, no configurables por diplomado.
    registration_type = Column(String(20), nullable=False, server_default="COMPLETA")

    tuition_plan = Column(String(20), nullable=False, server_default="GRUPAL")

    observations = Column(
        String(500),
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    start_date = Column(Date, nullable=False)

    end_date = Column(Date, nullable=False)

    # Evita reenviar el mismo recordatorio de "vence en 7 días" cada vez que
    # alguien inicia sesión ese mismo día: se guarda la fecha de vencimiento
    # para la que ya se avisó, y solo se vuelve a avisar cuando cambia.
    last_reminder_due_date = Column(Date, nullable=True)

    student = relationship(
        "Student",
        back_populates="enrollments"
    )

    diploma = relationship(
        "Diploma",
        back_populates="enrollments"
    )

    schedule = relationship(
        "Schedule",
        back_populates="enrollments"
    )

    payments = relationship(
        "Payment",
        back_populates="enrollment",
        cascade="all, delete-orphan"
    )