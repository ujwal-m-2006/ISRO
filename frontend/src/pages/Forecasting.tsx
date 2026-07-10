import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { ForecastProbabilityChart } from '../components/charts';
import { DataSourceBadge, FlareClassBadge, MeaningBox } from '../components/live';
import { LoadingState, PageHeader, Panel } from '../components/ui';
import { LIVE_REFRESH_MS, api, formatPct, formatTime } from '../services/api';

function ModelBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div>
      <div className="flex justify-between text-xs text-space-gray mb-0.5">
        <span>{label}</span>
        <span>{value.toFixed(1)}%</span>
      </div>
      <div className="h-1.5 bg-space-black rounded-full overflow-hidden">
        <div className="h-full rounded-full" style={{ width: `${Math.min(100, value)}%`, background: color }} />
      </div>
    </div>
  );
}

function Forecasting() {
  const forecast = useQuery({ queryKey: ['forecast'], queryFn: api.getForecasts, refetchInterval: LIVE_REFRESH_MS });
  const ensemble = useQuery({ queryKey: ['forecast-ensemble'], queryFn: api.getEnsembleForecast, refetchInterval: LIVE_REFRESH_MS });

  if (forecast.isLoading) return <LoadingState message="Loading NOAA-based hourly forecasts..." />;

  const data = forecast.data;
  const predictions = data?.predictions ?? [];
  const ensemblePredictions = ensemble.data?.predictions ?? [];

  const chartData = predictions.map((p) => ({
    horizon: p.time_horizon,
    c: p.c_class_chance_pct ?? p.probability * 100,
    m: p.m_class_chance_pct ?? 0,
    x: p.x_class_chance_pct ?? 0,
  }));

  return (
    <div className="space-y-6">
      <PageHeader title="Forecasting" subtitle="Automatic hourly/daily probabilities — no manual input required" status="NOAA + trend model" />
      <DataSourceBadge source={data?.data_source} updated={data?.last_updated} />

      <MeaningBox
        title="How forecasting works"
        text={data?.methodology ?? 'Combines NOAA active-region flare probabilities, SWPC 1–3 day outlook, and live GOES flux trend. Updates every 60 seconds automatically.'}
      />

      <Panel title="Probability by Time Horizon (C / M / X class chances %)">
        <ForecastProbabilityChart data={chartData} />
      </Panel>

      <Panel title="Detailed Forecast Table">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-space-gray border-b border-space-blue/20">
                <th className="pb-3 pr-3">Horizon</th>
                <th className="pb-3 pr-3">Most Likely</th>
                <th className="pb-3 pr-3">C-class %</th>
                <th className="pb-3 pr-3">M-class %</th>
                <th className="pb-3 pr-3">X-class %</th>
                <th className="pb-3 pr-3">Confidence</th>
                <th className="pb-3">Expected By</th>
              </tr>
            </thead>
            <tbody>
              {predictions.map((item) => (
                <tr key={item.id} className="border-b border-space-blue/10 hover:bg-space-blue/5">
                  <td className="py-3 pr-3 font-medium">{item.time_horizon}</td>
                  <td className="py-3 pr-3"><FlareClassBadge flareClass={`${item.flare_class}0.0`} /></td>
                  <td className="py-3 pr-3 text-blue-400">{item.c_class_chance_pct?.toFixed(1)}%</td>
                  <td className="py-3 pr-3 text-purple-400">{item.m_class_chance_pct?.toFixed(1)}%</td>
                  <td className="py-3 pr-3 text-red-400">{item.x_class_chance_pct?.toFixed(1)}%</td>
                  <td className="py-3 pr-3">{formatPct(item.confidence)}</td>
                  <td className="py-3">{formatTime(item.expected_time)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {predictions.map((item) => (
          <div key={item.id} className="bg-space-dark rounded-xl p-5 border border-space-blue/20">
            <p className="text-space-gray text-sm">{item.time_horizon} ahead</p>
            <div className="flex justify-between items-center mt-2">
              <FlareClassBadge flareClass={item.flare_class} />
              <span className="text-2xl font-bold text-space-cyan">{formatPct(item.probability)}</span>
            </div>
            <p className="text-xs text-space-gray mt-3">{item.reasoning}</p>
            <div className="mt-3 h-2 bg-space-black rounded-full overflow-hidden flex">
              <div className="h-full bg-blue-500" style={{ width: `${item.c_class_chance_pct ?? 0}%` }} title="C" />
              <div className="h-full bg-purple-500" style={{ width: `${(item.m_class_chance_pct ?? 0) * 0.5}%` }} title="M" />
              <div className="h-full bg-red-500" style={{ width: `${(item.x_class_chance_pct ?? 0) * 0.3}%` }} title="X" />
            </div>
          </div>
        ))}
      </div>

      <PageHeader title="3-Model Ensemble Forecast" subtitle="Every contributing signal shown separately, not a black-box number" />

      <MeaningBox
        title="How the ensemble works"
        text={ensemble.data?.methodology ?? 'Loading methodology...'}
      />

      {ensemble.isLoading ? (
        <LoadingState message="Loading ensemble forecast..." />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {ensemblePredictions.map((p) => (
            <div key={p.id} className="bg-space-dark rounded-xl p-5 border border-space-blue/20">
              <div className="flex justify-between items-center mb-3">
                <div>
                  <p className="text-space-gray text-sm">{p.time_horizon} ahead</p>
                  <p className="text-xs text-space-gray">{formatTime(p.expected_time)}</p>
                </div>
                <FlareClassBadge flareClass={p.flare_class} />
              </div>
              <div className="space-y-2 mb-3">
                <ModelBar label={`Combined C/M/X: ${p.combined.c}% / ${p.combined.m}% / ${p.combined.x}%`} value={p.combined.m} color="#1a3d8f" />
              </div>
              <div className="border-t border-space-blue/10 pt-3 space-y-2">
                <p className="text-xs font-semibold text-space-gray uppercase">Model breakdown (M-class %)</p>
                <ModelBar label={`NOAA official (weight ${(p.weights.noaa_official * 100).toFixed(0)}%)`} value={p.models.noaa_official.m} color="#0e7490" />
                <ModelBar label={`Flux trend (weight ${(p.weights.flux_trend * 100).toFixed(0)}%)`} value={p.models.flux_trend.m} color="#c2410c" />
                <ModelBar label={`Historical frequency (weight ${(p.weights.historical_frequency * 100).toFixed(0)}%)`} value={p.models.historical_frequency.m} color="#7e22ce" />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default Forecasting;
