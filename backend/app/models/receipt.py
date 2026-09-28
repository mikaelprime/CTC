from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.base import Base


class Receipt(Base):
    """Comprobante de un cobro (matrícula o colegiatura).

    Su `id` es el número correlativo que se imprime en el ticket (R-000123):
    lo genera la secuencia de la base de datos, así que dos cajeros cobrando
    al mismo tiempo nunca reciben el mismo número. Un cobro de varios meses
    es un solo comprobante con varias cuotas (payments). El efectivo recibido
    y el cambio son del cobro completo, no de cada cuota.
    """

    __tablename__ = "receipts"

    id = Column(Integer, primary_key=True, index=True)
    enrollment_id = Column(Integer, ForeignKey("enrollments.id"), nullable=False)
    cashier_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    cash_register_id = Column(Integer, ForeignKey("cash_registers.id"), nullable=True)

    kind = Column(String(20), nullable=False)  # MATRICULA / COLEGIATURA
    payment_type = Column(String(30), nullable=False)
    total = Column(Numeric(10, 2), nullable=False)
    cash_received = Column(Numeric(10, 2), nullable=False)
    change = Column(Numeric(10, 2), nullable=False)

    # EMITIDO / ANULADO. Un comprobante se anula completo, nunca se borra.
    status = Column(String(20), nullable=False, default="EMITIDO")
    void_reason = Column(String(200), nullable=True)

    issued_at = Column(DateTime(timezone=True), server_default=func.now())

    payments = relationship("Payment", back_populates="receipt")
    enrollment = relationship("Enrollment")
    cashier = relationship("User")

    @property
    def number(self) -> str:
        return f"R-{self.id:06d}"
