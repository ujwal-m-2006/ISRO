import React from 'react';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { FluxPoint, SolarWindPoint } from '../types';

export const CHART_COLORS = {
  shortwave: '#0e7490',
  longwave: '#c2410c',
  background: '#15803d',
  cThreshold: '#a16207',
  mThreshold: '#c2410c',
  xThreshold: '#b91c1c',
  regionC: '#1a3d8f',
  regionM: '#7e22ce',
  regionX: '#b91c1c',
  grid: '#e2e8f0',
  axis: '#475569',
};

const tooltipStyle = {
  background: '#ffffff',
  border: '1px solid #cbd5e1',
  borderRadius: 8,
  color: '#0f172a',
};

// A log-scale axis breaks entirely if any point is <= 0 (NOAA reports 0 flux
// during data gaps), so floor points to a tiny epsilon before charting.
const MIN_LOG_FLUX = 1e-9;
function sanitizeFluxPoints(data: FluxPoint[]): FluxPoint[] {
  return data.map((p) => ({
    ...p,
    soft: p.soft > 0 ? p.soft : MIN_LOG_FLUX,
    hard: p.hard > 0 ? p.hard : MIN_LOG_FLUX,
  }));
}

export function DualFluxChart({
  data,
  thresholds,
}: {
  data: FluxPoint[];
  thresholds?: Record<string, number>;
}) {
  return (
    <div className="h-80">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={sanitizeFluxPoints(data)} margin={{ top: 12, right: 12, left: 4, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
          <XAxis dataKey="time" stroke={CHART_COLORS.axis} tick={{ fontSize: 10 }} minTickGap={24} />
          <YAxis stroke={CHART_COLORS.axis} tick={{ fontSize: 10 }} scale="log" domain={['auto', 'auto']} tickFormatter={(v) => Number(v).toExponential(0)} />
          <Tooltip
            contentStyle={tooltipStyle}
            formatter={(value: number, name: string) => [
              `${Number(value).toExponential(2)} W/m²`,
              name === 'soft' ? 'Shortwave (0.05–0.4 nm)' : 'Longwave (0.1–0.8 nm)',
            ]}
          />
          <Legend />
          {thresholds?.C && <ReferenceLine y={thresholds.C} stroke={CHART_COLORS.cThreshold} strokeDasharray="4 4" label={{ value: 'C-class', fill: CHART_COLORS.cThreshold, fontSize: 10 }} />}
          {thresholds?.M && <ReferenceLine y={thresholds.M} stroke={CHART_COLORS.mThreshold} strokeDasharray="4 4" label={{ value: 'M-class', fill: CHART_COLORS.mThreshold, fontSize: 10 }} />}
          {thresholds?.X && <ReferenceLine y={thresholds.X} stroke={CHART_COLORS.xThreshold} strokeDasharray="4 4" label={{ value: 'X-class', fill: CHART_COLORS.xThreshold, fontSize: 10 }} />}
          <Line type="monotone" dataKey="soft" stroke={CHART_COLORS.shortwave} dot={false} name="Shortwave" strokeWidth={2.5} />
          <Line type="monotone" dataKey="hard" stroke={CHART_COLORS.longwave} dot={false} name="Longwave" strokeWidth={2.5} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function FluxAreaChart({ data, dataKey, color, label, thresholds }: {
  data: FluxPoint[];
  dataKey: 'soft' | 'hard';
  color: string;
  label: string;
  thresholds?: Record<string, number>;
}) {
  const gradId = `grad-${dataKey}`;
  return (
    <div className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={sanitizeFluxPoints(data)} margin={{ top: 12, right: 12, left: 4, bottom: 0 }}>
          <defs>
            <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={color} stopOpacity={0.45} />
              <stop offset="95%" stopColor={color} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
          <XAxis dataKey="time" stroke={CHART_COLORS.axis} tick={{ fontSize: 10 }} minTickGap={24} />
          <YAxis stroke={CHART_COLORS.axis} tick={{ fontSize: 10 }} scale="log" domain={['auto', 'auto']} tickFormatter={(v) => Number(v).toExponential(0)} />
          <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => [`${Number(v).toExponential(2)} W/m²`, label]} />
          {thresholds?.C && <ReferenceLine y={thresholds.C} stroke={CHART_COLORS.cThreshold} strokeDasharray="3 3" />}
          {thresholds?.M && <ReferenceLine y={thresholds.M} stroke={CHART_COLORS.mThreshold} strokeDasharray="3 3" />}
          <Area type="monotone" dataKey={dataKey} stroke={color} fill={`url(#${gradId})`} strokeWidth={2} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export function RegionProbabilityChart({ regions }: { regions: { name: string; c: number; m: number; x: number }[] }) {
  const flat = regions.flatMap((r) => [
    { region: r.name, type: 'C-class %', value: r.c, fill: CHART_COLORS.regionC },
    { region: r.name, type: 'M-class %', value: r.m, fill: CHART_COLORS.regionM },
    { region: r.name, type: 'X-class %', value: r.x, fill: CHART_COLORS.regionX },
  ]);

  return (
    <div className="h-80">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={flat} margin={{ top: 8, right: 8, left: 0, bottom: 40 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
          <XAxis dataKey="region" stroke={CHART_COLORS.axis} tick={{ fontSize: 10 }} angle={-20} textAnchor="end" height={50} />
          <YAxis stroke={CHART_COLORS.axis} domain={[0, 100]} tickFormatter={(v) => `${v}%`} />
          <Tooltip contentStyle={tooltipStyle} />
          <Legend />
          <Bar dataKey="value" name="Probability">
            {flat.map((entry, i) => (
              <Cell key={`cell-${i}`} fill={entry.fill} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function ForecastProbabilityChart({ data }: { data: { horizon: string; c: number; m: number; x: number }[] }) {
  return (
    <div className="h-80">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
          <XAxis dataKey="horizon" stroke={CHART_COLORS.axis} tick={{ fontSize: 11 }} />
          <YAxis stroke={CHART_COLORS.axis} domain={[0, 100]} tickFormatter={(v) => `${v}%`} />
          <Tooltip contentStyle={tooltipStyle} />
          <Legend />
          <Bar dataKey="c" name="C-class chance %" fill={CHART_COLORS.regionC} radius={[4, 4, 0, 0]} />
          <Bar dataKey="m" name="M-class chance %" fill={CHART_COLORS.regionM} radius={[4, 4, 0, 0]} />
          <Bar dataKey="x" name="X-class chance %" fill={CHART_COLORS.regionX} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// Distinct palette from ForecastProbabilityChart's blue/purple/red, so the
// Predictions tab's ensemble-model chart is visually distinguishable at a
// glance from the plain NOAA forecast chart it replaced.
const PREDICTED_COLORS = { c: '#0f766e', m: '#b45309', x: '#9d174d' };

export function PredictedStatisticalChart({ data }: { data: { horizon: string; c: number; m: number; x: number }[] }) {
  return (
    <div className="h-80">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
          <XAxis dataKey="horizon" stroke={CHART_COLORS.axis} tick={{ fontSize: 11 }} />
          <YAxis stroke={CHART_COLORS.axis} domain={[0, 100]} tickFormatter={(v) => `${v}%`} />
          <Tooltip contentStyle={tooltipStyle} />
          <Legend />
          <Bar dataKey="c" name="C-class chance % (ensemble)" fill={PREDICTED_COLORS.c} radius={[4, 4, 0, 0]} />
          <Bar dataKey="m" name="M-class chance % (ensemble)" fill={PREDICTED_COLORS.m} radius={[4, 4, 0, 0]} />
          <Bar dataKey="x" name="X-class chance % (ensemble)" fill={PREDICTED_COLORS.x} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// A third, again-distinct palette for the nowcast (current-moment) snapshot.
const NOWCAST_COLORS = { c: '#4338ca', m: '#0369a1', x: '#be123c' };

export function NowcastStatisticalChart({ data }: { data: { label: string; c: number; m: number; x: number }[] }) {
  return (
    <div className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
          <XAxis dataKey="label" stroke={CHART_COLORS.axis} tick={{ fontSize: 11 }} />
          <YAxis stroke={CHART_COLORS.axis} domain={[0, 100]} tickFormatter={(v) => `${v}%`} />
          <Tooltip contentStyle={tooltipStyle} />
          <Legend />
          <Bar dataKey="c" name="C-class chance % (nowcast)" fill={NOWCAST_COLORS.c} radius={[4, 4, 0, 0]} barSize={48} />
          <Bar dataKey="m" name="M-class chance % (nowcast)" fill={NOWCAST_COLORS.m} radius={[4, 4, 0, 0]} barSize={48} />
          <Bar dataKey="x" name="X-class chance % (nowcast)" fill={NOWCAST_COLORS.x} radius={[4, 4, 0, 0]} barSize={48} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function swTime(p: SolarWindPoint) {
  const t = p.time_tag;
  if (!t) return '';
  const d = new Date(t);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export function SolarWindSpeedChart({ points }: { points: SolarWindPoint[] }) {
  const data = points.map((p) => ({ time: swTime(p), speed: p.speed_km_s, density: p.density_p_cm3 }));
  return (
    <div className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 12, right: 12, left: 4, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
          <XAxis dataKey="time" stroke={CHART_COLORS.axis} tick={{ fontSize: 10 }} minTickGap={30} />
          <YAxis yAxisId="speed" stroke={CHART_COLORS.axis} tick={{ fontSize: 10 }} label={{ value: 'km/s', angle: -90, position: 'insideLeft', fontSize: 10, fill: CHART_COLORS.axis }} />
          <YAxis yAxisId="density" orientation="right" stroke={CHART_COLORS.axis} tick={{ fontSize: 10 }} label={{ value: 'p/cm³', angle: 90, position: 'insideRight', fontSize: 10, fill: CHART_COLORS.axis }} />
          <Tooltip contentStyle={tooltipStyle} />
          <Legend />
          <Line yAxisId="speed" type="monotone" dataKey="speed" name="Speed (km/s)" stroke={CHART_COLORS.regionC} dot={false} strokeWidth={2.5} />
          <Line yAxisId="density" type="monotone" dataKey="density" name="Density (p/cm³)" stroke={CHART_COLORS.regionM} dot={false} strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function SolarWindFieldChart({ points }: { points: SolarWindPoint[] }) {
  const data = points.map((p) => ({ time: swTime(p), bz: p.bz_nt, bt: p.bt_nt }));
  return (
    <div className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 12, right: 12, left: 4, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
          <XAxis dataKey="time" stroke={CHART_COLORS.axis} tick={{ fontSize: 10 }} minTickGap={30} />
          <YAxis stroke={CHART_COLORS.axis} tick={{ fontSize: 10 }} label={{ value: 'nT', angle: -90, position: 'insideLeft', fontSize: 10, fill: CHART_COLORS.axis }} />
          <Tooltip contentStyle={tooltipStyle} />
          <Legend />
          <ReferenceLine y={0} stroke={CHART_COLORS.axis} />
          <ReferenceLine y={-5} stroke={CHART_COLORS.xThreshold} strokeDasharray="4 4" label={{ value: 'Storm risk (Bz < -5nT)', fill: CHART_COLORS.xThreshold, fontSize: 10 }} />
          <Line type="monotone" dataKey="bz" name="Bz (nT, south = negative)" stroke={CHART_COLORS.xThreshold} dot={false} strokeWidth={2.5} />
          <Line type="monotone" dataKey="bt" name="Bt (total field, nT)" stroke={CHART_COLORS.shortwave} dot={false} strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function CMEVelocityChart({ events }: { events: { begin_time: string; velocity_km_s: number | null; type: string }[] }) {
  const data = events
    .filter((e) => e.velocity_km_s != null)
    .map((e) => ({
      time: new Date(e.begin_time).toLocaleDateString(),
      velocity: e.velocity_km_s,
      type: e.type,
    }))
    .reverse();

  return (
    <div className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 12, right: 12, left: 4, bottom: 40 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
          <XAxis dataKey="time" stroke={CHART_COLORS.axis} tick={{ fontSize: 9 }} angle={-45} textAnchor="end" height={60} />
          <YAxis stroke={CHART_COLORS.axis} tick={{ fontSize: 10 }} label={{ value: 'km/s', angle: -90, position: 'insideLeft', fontSize: 10, fill: CHART_COLORS.axis }} />
          <Tooltip contentStyle={tooltipStyle} />
          <Legend />
          <Line type="monotone" dataKey="velocity" name="Shock Velocity (km/s)" stroke={CHART_COLORS.xThreshold} dot={{ r: 3 }} strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function HistoryTimelineChart({ byMonth, color }: { byMonth: Record<string, number>; color: string }) {
  const data = Object.entries(byMonth).map(([month, count]) => ({ month, count }));
  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 40 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
          <XAxis dataKey="month" stroke={CHART_COLORS.axis} tick={{ fontSize: 9 }} angle={-45} textAnchor="end" height={60} interval={Math.max(0, Math.floor(data.length / 20))} />
          <YAxis stroke={CHART_COLORS.axis} tick={{ fontSize: 10 }} allowDecimals={false} />
          <Tooltip contentStyle={tooltipStyle} />
          <Bar dataKey="count" name="Files" fill={color} radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function IntensityChart({ regions }: { regions: { name: string; intensity: number }[] }) {
  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={regions} layout="vertical" margin={{ top: 8, right: 16, left: 8, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
          <XAxis type="number" stroke={CHART_COLORS.axis} />
          <YAxis type="category" dataKey="name" stroke={CHART_COLORS.axis} width={72} tick={{ fontSize: 11 }} />
          <Tooltip contentStyle={tooltipStyle} />
          <Bar dataKey="intensity" fill={CHART_COLORS.longwave} radius={[0, 4, 4, 0]} name="Intensity score" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
