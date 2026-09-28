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

    # Comprobante al que pertenece la cuota y caja en la que entró el dinero.
    # Antes la caja sumaba "los pagos del cajero creados desde que abrió", y
    # una caja que quedaba abierta de un día para otro mezclaba cobros.
    # Nulos solo en pagos anteriores a este cambio.
    receipt_id = Column(Integer, ForeignKey("receipts.id"), nullable=True, index=True)
    cash_register_id = Column(Integer, ForeignKey("cash_registers.id"), nullable=True, index=True)

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

    receipt = relationship("Receipt", back_populates="payments")