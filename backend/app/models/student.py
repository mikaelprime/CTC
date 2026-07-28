from sqlalchemy import Column, Integer, String, Date, Boolean, DateTime
from sqlalchemy.sql import func
from app.database.base import Base

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)

    full_name = Column(String(150), nullable=False)

    birth_date = Column(Date, nullable=False)

    email = Column(String(120), unique=True, nullable=False)

    phone = Column(String(15), nullable=False)

    address = Column(String(255), nullable=False)

    education_level = Column(String(50), nullable=False)

    dui = Column(String(10), unique=True, nullable=True)

    guardian_name = Column(String(150), nullable=False)

    guardian_dui = Column(String(10), nullable=False)

    guardian_relationship = Column(String(50), nullable=False)

    guardian_email = Column(String(120), nullable=True)

    guardian_whatsapp = Column(String(15), nullable=True)

    observations = Column(String(500), nullable=True)

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )