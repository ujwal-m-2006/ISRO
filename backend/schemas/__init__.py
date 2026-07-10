from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

from .auth import User, UserCreate, UserLogin, Token, TokenData


class BaseSchema(BaseModel):
    class Config:
        from_attributes = True


class SoLEXSObservationBase(BaseSchema):
    timestamp: datetime
    soft_xray_flux: Optional[float] = None
    energy_spectrum: Optional[List[float]] = None
    photon_count: Optional[int] = None
    temperature: Optional[float] = None
    observation_time: Optional[datetime] = None
    detector_health: Optional[str] = None
    quality_flag: Optional[str] = None
    instrument_status: Optional[str] = None
    source: Optional[str] = "PRADAN"


class SoLEXSObservationCreate(SoLEXSObservationBase):
    pass


class SoLEXSObservation(SoLEXSObservationBase):
    id: int
    created_at: datetime


class HEL1OSObservationBase(BaseSchema):
    timestamp: datetime
    hard_xray_flux: Optional[float] = None
    energy_distribution: Optional[List[float]] = None
    detector_count: Optional[int] = None
    peak_energy: Optional[float] = None
    observation_time: Optional[datetime] = None
    detector_health: Optional[str] = None
    quality_flag: Optional[str] = None
    instrument_status: Optional[str] = None
    source: Optional[str] = "PRADAN"


class HEL1OSObservationCreate(HEL1OSObservationBase):
    pass


class HEL1OSObservation(HEL1OSObservationBase):
    id: int
    created_at: datetime


class PredictionBase(BaseSchema):
    timestamp: datetime
    prediction_type: str
    time_horizon: Optional[str] = None
    flare_class: Optional[str] = None
    probability: Optional[float] = None
    confidence: Optional[float] = None
    expected_time: Optional[datetime] = None
    prediction_interval: Optional[str] = None
    model_used: Optional[str] = None
    reasoning: Optional[str] = None
    source: Optional[str] = "AI_MODEL"


class PredictionCreate(PredictionBase):
    pass


class Prediction(PredictionBase):
    id: int
    created_at: datetime


class AlertBase(BaseSchema):
    timestamp: datetime
    alert_level: str
    alert_type: str
    reason: Optional[str] = None
    confidence: Optional[float] = None
    source: Optional[str] = None
    acknowledged: bool = False


class AlertCreate(AlertBase):
    pass


class Alert(AlertBase):
    id: int
    created_at: datetime


class InstrumentStatusBase(BaseSchema):
    instrument_name: str
    status: str
    last_updated: datetime
    health_score: Optional[float] = None
    details: Optional[Dict[str, Any]] = None


class InstrumentStatusCreate(InstrumentStatusBase):
    pass


class InstrumentStatus(InstrumentStatusBase):
    id: int
    created_at: datetime


class LatestDataResponse(BaseSchema):
    solexs: Optional[SoLEXSObservation] = None
    hel1os: Optional[HEL1OSObservation] = None
    last_updated: datetime
    data_source: str


class HistoricalDataResponse(BaseSchema):
    data: List[Dict[str, Any]]
    total: int
    page: int
    pages: int


class NowcastResponse(BaseSchema):
    current_flare_class: Optional[str] = None
    current_activity_level: Optional[str] = None
    probability_of_current_event: Optional[float] = None
    current_flux: Optional[float] = None
    expected_peak: Optional[float] = None
    expected_duration: Optional[str] = None
    affected_region: Optional[str] = None
    current_confidence: Optional[float] = None
    ai_explanation: Optional[str] = None
    risk_level: Optional[str] = None
    suggested_action: Optional[str] = None
    last_update: datetime


class ForecastResponse(BaseSchema):
    predictions: List[Prediction]
    last_updated: datetime


class AlertResponse(BaseSchema):
    alerts: List[Alert]
    total_active: int
    last_checked: datetime


class StatusResponse(BaseSchema):
    status: str
    timestamp: datetime
    services: Dict[str, str]


class HealthCheckResponse(BaseSchema):
    status: str
    message: str
    timestamp: datetime
