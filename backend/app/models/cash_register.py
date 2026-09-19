from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from app.database.base import Base

class CashRegister(Base):
    __tablename__ = "cash_registers"

    id = Column(Integer, primary_key=True, index=True)
    cashier_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Saldos
    initial_amount = Column(Float, default=0.0)      # Fondo inicial con el que abre caja
    system_expected_amount = Column(Float, default=0.0) # Lo que el sistema calcula que vendió
    real_physical_amount = Column(Float, default=0.0)   # Lo que el cajero contó físicamente
    difference = Column(Float, default=0.0)            # Sobrante (+) o Faltante (-)

    # Auditoría (Mejora solicitada)
    audit_explanation = Column(String, nullable=True)  # Justificación obligatoria si hay descuadre

    # Estados
    is_open = Column(Boolean, default=True)           # Estado de la caja diaria
    opened_at = Column(DateTime(timezone=True), server_default=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)