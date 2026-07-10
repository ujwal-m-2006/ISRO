import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { CHART_COLORS, DualFluxChart, FluxAreaChart } from '../components/charts';
import { DataSourceBadge, FlareClassBadge, MeaningBox } from '../components/live';
import { LoadingState, PageHeader, Panel, StatCard, formatFlux, formatTime, getRiskBg, getRiskColor } from '../components/ui';
import { LIVE_REFRESH_MS, api, formatPct } from '../services/api';

function Dashboard() {
  const summary = useQuery({ queryKey: ['live-summary'], queryFn: api.getLiveSummary, refetchInterval: LIVE_REFRESH_MS });
  const flux = useQuery({ queryKey: ['flux', 6], queryFn: () => api.getFluxHistory(6), refetchInterval: LIVE_REFRESH_MS });
  const nowcast = useQuery({ queryKey: ['nowcast'], queryFn: api.getNowcast, refetchInterval: LIVE_REFRESH_MS });
  const flares = useQuery({ queryKey: ['flares'], queryFn: api.getRecentFlares, refetchInterval: LIVE_REFRESH_MS });

  if (summary.isLoading) return <LoadingState message="Fetching live NOAA GOES data..." />;

  const s = summary.data;
  const points = flux.data?.points ?? [];
  const thresholds = flux.data?.thresholds;

  return (
    <div className="space-y-6">
      <PageHeader title="Dashboard" status="NOAA GOES-18 live feed" />
      <DataSourceBadge source={s?.data_source} updated={s?.last_update} />

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard label="Current Flare Class (GOES Long)" value={<FlareClassBadge flareClass={s?.current_class ?? 'A0.0'} />} badge="GOES" />
        <StatCard label="Longwave Flux (0.1–0.8 nm)" value={formatFlux(s?.current_flux.longwave_0_1_0_8_nm_wm2)} badge="L" accent="from-orange-500 to-red-500" />
        <StatCard label="Shortwave Flux (0.05–0.4 nm)" value={formatFlux(s?.current_flux.shortwave_0_05_0_4_nm_wm2)} badge="S" accent="from-cyan-500 to-blue-500" />
        <div className={`rounded-xl p-6 border ${getRiskBg(s?.risk_level)}`}>
          <p className="text-space-gray text-sm">Activity / Risk</p>
          <p className="text-2xl font-bold mt-1">{s?.activity_level}</p>
          <p className={`text-sm mt-1 ${getRiskColor(s?.risk_level)}`}>{s?.risk_level} risk</p>
        </div>
        <StatCard label="30-min Flux Trend" value={`${s?.flux_trend_pct_30min ?? 0}%`} badge="Δ" />
        <StatCard label="Active Regions" value={s?.active_regions_count ?? 0} badge="AR" />
        <StatCard label="Flares (7 days)" value={s?.recent_flares_count_7d ?? 0} badge="7d" />
        <StatCard label="Nowcast Probability" value={formatPct(nowcast.data?.probability_of_current_event)} badge="AI" accent="from-purple-500 to-fuchsia-500" />
      </div>

      <MeaningBox title="What does the current class mean?" text={s?.class_meaning ?? ''} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Panel title="Shortwave X-ray Flux — 0.05–0.4 nm (cyan)">
          <FluxAreaChart data={points} dataKey="soft" color={CHART_COLORS.shortwave} label="Shortwave" thresholds={thresholds} />
        </Panel>
        <Panel title="Longwave X-ray Flux — 0.1–0.8 nm (orange)">
          <FluxAreaChart data={points} dataKey="hard" color={CHART_COLORS.longwave} label="Longwave (flare class band)" thresholds={thresholds} />
        </Panel>
        <Panel title="Combined Live Flux (matches NOAA SWPC plots)">
          <DualFluxChart data={points} thresholds={thresholds} />
        </Panel>
        <Panel title="Latest Flare Event">
          {s?.latest_flare ? (
            <div className="space-y-3 text-sm">
              <div className="flex items-center gap-3">
                <FlareClassBadge flareClass={s.latest_flare.max_class ?? '?'} />
                <span className="text-space-gray">Peak flux {formatFlux(s.latest_flare.max_flux_wm2)}</span>
              </div>
              <p><span className="text-space-gray">Begin:</span> {formatTime(s.latest_flare.begin_time)}</p>
              <p><span className="text-space-gray">Peak:</span> {formatTime(s.latest_flare.max_time)}</p>
              <p><span className="text-space-gray">End:</span> {formatTime(s.latest_flare.end_time)}</p>
              <p className="text-space-gray">{nowcast.data?.ai_explanation}</p>
            </div>
          ) : (
            <p className="text-space-gray text-sm">No flare in latest NOAA report.</p>
          )}
        </Panel>
      </div>

      {flares.data?.flares?.length ? (
        <Panel title="Recent Flares (last 7 days — NOAA verified)">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-space-gray border-b border-space-blue/20">
                  <th className="pb-2 pr-4">Peak Class</th>
                  <th className="pb-2 pr-4">Peak Flux</th>
                  <th className="pb-2 pr-4">Begin</th>
                  <th className="pb-2 pr-4">Peak Time</th>
                  <th className="pb-2">Duration</th>
                </tr>
              </thead>
              <tbody>
                {flares.data.flares.slice(0, 8).map((f) => (
                  <tr key={f.id} className="border-b border-space-blue/10">
                    <td className="py-2 pr-4"><FlareClassBadge flareClass={f.max_class ?? '?'} /></td>
                    <td className="py-2 pr-4">{formatFlux(f.max_flux_wm2)}</td>
                    <td className="py-2 pr-4">{formatTime(f.begin_time)}</td>
                    <td className="py-2 pr-4">{formatTime(f.max_time)}</td>
                    <td className="py-2">{f.duration_minutes ? `${f.duration_minutes} min` : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      ) : null}
    </div>
  );
}

export default Dashboard;
