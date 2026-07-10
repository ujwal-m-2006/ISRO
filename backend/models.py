from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import ARRAY
from datetime import datetime
import pytz

# Import authentication models
from .auth import User

Base = declarative_base()

class SoLEXSObservation(Base):
    __tablename__ = "solexs_observations"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    soft_xray_flux = Column(Float, nullable=True)  # in W/m²
    energy_spectrum = Column(ARRAY(Float), nullable=True)  # array of energy bins
    photon_count = Column(Integer, nullable=True)
    temperature = Column(Float, nullable=True)  # in MK
    observation_time = Column(DateTime(timezone=True), nullable=True)
    detector_health = Column(String, nullable=True)
    quality_flag = Column(String, nullable=True)  # 'good', 'warning', 'bad'
    instrument_status = Column(String, nullable=True)
    source = Column(String, nullable=True, default="PRADAN")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC))


class HEL1OSObservation(Base):
    __tablename__ = "hel1os_observations"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    hard_xray_flux = Column(Float, nullable=True)  # in W/m²
    energy_distribution = Column(ARRAY(Float), nullable=True)  # array of energy bins
    detector_count = Column(Integer, nullable=True)
    peak_energy = Column(Float, nullable=True)  # in keV
    observation_time = Column(DateTime(timezone=True), nullable=True)
    detector_health = Column(String, nullable=True)
    quality_flag = Column(String, nullable=True)  # 'good', 'warning', 'bad'
    instrument_status = Column(String, nullable=True)
    source = Column(String, nullable=True, default="PRADAN")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC))


class Prediction(Base):
    __tablename__ = "predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    prediction_type = Column(String, nullable=False)  # 'nowcast' or 'forecast'
    time_horizon = Column(String, nullable=True)  # '15min', '30min', '1hr', etc.
    flare_class = Column(String, nullable=True)  # 'A', 'B', 'C', 'M', 'X'
    probability = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)
    expected_time = Column(DateTime(timezone=True), nullable=True)
    prediction_interval = Column(String, nullable=True)  # '15-30min', '1-2hr', etc.
    model_used = Column(String, nullable=True)
    reasoning = Column(String, nullable=True)
    source = Column(String, nullable=True, default="AI_MODEL")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC))


class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    alert_level = Column(String, nullable=False)  # 'INFO', 'WARNING', 'CRITICAL'
    alert_type = Column(String, nullable=False)  # 'M_CLASS_EXCEEDED', 'X_CLASS_EXCEEDED', etc.
    reason = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    source = Column(String, nullable=True)
    acknowledged = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC))


class InstrumentStatus(Base):
    __tablename__ = "instrument_status"
    
    id = Column(Integer, primary_key=True, index=True)
    instrument_name = Column(String, nullable=False)  # 'SoLEXS', 'HEL1OS'
    status = Column(String, nullable=False)  # 'online', 'offline', 'degraded'
    last_updated = Column(DateTime(timezone=True), nullable=False)
    health_score = Column(Float, nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC))