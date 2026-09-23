from sqlalchemy import Column, Integer, ForeignKey, Date, DateTime, String, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.base import Base

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)

    enrollment_id = Column(
        Integer,
        ForeignKey("enrollments.id"),
        nullable=False
    )

    cashier_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    payment_date = Column(
        Date,
        nullable=False
    )

    due_date = Column(
        Date,
        nullable=False
    )

    amount = Column(
        Numeric(10, 2),
        nullable=False
    )

    surcharge = Column(
        Numeric(10, 2),
        default=0
    )

    total = Column(
        Numeric(10, 2),
        nullable=False
    )

    payment_type = Column(
        String(30),
        nullable=False
    )

    status = Column(
        String(30),
        default="PENDIENTE"
    )

    # Distingue el cobro único de matrícula (MATRICULA) del ciclo recurrente
    # de colegiatura cada 28 días (COLEGIATURA). Necesario para que
    # get_last_by_enrollment() no confunda la matrícula con "la última
    # cuota de colegiatura" al calcular el próximo vencimiento.
    kind = Column(String(20), nullable=False, server_default="COLEGIATURA")

    cash_received = Column(
        Numeric(10, 2),
        nullable=True
    )

    change = Column(
        Numeric(10, 2),
        nullable=True
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

    enrollment = relationship(
        "Enrollment",
        back_populates="payments"
    )