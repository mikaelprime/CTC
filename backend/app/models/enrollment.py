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