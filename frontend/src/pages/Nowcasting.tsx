import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { CHART_COLORS, FluxAreaChart } from '../components/charts';
import { DataSourceBadge, FlareClassBadge, MeaningBox } from '../components/live';
import { LoadingState, PageHeader, Panel, StatCard, formatFlux, formatTime, getRiskBg, getRiskColor } from '../components/ui';
import { LIVE_REFRESH_MS, api, formatPct } from '../services/api';

function Nowcasting() {
  const nowcast = useQuery({ queryKey: ['nowcast'], queryFn: api.getNowcast, refetchInterval: LIVE_REFRESH_MS });
  const flux = useQuery({ queryKey: ['flux', 6], queryFn: () => api.getFluxHistory(6), refetchInterval: LIVE_REFRESH_MS });
  const regions = useQuery({ queryKey: ['regions'], queryFn: api.getActiveRegions, refetchInterval: LIVE_REFRESH_MS });

  if (nowcast.isLoading) return <LoadingState message="Computing live nowcast from NOAA data..." />;

  const n = nowcast.data;
  const top = regions.data?.regions?.[0];

  return (
    <div className="space-y-6">
      <PageHeader title="Nowcasting" subtitle="Automated 0–60 min flare assessment from live GOES flux + active regions" status="Auto-updating" />
      <DataSourceBadge source={n?.data_source} updated={n?.last_update} />

      <div className={`rounded-xl p-6 border ${getRiskBg(n?.risk_level)}`}>
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div>
            <p className="text-sm text-space-gray">Current NOAA GOES Class</p>
            <div className="mt-2"><FlareClassBadge flareClass={n?.current_flare_class ?? 'A0.0'} /></div>
            <p className={`mt-2 text-sm ${getRiskColor(n?.risk_level)}`}>{n?.suggested_action}</p>
          </div>
          <div className="grid grid-cols-3 gap-3 text-center">
            <div className="bg-space-black/40 rounded-lg p-3">
              <p className="text-xs text-space-gray">Event Probability</p>
              <p className="text-xl font-bold">{formatPct(n?.probability_of_current_event)}</p>
            </div>
            <div className="bg-space-black/40 rounded-lg p-3">
              <p className="text-xs text-space-gray">Confidence</p>
              <p className="text-xl font-bold">{formatPct(n?.current_confidence)}</p>
            </div>
            <div className="bg-space-black/40 rounded-lg p-3">
              <p className="text-xs text-space-gray">Activity</p>
              <p className="text-xl font-bold">{n?.current_activity_level}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard label="Longwave Flux" value={formatFlux(n?.current_flux)} badge="L" accent="from-orange-500 to-red-500" />
        <StatCard label="Shortwave Flux" value={formatFlux(n?.shortwave_flux)} badge="S" accent="from-cyan-500 to-blue-500" />
        <StatCard label="Dominant Active Region" value={n?.affected_region ?? '—'} badge="AR" />
      </div>

      <Panel title="NOAA Published Class Probabilities (next 24h, dominant active region)">
        <p className="text-xs text-space-gray mb-3">
          These are NOAA's own forecaster-issued probabilities for the dominant active region — not a derived guess.
          We deliberately don't show a single predicted peak magnitude (e.g. "M5.1"): extrapolating one exact future
          flux value from a short-term trend systematically overshoots during a flare's rise phase, since real flares
          rise then decay rather than keep climbing at the observed rate.
        </p>
        <div className="grid grid-cols-3 gap-3 text-center">
          <div className="bg-space-black/40 rounded-lg p-3">
            <p className="text-xs text-space-gray">C-class+</p>
            <p className="text-xl font-bold text-blue-500">{n?.c_class_probability_pct ?? '—'}%</p>
          </div>
          <div className="bg-space-black/40 rounded-lg p-3">
            <p className="text-xs text-space-gray">M-class+</p>
            <p className="text-xl font-bold text-purple-500">{n?.m_class_probability_pct ?? '—'}%</p>
          </div>
          <div className="bg-space-black/40 rounded-lg p-3">
            <p className="text-xs text-space-gray">X-class</p>
            <p className="text-xl font-bold text-red-500">{n?.x_class_probability_pct ?? '—'}%</p>
          </div>
        </div>
        <p className="text-xs text-space-gray mt-3">Expected duration if a flare occurs: {n?.expected_duration}</p>
      </Panel>

      <Panel title="Input Flux (last 6 hours)">
        <FluxAreaChart data={flux.data?.points ?? []} dataKey="hard" color={CHART_COLORS.longwave} label="Longwave" thresholds={flux.data?.thresholds} />
      </Panel>

      <Panel title="Automated Analysis">
        <p className="text-sm text-space-gray leading-relaxed">{n?.ai_explanation}</p>
        <p className="text-xs text-space-gray mt-3">Last update: {formatTime(n?.last_update)}</p>
      </Panel>

      {top && (
        <MeaningBox
          title={`Active Region ${top.region_number} — ${top.location}`}
          text={`Magnetic class ${top.magnetic_class} (${top.spot_class}). NOAA 24h probabilities: C=${top.c_probability_pct}%, M=${top.m_probability_pct}%, X=${top.x_probability_pct}%. Intensity score ${top.intensity_score}.`}
        />
      )}
    </div>
  );
}

export default Nowcasting;
