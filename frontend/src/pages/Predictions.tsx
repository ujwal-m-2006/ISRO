import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { NowcastStatisticalChart, PredictionTableTrendChart } from '../components/charts';
import { DataSourceBadge, FlareClassBadge, MeaningBox } from '../components/live';
import { LoadingState, PageHeader, Panel, StatCard } from '../components/ui';
import { LIVE_REFRESH_MS, api, formatPct, formatTime } from '../services/api';

function scaleColor(scale: string) {
  const n = Number(scale) || 0;
  if (n === 0) return 'bg-green-100 text-green-800 border-green-400/50';
  if (n <= 1) return 'bg-yellow-100 text-yellow-800 border-yellow-400/50';
  if (n <= 2) return 'bg-orange-100 text-orange-800 border-orange-400/50';
  return 'bg-red-100 text-red-800 border-red-400/50';
}

function Predictions() {
  const forecast = useQuery({ queryKey: ['forecast'], queryFn: api.getForecasts, refetchInterval: LIVE_REFRESH_MS });
  const ensemble = useQuery({ queryKey: ['forecast-ensemble'], queryFn: api.getEnsembleForecast, refetchInterval: LIVE_REFRESH_MS });
  const nowcast = useQuery({ queryKey: ['nowcast'], queryFn: api.getNowcast, refetchInterval: LIVE_REFRESH_MS });
  const watches = useQuery({ queryKey: ['storm-watches'], queryFn: api.getStormWatches, refetchInterval: LIVE_REFRESH_MS });
  const indicators = useQuery({ queryKey: ['cme-indicators', 7], queryFn: () => api.getCMEIndicators(7), refetchInterval: LIVE_REFRESH_MS });
  const accuracy = useQuery({ queryKey: ['prediction-accuracy'], queryFn: api.getPredictionAccuracy, refetchInterval: LIVE_REFRESH_MS });

  if (forecast.isLoading || ensemble.isLoading) return <LoadingState message="Loading predictions from all models..." />;

  const predictions = forecast.data?.predictions ?? [];
  const ensemblePredictions = ensemble.data?.predictions ?? [];
  const activeWatch = watches.data?.latest_current;
  const staleWatch = !activeWatch ? watches.data?.latest : null;
  const arrivalEvents = (indicators.data?.events ?? []).filter((e) => e.arrival_estimate?.estimable);
  const nextArrival = arrivalEvents[0];

  const highestMProb = ensemblePredictions.reduce((max, p) => (p.combined.m > max ? p.combined.m : max), 0);
  const nearestHorizon = ensemblePredictions[0];

  const predictedChartData = ensemblePredictions.map((p) => ({
    horizon: p.time_horizon,
    m: p.combined.m,
    x: p.combined.x,
  }));

  const nowcastChartData = nowcast.data
    ? [{
        label: 'Right Now',
        c: nowcast.data.c_class_probability_pct ?? 0,
        m: nowcast.data.m_class_probability_pct ?? 0,
        x: nowcast.data.x_class_probability_pct ?? 0,
      }]
    : [];

  return (
    <div className="space-y-6">
      <PageHeader title="Predictions" subtitle="Flare forecast + geomagnetic storm watch + CME arrival — every predicted event, when, and how strong" status="Multi-model" />
      <DataSourceBadge source="Ensemble (NOAA + trend + historical) + NOAA storm watches + CME drag-based model" updated={forecast.data?.last_updated} />

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard
          label="Next Flare Forecast"
          value={nearestHorizon ? <FlareClassBadge flareClass={nearestHorizon.flare_class} /> : '—'}
          footer={nearestHorizon && <span className="text-xs text-space-gray">{nearestHorizon.time_horizon} ahead, M-class {nearestHorizon.combined.m}%</span>}
          badge="⚡"
        />
        <StatCard
          label="Geomagnetic Storm Watch"
          value={activeWatch?.peak_category ?? 'None active'}
          footer={
            activeWatch
              ? <span className="text-xs text-space-gray">Issued {formatTime(activeWatch.issued)}</span>
              : staleWatch && <span className="text-xs text-space-gray">Last issued {formatTime(staleWatch.issued)} — expired</span>
          }
          badge="G"
          accent={activeWatch ? 'from-yellow-500 to-orange-500' : 'from-space-blue to-space-purple'}
        />
        <StatCard
          label="Next CME Earth Arrival"
          value={nextArrival ? formatTime(nextArrival.arrival_estimate?.nominal?.arrival_time) : 'None predicted'}
          footer={nextArrival && <span className="text-xs text-space-gray">{nextArrival.velocity_km_s?.toFixed(0)} km/s shock</span>}
          badge="☄"
          accent={nextArrival ? 'from-red-500 to-orange-500' : 'from-space-blue to-space-purple'}
        />
      </div>

      {/* Flare prediction */}
      <PageHeader title="Solar Flare Forecast" subtitle="Probability by time horizon, from the 3-model ensemble" />
      <Panel title="Prediction Table Trend (M-class / X-class chance)">
        <PredictionTableTrendChart data={predictedChartData} />
      </Panel>
      <Panel title="Nowcast — Current-Moment Probability">
        {nowcast.isLoading ? (
          <LoadingState message="Loading nowcast..." />
        ) : (
          <NowcastStatisticalChart data={nowcastChartData} />
        )}
      </Panel>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-space-gray border-b border-space-blue/20">
              <th className="pb-2 pr-3">Horizon</th>
              <th className="pb-2 pr-3">Expected By</th>
              <th className="pb-2 pr-3">Most Likely Class</th>
              <th className="pb-2 pr-3">M-class Chance</th>
              <th className="pb-2">X-class Chance</th>
            </tr>
          </thead>
          <tbody>
            {ensemblePredictions.map((p) => (
              <tr key={p.id} className="border-b border-space-blue/10">
                <td className="py-2 pr-3 font-medium">{p.time_horizon}</td>
                <td className="py-2 pr-3">{formatTime(p.expected_time)}</td>
                <td className="py-2 pr-3"><FlareClassBadge flareClass={p.flare_class} /></td>
                <td className="py-2 pr-3 text-purple-700">{p.combined.m}%</td>
                <td className="py-2 text-red-700">{p.combined.x}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Storm watch */}
      <PageHeader title="Geomagnetic Storm Prediction" subtitle="NOAA forecaster-issued day-by-day watch" />
      {activeWatch ? (
        <Panel title={`Watch issued ${formatTime(activeWatch.issued)} — peak category ${activeWatch.peak_category}`}>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {activeWatch.daily_forecast.map((d, i) => {
              const scale = d.level.match(/G(\d)/)?.[1] ?? '0';
              return (
                <div key={i} className={`rounded-lg border p-4 ${scaleColor(scale)}`}>
                  <p className="text-xs uppercase opacity-70">{d.day}</p>
                  <p className="font-bold">{d.level}</p>
                </div>
              );
            })}
          </div>
        </Panel>
      ) : (
        <Panel title="Geomagnetic Storm Watch">
          <p className="text-sm text-space-gray py-4 text-center">No active NOAA storm watch right now — quiet conditions expected.</p>
          {staleWatch && (
            <p className="text-xs text-space-gray text-center">
              (Most recent watch was issued {formatTime(staleWatch.issued)} for {staleWatch.daily_forecast.map((d) => d.day).join(', ')} — those days have passed, so it's no longer current.)
            </p>
          )}
        </Panel>
      )}

      {/* CME arrival */}
      <PageHeader title="CME Earth-Arrival Prediction" subtitle="Drag-Based Model estimate from detected radio-burst shock velocity" />
      {arrivalEvents.length === 0 ? (
        <Panel title="CME Arrival">
          <p className="text-sm text-space-gray py-6 text-center">No Earth-bound CME shocks detected in the last 7 days.</p>
        </Panel>
      ) : (
        <div className="space-y-4">
          {arrivalEvents.map((e, i) => {
            const est = e.arrival_estimate!;
            return (
              <Panel
                key={i}
                title={`${e.type} detected ${formatTime(e.begin_time)} — ${e.velocity_km_s?.toFixed(0)} km/s`}
                action={e.associated_flare?.flare_class ? <FlareClassBadge flareClass={e.associated_flare.flare_class} /> : undefined}
              >
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm">
                  <div>
                    <p className="text-xs text-space-gray uppercase">Earliest Plausible</p>
                    <p className="font-medium">{formatTime(est.earliest_plausible?.arrival_time)}</p>
                  </div>
                  <div className="bg-red-50 rounded p-2 -m-2 border border-red-400/30">
                    <p className="text-xs text-space-gray uppercase">Nominal Arrival</p>
                    <p className="font-bold text-red-800">{formatTime(est.nominal?.arrival_time)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-space-gray uppercase">Latest Plausible</p>
                    <p className="font-medium">{formatTime(est.latest_plausible?.arrival_time)}</p>
                  </div>
                </div>
                <p className="text-xs text-space-gray mt-3">{est.uncertainty_note}</p>
                {e.donki_cross_check?.donki_speed_km_s && (
                  <p className="text-xs text-space-gray mt-2 pt-2 border-t border-space-blue/10">
                    Cross-check vs NASA DONKI (coronagraph): {e.donki_cross_check.donki_speed_km_s.toFixed(0)} km/s
                    {e.donki_cross_check.speed_difference_pct != null && ` (${e.donki_cross_check.speed_difference_pct}% different — expected, different measurement method)`}
                  </p>
                )}
              </Panel>
            );
          })}
        </div>
      )}

      {/* Prediction accuracy */}
      <PageHeader title="Prediction Accuracy" subtitle="Real computed accuracy — every prediction is stored, then checked against actual NOAA outcomes once its window passes" />
      {accuracy.isLoading ? (
        <LoadingState message="Loading accuracy stats..." />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {accuracy.data && (['ensemble_flare', 'storm_watch', 'cme_arrival'] as const).map((key) => {
            const c = accuracy.data![key];
            const labels: Record<string, string> = { ensemble_flare: 'Flare Class', storm_watch: 'Storm G-Level', cme_arrival: 'CME Impact Detected' };
            return (
              <div key={key} className="bg-space-dark rounded-xl p-5 border border-space-blue/20">
                <p className="text-sm text-space-gray">{labels[key]}</p>
                <p className="text-3xl font-bold mt-1">{c.accuracy_pct != null ? `${c.accuracy_pct}%` : '—'}</p>
                <p className="text-xs text-space-gray mt-2">
                  {c.correct} correct / {c.total_verified} verified &middot; {c.total_pending} awaiting their target window
                </p>
              </div>
            );
          })}
        </div>
      )}
      <p className="text-xs text-space-gray">
        These numbers only reflect predictions old enough that their target window has actually passed — accuracy will
        fill in as more predictions age past their target time. No solar flare/storm forecasting system (including
        NOAA's own operational models) achieves 100% accuracy; these are genuine measured hit-rates, not a promised guarantee.
      </p>

      <MeaningBox
        title="How these predictions are made"
        text="Flare probabilities combine NOAA's official active-region statistics, live GOES flux trend, and historical flare frequency (3 independent models, weighted and shown separately — see the Forecasting page for full model breakdown). Storm watches are NOAA's own human-forecaster issued day-by-day G-scale predictions. CME arrival times use the published Drag-Based Model (Vrsnak et al. 2013), fed by real detected shock velocities and live solar wind speed — typically accurate to within +/-10 hours, not an exact time."
      />
    </div>
  );
}

export default Predictions;
