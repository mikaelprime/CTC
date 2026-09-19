from sqlalchemy import Column, Integer, String, Date
from sqlalchemy.orm import relationship
from app.database.base import Base

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    age = Column(Integer, nullable=True)
    birth_date = Column(Date, nullable=True)
    dui = Column(String, nullable=True)
    address = Column(String, nullable=True)
    email = Column(String, nullable=True)
    contact_phone = Column(String, nullable=True)
    schooling = Column(String, nullable=True)

    # Datos del Responsable
    responsible_name = Column(String, nullable=True)
    responsible_dui = Column(String, nullable=True)
    responsible_kinship = Column(String, nullable=True)
    responsible_email = Column(String, nullable=True)
    responsible_whatsapp = Column(String, nullable=True)

    # RELACIÓN QUE FALTABA Y QUE CAUSABA EL ERROR:
    enrollments = relationship("Enrollment", back_populates="student")