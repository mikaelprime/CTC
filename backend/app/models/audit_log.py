from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.base import Base


class AuditLog(Base):
    """Bitácora: quién hizo qué operación sensible y cuándo (cobros,
    anulaciones, cierres de caja, cambios de configuración, usuarios...).
    Solo se agregan filas; nunca se editan ni se borran."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(50), nullable=False, index=True)
    entity = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=True)
    detail = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    user = relationship("User")
