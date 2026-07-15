import type {
  ActiveRegion,
  AlertItem,
  AllPredictionAccuracy,
  CMEIndicators,
  CMESummary,
  EarthImpact,
  EnsembleForecast,
  FlareAlertsResponse,
  FluxHistory,
  ForecastPrediction,
  Glossary,
  LatestData,
  LiveFlare,
  LiveSummary,
  NowcastData,
  PradanHistory,
  PradanStatus,
  SatelliteRoster,
  SolarWindHistory,
  SolarWindSummary,
  StormWatches,
  SystemStatus,
  TrainedModelResponse,
} from '../types';

const REFRESH_MS = 60_000;

// Relative paths work in local dev via Vite's proxy (vite.config.ts) since
// frontend and backend are on different ports there. In production there's
// no dev proxy, so this needs to point at wherever the backend actually
// lives — set VITE_API_BASE_URL at build time (e.g. in Vercel's project env
// vars) to your backend's real URL. Left unset, it stays relative, which
// only works if the backend is served from the same domain.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';

async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${url}`);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json() as Promise<T>;
}

export const api = {
  getLiveSummary: () => fetchJson<LiveSummary>('/api/v1/live/summary'),
  getFluxHistory: (hours = 6) => fetchJson<FluxHistory>(`/api/v1/live/flux?hours=${hours}`),
  getRecentFlares: () => fetchJson<{ flares: LiveFlare[]; data_source: string; last_update: string }>('/api/v1/live/flares'),
  getActiveRegions: () => fetchJson<{ regions: ActiveRegion[]; data_source: string; last_update: string; glossary: Record<string, string> }>('/api/v1/live/regions'),
  getNowcast: () => fetchJson<NowcastData>('/api/v1/nowcast'),
  getLatestData: () => fetchJson<LatestData>('/api/v1/latest'),
  getStatus: () => fetchJson<SystemStatus>('/api/v1/status'),
  getForecasts: () => fetchJson<{ predictions: ForecastPrediction[]; data_source: string; methodology: string; last_updated: string }>('/api/v1/forecast').then((r) => r),
  getAlerts: () => fetchJson<{ alerts: AlertItem[]; total_active: number; last_checked: string; data_source: string }>('/api/v1/alerts'),
  getGlossary: () => fetchJson<Glossary>('/api/v1/glossary'),
  getJobStatus: () => fetchJson<{ jobs: Record<string, { last_run: string; success: boolean; detail: string; duration_ms: number }>; snapshots: { key: string; saved_at: string }[] }>('/api/v1/jobs/status'),
  getSolarWind: () => fetchJson<SolarWindSummary>('/api/v1/space-weather/solar-wind'),
  getSolarWindHistory: () => fetchJson<SolarWindHistory>('/api/v1/space-weather/solar-wind/history'),
  getCME: () => fetchJson<CMESummary>('/api/v1/space-weather/cme'),
  getEarthImpact: () => fetchJson<EarthImpact>('/api/v1/space-weather/earth-impact'),
  getSatelliteRoster: () => fetchJson<SatelliteRoster>('/api/v1/satellites'),
  getPradanStatus: () => fetchJson<PradanStatus>('/api/v1/pradan/status'),
  getPradanHistory: () => fetchJson<PradanHistory>('/api/v1/pradan/history'),
  getEnsembleForecast: () => fetchJson<EnsembleForecast>('/api/v1/forecast/ensemble'),
  getCMEIndicators: (days = 7) => fetchJson<CMEIndicators>(`/api/v1/space-weather/cme-indicators?days=${days}`),
  getStormWatches: () => fetchJson<StormWatches>('/api/v1/space-weather/storm-watches'),
  getPredictionAccuracy: () => fetchJson<AllPredictionAccuracy>('/api/v1/predictions/accuracy'),
  getFlareAlerts: () => fetchJson<FlareAlertsResponse>('/api/v1/flare-alerts'),
  getTrainedModelPredictions: () => fetchJson<TrainedModelResponse>('/api/v1/predictions/trained-model'),
};

export const FLARE_ALERTS_REFRESH_MS = 5 * 60_000;

export const LIVE_REFRESH_MS = REFRESH_MS;

export function formatFlux(value?: number) {
  if (value == null || Number.isNaN(value)) return '—';
  return `${value.toExponential(2)} W/m²`;
}

export function formatPct(value?: number) {
  if (value == null) return '—';
  return value <= 1 ? `${(value * 100).toFixed(1)}%` : `${value.toFixed(1)}%`;
}

export function formatTime(iso?: string) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString();
}

export function classColor(flareClass?: string) {
  const letter = flareClass?.[0]?.toUpperCase();
  switch (letter) {
    case 'X': return 'text-red-400 bg-red-500/20 border-red-500/40';
    case 'M': return 'text-orange-400 bg-orange-500/20 border-orange-500/40';
    case 'C': return 'text-yellow-300 bg-yellow-500/20 border-yellow-500/40';
    case 'B': return 'text-green-400 bg-green-500/20 border-green-500/40';
    default: return 'text-space-cyan bg-space-blue/20 border-space-blue/40';
  }
}
