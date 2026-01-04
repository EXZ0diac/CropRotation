from sqlalchemy import Column, Integer, Float, DateTime, String
from sqlalchemy.sql import func
from .database import Base


class Reading(Base):
    __tablename__ = "readings"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    np_n = Column(Float, nullable=True)
    np_p = Column(Float, nullable=True)
    np_k = Column(Float, nullable=True)

    ph = Column(Float, nullable=True)
    ec = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    temperature = Column(Float, nullable=True)

    raw = Column(String, nullable=True)
