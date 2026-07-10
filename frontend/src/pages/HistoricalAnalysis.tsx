import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { DualFluxChart } from '../components/charts';
import { DataSourceBadge, FlareClassBadge } from '../components/live';
import { LoadingState, PageHeader, Panel } from '../components/ui';
import { LIVE_REFRESH_MS, api, formatFlux } from '../services/api';

function HistoricalAnalysis() {
  const [hours, setHours] = useState<6 | 24 | 168>(24);
  const flux = useQuery({ queryKey: ['flux', hours], queryFn: () => api.getFluxHistory(hours), refetchInterval: LIVE_REFRESH_MS });
  const flares = useQuery({ queryKey: ['flares'], queryFn: api.getRecentFlares, refetchInterval: LIVE_REFRESH_MS });

  const points = flux.data?.points ?? [];
  const avgLong = points.length ? points.reduce((s, p) => s + p.hard, 0) / points.length : 0;
  const maxLong = points.length ? Math.max(...points.map((p) => p.hard)) : 0;

  return (
    <div className="space-y-6">
      <PageHeader title="Historical Analysis" subtitle="NOAA GOES archived flux — same data as SWPC 6h/1d/7d products" />
      <DataSourceBadge source={flux.data?.data_source} updated={flux.data?.last_update} />

      <div className="flex gap-2">
        {([6, 24, 168] as const).map((h) => (
          <button key={h} type="button" onClick={() => setHours(h)} className={`px-4 py-2 rounded-lg text-sm font-medium ${hours === h ? 'bg-space-blue text-white' : 'bg-space-dark border border-space-blue/20 text-space-gray'}`}>
            {h === 168 ? '7 days' : `${h} hours`}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <SummaryCard label="Average Longwave Flux" value={formatFlux(avgLong)} />
        <SummaryCard label="Peak Longwave Flux" value={formatFlux(maxLong)} />
        <SummaryCard label="Data Points" value={String(points.length)} />
      </div>

      <Panel title={`GOES Flux History — ${hours === 168 ? '7 days' : `${hours} hours`}`}>
        {flux.isLoading ? <LoadingState /> : <DualFluxChart data={points} thresholds={flux.data?.thresholds} />}
      </Panel>

      <Panel title="Recent Flare Events (NOAA catalogue)">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-space-gray border-b border-space-blue/20">
                <th className="pb-2 pr-4">Peak</th>
                <th className="pb-2 pr-4">Begin → End Class</th>
                <th className="pb-2 pr-4">Peak Flux</th>
                <th className="pb-2">Duration</th>
              </tr>
            </thead>
            <tbody>
              {(flares.data?.flares ?? []).map((f) => (
                <tr key={f.id} className="border-b border-space-blue/10">
                  <td className="py-2 pr-4"><FlareClassBadge flareClass={f.max_class ?? '?'} /></td>
                  <td className="py-2 pr-4">{f.begin_class} → {f.end_class}</td>
                  <td className="py-2 pr-4">{formatFlux(f.max_flux_wm2)}</td>
                  <td className="py-2">{f.duration_minutes ? `${f.duration_minutes} min` : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-space-dark rounded-xl p-5 border border-space-blue/20">
      <p className="text-space-gray text-sm">{label}</p>
      <p className="text-2xl font-bold mt-1">{value}</p>
    </div>
  );
}

export default HistoricalAnalysis;
