import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { DataSourceBadge } from '../components/live';
import { ErrorState, LoadingState, PageHeader, Panel } from '../components/ui';
import { LIVE_REFRESH_MS, api } from '../services/api';
import type { EarthImpactDay, ScaleDetail } from '../types';

function scaleColor(scale: string) {
  const n = Number(scale) || 0;
  if (n === 0) return 'bg-green-100 text-green-800 border-green-400/50';
  if (n <= 1) return 'bg-yellow-100 text-yellow-800 border-yellow-400/50';
  if (n <= 2) return 'bg-orange-100 text-orange-800 border-orange-400/50';
  return 'bg-red-100 text-red-800 border-red-400/50';
}

function ScaleCard({ title, code, detail }: { title: string; code: string; detail: ScaleDetail }) {
  return (
    <div className={`rounded-xl border p-4 ${scaleColor(detail.scale)}`}>
      <div className="flex items-center justify-between mb-1">
        <p className="font-semibold text-sm">{title}</p>
        <span className="font-bold text-lg">{code}{detail.scale}</span>
      </div>
      <p className="text-xs uppercase tracking-wide opacity-70 mb-2">{detail.text}</p>
      <p className="text-sm leading-relaxed">{detail.effect}</p>
    </div>
  );
}

function DayPanel({ day }: { day: EarthImpactDay }) {
  return (
    <Panel title={`${day.label}${day.date ? ` — ${day.date}` : ''}`}>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <ScaleCard title="Radio Blackout" code="R" detail={day.radio_blackout} />
        <ScaleCard title="Radiation Storm" code="S" detail={day.radiation_storm} />
        <ScaleCard title="Geomagnetic Storm" code="G" detail={day.geomagnetic_storm} />
      </div>
    </Panel>
  );
}

function EarthImpact() {
  const impact = useQuery({ queryKey: ['earth-impact'], queryFn: api.getEarthImpact, refetchInterval: LIVE_REFRESH_MS });

  if (impact.isLoading) return <LoadingState message="Loading Earth impact forecast..." />;
  if (impact.isError) return <ErrorState message="Could not reach the Earth impact endpoint." />;

  const d = impact.data!;

  return (
    <div className="space-y-6">
      <PageHeader title="How This Affects Earth" subtitle="NOAA Space Weather Scales (R/S/G) — plain-language impact of current solar activity" status="Live" />
      <DataSourceBadge source={d.data_source} updated={d.last_update} />

      <div className={`rounded-xl border p-5 ${scaleColor(String(d.max_scale_today))}`}>
        <p className="text-xs uppercase tracking-wide opacity-70 mb-1">Overall assessment — today</p>
        <p className="text-lg font-semibold">{d.overall_earth_effect}</p>
      </div>

      <DayPanel day={d.today} />

      <Panel title="3-Day Forecast">
        <div className="space-y-4">
          {d.forecast.map((day) => (
            <DayPanel key={day.label} day={day} />
          ))}
        </div>
      </Panel>

      <div className="rounded-xl border border-space-blue/20 bg-space-dark p-4 text-xs text-space-gray space-y-1">
        <p><strong>R — Radio Blackout:</strong> caused by X-ray flares, affects HF radio and navigation.</p>
        <p><strong>S — Radiation Storm:</strong> caused by high-energy protons, affects astronauts, satellites, and polar flights.</p>
        <p><strong>G — Geomagnetic Storm:</strong> caused by CME/solar wind impacts on Earth's magnetosphere, affects power grids, satellites, and produces aurora.</p>
        <p>Each scale runs 0 (none) to 5 (extreme), per NOAA's official Space Weather Scales.</p>
      </div>
    </div>
  );
}

export default EarthImpact;
