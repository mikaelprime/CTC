from sqlalchemy import Column, Integer, String, Time, Boolean
from app.database.base import Base

class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(100), nullable=False)

    start_time = Column(Time, nullable=False)

    end_time = Column(Time, nullable=False)

    active = Column(Boolean, default=True)