from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime


class LiveFluxPoint(BaseModel):
    time: str
    time_tag: str
    soft: float
    hard: float


class LiveFlareEvent(BaseModel):
    id: int
    begin_time: Optional[str] = None
    max_time: Optional[str] = None
    end_time: Optional[str] = None
    begin_class: Optional[str] = None
    max_class: Optional[str] = None
    end_class: Optional[str] = None
    max_flux_wm2: float
    peak_intensity: Optional[str] = None
    satellite: int = 18
    duration_minutes: Optional[int] = None


class ActiveRegion(BaseModel):
    region_number: int
    location: str
    latitude: Optional[int] = None
    longitude: Optional[int] = None
    area_millionths: Optional[int] = None
    spot_class: Optional[str] = None
    magnetic_class: Optional[str] = None
    num_spots: Optional[int] = None
    c_probability_pct: int
    m_probability_pct: int
    x_probability_pct: int
    c_events: int
    m_events: int
    x_events: int
    observed_date: str
    intensity_score: float


class LiveSummaryResponse(BaseModel):
    data_source: str
    source_urls: List[str]
    last_update: str
    satellite: int
    current_flux: Dict[str, Any]
    current_class: str
    current_class_letter: str
    class_meaning: str
    activity_level: str
    flux_trend_pct_30min: float
    latest_flare: Optional[Dict[str, Any]] = None
    recent_flares_count_7d: int
    active_regions_count: int
    top_active_region: Optional[Dict[str, Any]] = None
    global_probabilities: Dict[str, Any]
    risk_level: str


class FluxHistoryResponse(BaseModel):
    points: List[LiveFluxPoint]
    hours: int
    data_source: str
    last_update: str
    thresholds: Dict[str, float]


class FlaresResponse(BaseModel):
    flares: List[LiveFlareEvent]
    data_source: str
    last_update: str


class ActiveRegionsResponse(BaseModel):
    regions: List[ActiveRegion]
    data_source: str
    last_update: str
    glossary: Dict[str, str]


class ExtendedNowcastResponse(BaseModel):
    current_flare_class: Optional[str] = None
    current_activity_level: Optional[str] = None
    probability_of_current_event: Optional[float] = None
    current_flux: Optional[float] = None
    shortwave_flux: Optional[float] = None
    c_class_probability_pct: Optional[float] = None
    m_class_probability_pct: Optional[float] = None
    x_class_probability_pct: Optional[float] = None
    expected_duration: Optional[str] = None
    affected_region: Optional[str] = None
    current_confidence: Optional[float] = None
    ai_explanation: Optional[str] = None
    risk_level: Optional[str] = None
    suggested_action: Optional[str] = None
    last_update: str
    data_source: str


class ExtendedForecastItem(BaseModel):
    id: int
    time_horizon: str
    hours_ahead: int
    flare_class: str
    probability: float
    c_class_chance_pct: float
    m_class_chance_pct: float
    x_class_chance_pct: float
    confidence: float
    expected_time: str
    prediction_interval: str
    model_used: str
    reasoning: str


class ExtendedForecastResponse(BaseModel):
    predictions: List[ExtendedForecastItem]
    last_updated: str
    data_source: str
    methodology: str


class SolarWindSummaryResponse(BaseModel):
    data_source: str
    source_urls: List[str]
    last_update: Optional[str] = None
    speed_km_s: Optional[float] = None
    density_p_cm3: Optional[float] = None
    temperature_k: Optional[float] = None
    bz_nt: Optional[float] = None
    bt_nt: Optional[float] = None
    bz_south_alert: bool = False
    kp_index: float = 0
    kp_activity: str
    kp_last_update: Optional[str] = None


class SolarWindPoint(BaseModel):
    time_tag: Optional[str] = None
    propagated_time_tag: Optional[str] = None
    speed_km_s: Optional[float] = None
    density_p_cm3: Optional[float] = None
    temperature_k: Optional[float] = None
    bx_nt: Optional[float] = None
    by_nt: Optional[float] = None
    bz_nt: Optional[float] = None
    bt_nt: Optional[float] = None


class SolarWindHistoryResponse(BaseModel):
    points: List[SolarWindPoint]
    data_source: str
    last_update: Optional[str] = None


class CMEEvent(BaseModel):
    id: Optional[str] = None
    start_time: Optional[str] = None
    speed_km_s: Optional[float] = None
    type: Optional[str] = None
    is_most_accurate: Optional[bool] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    half_angle_deg: Optional[float] = None
    earth_directed: bool = False
    note: Optional[str] = None
    link: Optional[str] = None
    arrival_estimate: Optional[Dict[str, Any]] = None


class CMESummaryResponse(BaseModel):
    data_source: str
    source_urls: List[str]
    last_checked: str
    window_days: int
    total_cmes: int
    earth_directed_count: int
    events: List[CMEEvent]
    note: Optional[str] = None
    api_key_mode: str


class ScaleDetail(BaseModel):
    scale: str
    text: str
    effect: str


class EarthImpactDay(BaseModel):
    label: str
    date: Optional[str] = None
    radio_blackout: ScaleDetail
    radiation_storm: ScaleDetail
    geomagnetic_storm: ScaleDetail


class EarthImpactResponse(BaseModel):
    data_source: str
    source_urls: List[str]
    last_update: str
    today: EarthImpactDay
    forecast: List[EarthImpactDay]
    overall_earth_effect: str
    max_scale_today: int


class SatellitePayload(BaseModel):
    code: str
    pradan_ids: List[str] = []
    name: str
    measures: str
    proxy_available: bool
    proxy_source: Optional[str] = None
    note: str
    archive_available: bool = False
    archive_file_count: int = 0
    archive_earliest: Optional[str] = None
    archive_latest: Optional[str] = None


class SatelliteRosterResponse(BaseModel):
    mission: str
    agency: str
    payload_count: int
    payloads: List[SatellitePayload]
    proxied_count: int
    archived_count: int = 0
    generated_at: str
    disclosure: str


class EnsemblePrediction(BaseModel):
    id: int
    time_horizon: str
    hours_ahead: int
    expected_time: str
    flare_class: str
    probability: float
    combined: Dict[str, float]
    models: Dict[str, Dict[str, float]]
    weights: Dict[str, float]


class EnsembleForecastResponse(BaseModel):
    predictions: List[EnsemblePrediction]
    last_updated: str
    data_source: str
    methodology: str
