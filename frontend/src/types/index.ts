export interface NowcastData {
  current_flare_class?: string;
  current_activity_level?: string;
  probability_of_current_event?: number;
  current_flux?: number;
  shortwave_flux?: number;
  c_class_probability_pct?: number;
  m_class_probability_pct?: number;
  x_class_probability_pct?: number;
  expected_duration?: string;
  affected_region?: string;
  current_confidence?: number;
  ai_explanation?: string;
  risk_level?: string;
  suggested_action?: string;
  last_update?: string;
  data_source?: string;
}

export interface InstrumentObservation {
  soft_xray_flux?: number;
  hard_xray_flux?: number;
  energy_band?: string;
  current_class?: string;
  observation_time?: string;
  detector_health?: string;
  quality_flag?: string;
  instrument_status?: string;
  timestamp?: string;
}

export interface LatestData {
  solexs?: InstrumentObservation | null;
  hel1os?: InstrumentObservation | null;
  last_updated?: string;
  data_source?: string;
  class_meanings?: Record<string, string>;
}

export interface ForecastPrediction {
  id: number;
  time_horizon: string;
  hours_ahead?: number;
  flare_class: string;
  probability: number;
  c_class_chance_pct?: number;
  m_class_chance_pct?: number;
  x_class_chance_pct?: number;
  confidence: number;
  expected_time?: string;
  prediction_interval?: string;
  model_used?: string;
  reasoning?: string;
}

export interface AlertItem {
  id: number;
  timestamp: string;
  alert_level: 'INFO' | 'WARNING' | 'CRITICAL';
  alert_type: string;
  reason?: string;
  confidence?: number;
  acknowledged: boolean;
}

export interface SystemStatus {
  status: string;
  timestamp: string;
  services: Record<string, string>;
}

export interface FluxPoint {
  time: string;
  time_tag?: string;
  soft: number;
  hard: number;
}

export interface FluxHistory {
  points: FluxPoint[];
  hours: number;
  data_source: string;
  last_update: string;
  thresholds: Record<string, number>;
}

export interface LiveFlare {
  id: number;
  begin_time?: string;
  max_time?: string;
  end_time?: string;
  begin_class?: string;
  max_class?: string;
  end_class?: string;
  max_flux_wm2: number;
  peak_intensity?: string;
  duration_minutes?: number;
}

export interface ActiveRegion {
  region_number: number;
  location: string;
  latitude: number;
  longitude: number;
  area_millionths: number;
  spot_class?: string;
  magnetic_class?: string;
  num_spots: number;
  c_probability_pct: number;
  m_probability_pct: number;
  x_probability_pct: number;
  c_events: number;
  m_events: number;
  x_events: number;
  observed_date: string;
  intensity_score: number;
}

export interface LiveSummary {
  data_source: string;
  source_urls: string[];
  last_update: string;
  satellite: number;
  current_flux: {
    shortwave_0_05_0_4_nm_wm2: number;
    longwave_0_1_0_8_nm_wm2: number;
    background_wm2: number;
    shortwave_label: string;
    longwave_label: string;
  };
  current_class: string;
  current_class_letter: string;
  class_meaning: string;
  activity_level: string;
  flux_trend_pct_30min: number;
  latest_flare?: LiveFlare;
  recent_flares_count_7d: number;
  active_regions_count: number;
  top_active_region?: ActiveRegion;
  risk_level: string;
}

export interface Glossary {
  flare_classes: Record<string, string>;
  flux_thresholds_wm2: Record<string, number>;
  instruments: Record<string, string>;
  data_sources: string[];
}

export interface ModelMetric {
  name: string;
  value: number;
  target: number;
  unit: string;
}

export interface SolarWindSummary {
  data_source: string;
  source_urls: string[];
  last_update?: string;
  speed_km_s?: number;
  density_p_cm3?: number;
  temperature_k?: number;
  bz_nt?: number;
  bt_nt?: number;
  bz_south_alert: boolean;
  kp_index: number;
  kp_activity: string;
  kp_last_update?: string;
}

export interface SolarWindPoint {
  time_tag?: string;
  propagated_time_tag?: string;
  speed_km_s?: number;
  density_p_cm3?: number;
  temperature_k?: number;
  bx_nt?: number;
  by_nt?: number;
  bz_nt?: number;
  bt_nt?: number;
}

export interface SolarWindHistory {
  points: SolarWindPoint[];
  data_source: string;
  last_update?: string;
}

export interface CMEEvent {
  id?: string;
  start_time?: string;
  speed_km_s?: number;
  type?: string;
  is_most_accurate?: boolean;
  latitude?: number;
  longitude?: number;
  half_angle_deg?: number;
  earth_directed: boolean;
  note?: string;
  link?: string;
  arrival_estimate?: CMEArrivalEstimate;
}

export interface CMESummary {
  data_source: string;
  source_urls: string[];
  last_checked: string;
  window_days: number;
  total_cmes: number;
  earth_directed_count: number;
  events: CMEEvent[];
  note?: string;
  api_key_mode: string;
}

export interface ScaleDetail {
  scale: string;
  text: string;
  effect: string;
}

export interface EarthImpactDay {
  label: string;
  date?: string;
  radio_blackout: ScaleDetail;
  radiation_storm: ScaleDetail;
  geomagnetic_storm: ScaleDetail;
}

export interface EarthImpact {
  data_source: string;
  source_urls: string[];
  last_update: string;
  today: EarthImpactDay;
  forecast: EarthImpactDay[];
  overall_earth_effect: string;
  max_scale_today: number;
}

