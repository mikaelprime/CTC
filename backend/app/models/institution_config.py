from sqlalchemy import Column, Integer, Numeric, String
from app.database.base import Base


class InstitutionConfig(Base):
    """Políticas institucionales editables desde la app. Siempre hay una sola
    fila (id=1): antes esto vivía en un diccionario en memoria y se perdía
    cada vez que el backend se reiniciaba (algo frecuente en el free tier de
    Render, que duerme el servicio tras un rato sin tráfico)."""

    __tablename__ = "institution_config"

    id = Column(Integer, primary_key=True, default=1)
    institution_name = Column(String(150), nullable=False, default="CTC El Salvador")
    late_fee = Column(Numeric(10, 2), nullable=False, default=3.00)
    payment_cycle_days = Column(Integer, nullable=False, default=28)
    alert_days_before = Column(Integer, nullable=False, default=7)
