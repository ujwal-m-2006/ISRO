import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { IntensityChart, RegionProbabilityChart } from '../components/charts';
import { DataSourceBadge, FlareClassBadge, GlossaryPanel, MeaningBox } from '../components/live';
import { LoadingState, PageHeader, Panel, StatCard } from '../components/ui';
import { LIVE_REFRESH_MS, api, formatFlux } from '../services/api';

function SolarAnalytics() {
  const regions = useQuery({ queryKey: ['regions'], queryFn: api.getActiveRegions, refetchInterval: LIVE_REFRESH_MS });
  const summary = useQuery({ queryKey: ['live-summary'], queryFn: api.getLiveSummary, refetchInterval: LIVE_REFRESH_MS });

  if (regions.isLoading) return <LoadingState message="Loading active region analytics..." />;

  const list = regions.data?.regions ?? [];
  const top8 = list.slice(0, 8);
  const longFlux = summary.data?.current_flux.longwave_0_1_0_8_nm_wm2 ?? 0;
  const shortFlux = summary.data?.current_flux.shortwave_0_05_0_4_nm_wm2 ?? 0;

  const probChart = top8.map((r) => ({
    name: `AR ${r.region_number}`,
    c: r.c_probability_pct,
    m: r.m_probability_pct,
    x: r.x_probability_pct,
  }));

  const intensityChart = top8.map((r) => ({
    name: `AR ${r.region_number}`,
    intensity: r.intensity_score,
  }));

  return (
    <div className="space-y-6">
      <PageHeader title="Solar Analytics" subtitle="Active region intensity & NOAA flare probabilities" status="Live" />
      <DataSourceBadge source={regions.data?.data_source} updated={regions.data?.last_update} />

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard label="Short/Long Flux Ratio" value={(shortFlux / (longFlux || 1)).toFixed(3)} badge="R" />
        <StatCard label="Current GOES Class" value={<FlareClassBadge flareClass={summary.data?.current_class ?? 'A0.0'} />} badge="C" />
        <StatCard label="Active Regions Today" value={list.length} badge="N" accent="from-cyan-500 to-blue-500" />
        <StatCard label="Highest M-Prob Region" value={top8[0] ? `AR ${top8[0].region_number} (${top8[0].m_probability_pct}%)` : '—'} badge="M" accent="from-purple-500 to-pink-500" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Panel title="Flare Probabilities by Active Region (NOAA official %)">
          <RegionProbabilityChart regions={probChart} />
          <p className="text-xs text-space-gray mt-2">Blue = C-class · Purple = M-class · Red = X-class chance in next 24h</p>
        </Panel>
        <Panel title="Region Intensity Score">
          <IntensityChart regions={intensityChart} />
          <p className="text-xs text-space-gray mt-2">Composite of magnetic complexity, sunspot area, and flare history</p>
        </Panel>
      </div>

      <Panel title="Active Regions — Live NOAA Data">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-space-gray border-b border-space-blue/20">
                <th className="pb-2 pr-3">Region</th>
                <th className="pb-2 pr-3">Location</th>
                <th className="pb-2 pr-3">Mag Class</th>
                <th className="pb-2 pr-3">Area</th>
                <th className="pb-2 pr-3">C%</th>
                <th className="pb-2 pr-3">M%</th>
                <th className="pb-2 pr-3">X%</th>
                <th className="pb-2 pr-3">Events C/M/X</th>
                <th className="pb-2">Intensity</th>
              </tr>
            </thead>
            <tbody>
              {list.map((r) => (
                <tr key={`${r.region_number}-${r.observed_date}`} className="border-b border-space-blue/10 hover:bg-space-blue/5">
                  <td className="py-2 pr-3 font-bold">AR {r.region_number}</td>
                  <td className="py-2 pr-3">{r.location}</td>
                  <td className="py-2 pr-3"><span className="text-orange-300">{r.magnetic_class}</span> / {r.spot_class}</td>
                  <td className="py-2 pr-3">{r.area_millionths}</td>
                  <td className="py-2 pr-3 text-blue-400">{r.c_probability_pct}%</td>
                  <td className="py-2 pr-3 text-purple-400">{r.m_probability_pct}%</td>
                  <td className="py-2 pr-3 text-red-400">{r.x_probability_pct}%</td>
                  <td className="py-2 pr-3">{r.c_events}/{r.m_events}/{r.x_events}</td>
                  <td className="py-2 font-bold text-orange-400">{r.intensity_score}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      {top8[0] && (
        <MeaningBox
          title={`Highest intensity: AR ${top8[0].region_number} at ${top8[0].location}`}
          text={`Magnetic class ${top8[0].magnetic_class} indicates ${top8[0].magnetic_class?.startsWith('D') || top8[0].magnetic_class?.startsWith('E') || top8[0].magnetic_class?.startsWith('F') || top8[0].magnetic_class?.startsWith('G') ? 'complex beta-gamma-delta fields — elevated flare productivity' : ' simpler magnetic configuration'}. Live flux: longwave ${formatFlux(longFlux)}.`}
        />
      )}

      {regions.data?.glossary && <GlossaryPanel title="Active Region Field Guide" items={regions.data.glossary} />}
    </div>
  );
}

export default SolarAnalytics;