export interface SatellitePayload {
  code: string;
  pradan_ids: string[];
  name: string;
  measures: string;
  proxy_available: boolean;
  proxy_source?: string;
  note: string;
  archive_available: boolean;
  archive_file_count: number;
  archive_earliest?: string;
  archive_latest?: string;
}

export interface SatelliteRoster {
  mission: string;
  agency: string;
  payload_count: number;
  payloads: SatellitePayload[];
  proxied_count: number;
  archived_count: number;
  generated_at: string;
  disclosure: string;
}

export interface PradanFile {
  url: string;
  filename: string;
  instrument: string;
  start_time?: string;
  end_time?: string;
  size_kb?: string;
}

export interface PradanStatus {
  authenticated: boolean;
  error: string | null;
  files: {
    solexs_count?: number;
    hel1os_count?: number;
    solexs_latest?: PradanFile[];
    hel1os_latest?: PradanFile[];
  };
}

export interface PradanHistorySummary {
  count: number;
  earliest: string | null;
  latest: string | null;
  by_month: Record<string, number>;
}

export interface PradanHistoryInstrument {
  files: PradanFile[];
  summary: PradanHistorySummary;
}

export interface PradanHistory {
  authenticated: boolean;
  error: string | null;
  instruments: Record<string, PradanHistoryInstrument>;
}

export interface CMEArrivalEstimate {
  estimable: boolean;
  reason?: string;
  model?: string;
  inputs?: { cme_speed_km_s: number; ambient_solar_wind_speed_km_s: number; r0_km: number; target_distance_km: number };
  nominal?: { hours_after_launch: number; arrival_time: string };
  earliest_plausible?: { hours_after_launch: number; arrival_time: string };
  latest_plausible?: { hours_after_launch: number; arrival_time: string };
  uncertainty_note?: string;
}

export interface ModelVariantScore {
  flare_class: string;
  probability: number;
  c: number;
  m: number;
  x: number;
}

export interface EnsemblePrediction {
  id: number;
  time_horizon: string;
  hours_ahead: number;
  expected_time: string;
  flare_class: string;
  probability: number;
  combined: { c: number; m: number; x: number };
  single_model: ModelVariantScore;
  dual_model: ModelVariantScore;
  models: {
    noaa_official: { c: number; m: number; x: number };
    flux_trend: { c: number; m: number; x: number };
    historical_frequency: { c: number; m: number; x: number };
  };
  weights: { noaa_official: number; flux_trend: number; historical_frequency: number };
}

export interface EnsembleForecast {
  predictions: EnsemblePrediction[];
  last_updated: string;
  data_source: string;
  adaptive_weights_active: boolean;
  methodology: string;
}

export interface AssociatedFlare {
  flare_class?: string;
  flare_peak_time?: string;
  time_diff_minutes?: number;
}

export interface DonkiCrossCheck {
  donki_speed_km_s?: number;
  donki_start_time?: string;
  donki_link?: string;
  time_diff_hours?: number;
  speed_difference_pct?: number;
  note?: string;
}

export interface CMEIndicatorEvent {
  product_id: string;
  type: string;
  begin_time: string;
  velocity_km_s: number | null;
  issued: string;
  associated_flare?: AssociatedFlare;
  donki_cross_check?: DonkiCrossCheck;
  arrival_estimate?: CMEArrivalEstimate;
}

export interface CMEIndicators {
  data_source: string;
  source_urls: string[];
  window_days: number;
  count: number;
  events: CMEIndicatorEvent[];
}

export interface StormWatchDay {
  day: string;
  level: string;
}

export interface StormWatch {
  product_id: string;
  issued: string;
  peak_category: string;
  daily_forecast: StormWatchDay[];
  is_current: boolean;
}

export interface StormWatches {
  data_source: string;
  source_urls: string[];
  count: number;
  watches: StormWatch[];
  latest: StormWatch | null;
  latest_current: StormWatch | null;
  has_active_watch: boolean;
}

export interface PredictionAccuracyCategory {
  category: string;
  total_recorded: number;
  total_verified: number;
  total_pending: number;
  correct: number;
  accuracy_pct: number | null;
  recent: Record<string, any>[];
}

export interface BestFlareModel {
  model: 'single_model' | 'dual_model' | 'multi_model' | null;
  accuracy_pct: number | null;
  note: string;
}

export interface AllPredictionAccuracy {
  ensemble_flare: PredictionAccuracyCategory;
  single_model_flare: PredictionAccuracyCategory;
  dual_model_flare: PredictionAccuracyCategory;
  storm_watch: PredictionAccuracyCategory;
  cme_arrival: PredictionAccuracyCategory;
  best_flare_model: BestFlareModel;
}

export interface FlareAlert {
  id: string;
  flare_class: string;
  severity: 'Low' | 'Moderate' | 'High' | 'Severe' | 'Extreme';
  active_region: string | null;
  status: 'Increasing' | 'Decaying' | 'Ended';
  start_time: string | null;
  peak_time: string | null;
  end_time: string | null;
  peak_flux_wm2: number | null;
  duration_minutes: number | null;
  impact: string[];
  radio_scale: string;
  description: string;
}

export interface FlareAlertsSummary {
  total_flares_today: number;
  strongest_flare: string | null;
  current_activity_level: string;
  active_regions_count: number;
  latest_flare: string | null;
  radio_blackout_level: string;
}

export interface FlareAlertsResponse {
  alerts: FlareAlert[];
  ticker_alerts: FlareAlert[];
  summary: FlareAlertsSummary;
  last_updated: string;
  data_source: string;
  source_urls: string[];
}
