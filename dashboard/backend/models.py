from sqlalchemy import Column, Integer, Float, DateTime, String, JSON
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


class SoilEntry(Base):
    __tablename__ = "soil_entries"

    id = Column(Integer, primary_key=True, index=True)
    label = Column(String, nullable=True)
    n = Column(Float)
    p = Column(Float)
    k = Column(Float)
    ph = Column(Float)
    moisture = Column(Float)
    temperature = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class PlantHistory(Base):
    __tablename__ = "plant_history"

    id = Column(Integer, primary_key=True, index=True)
    previous_plant = Column(String, nullable=True)
    next_plant = Column(String, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
