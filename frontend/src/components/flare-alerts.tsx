import React, { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import type { FlareAlert, FlareAlertsResponse } from '../types';
import { DualFluxChart } from './charts';
import { StatCard } from './ui';
import { api, FLARE_ALERTS_REFRESH_MS, formatFlux, LIVE_REFRESH_MS } from '../services/api';

// Severity color coding — matches spec: A/B green, C yellow, M orange, X red.
export function severityBadgeClasses(severity: string) {
  switch (severity) {
    case 'Low':
      return 'bg-green-100 text-green-800 border-green-400/60';
    case 'Moderate':
      return 'bg-yellow-100 text-yellow-800 border-yellow-400/60';
    case 'High':
      return 'bg-orange-100 text-orange-800 border-orange-400/60';
    case 'Severe':
      return 'bg-red-100 text-red-800 border-red-400/60';
    case 'Extreme':
      return 'bg-red-200 text-red-900 border-red-600/70 shadow-[0_0_10px_rgba(220,38,38,0.5)]';
    default:
      return 'bg-space-blue/10 text-space-blue border-space-blue/30';
  }
}

function statusDotColor(status: string) {
  switch (status) {
    case 'Increasing':
      return 'bg-red-500 animate-pulse';
    case 'Decaying':
      return 'bg-orange-500';
    default:
      return 'bg-space-gray';
  }
}

function fmtTime(iso: string | null) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString(undefined, { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: 'UTC', timeZoneName: 'short' });
}

// --- 1. Live scrolling alert ticker (site-wide, sticky under nav) ----------

export function FlareAlertTicker({ onSelect }: { onSelect: (alert: FlareAlert) => void }) {
  const { data } = useQuery({ queryKey: ['flare-alerts'], queryFn: api.getFlareAlerts, refetchInterval: FLARE_ALERTS_REFRESH_MS });
  const items = data?.ticker_alerts ?? [];

  if (!data) return null;

  if (items.length === 0) {
    return (
      <div className="bg-isro-navy-dark border-b border-space-blue/30 text-white/80 text-xs px-4 py-1.5 text-center">
        No significant solar flare activity detected at this time. Last updated: {new Date(data.last_updated).toLocaleTimeString()}
      </div>
    );
  }

  const loop = [...items, ...items]; // duplicated for a seamless marquee loop

  return (
    <div className="bg-isro-navy-dark border-b border-space-blue/30 overflow-hidden group">
      <div className="flex items-center">
        <span className="shrink-0 bg-red-600 text-white text-[11px] font-bold uppercase tracking-wide px-3 py-1.5 z-10">Flare Alerts</span>
        <div className="overflow-hidden flex-1">
          <div className="flex animate-marquee whitespace-nowrap group-hover:[animation-play-state:paused]">
            {loop.map((a, i) => (
              <button
                key={`${a.id}-${i}`}
                type="button"
                onClick={() => onSelect(a)}
                className="inline-flex items-center gap-2 px-4 py-1.5 text-xs shrink-0 border-l border-white/10 hover:bg-white/10 transition-colors text-white"
              >
                <span className={`w-1.5 h-1.5 rounded-full ${statusDotColor(a.status)}`} />
                <span className={`px-1.5 py-0.5 rounded font-bold border ${severityBadgeClasses(a.severity)}`}>{a.flare_class}</span>
                <span className="text-white/90">{a.active_region ? a.active_region.split(' ')[0] : 'Region N/A'}</span>
                <span className="text-white/60">{fmtTime(a.peak_time)}</span>
                <span className="text-white/70">{a.status}</span>
                {a.radio_scale !== 'R0' && <span className="text-white/70">{a.radio_scale}</span>}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// --- 3+7. Dashboard summary cards -------------------------------------------

export function FlareDashboardCards({ data }: { data: FlareAlertsResponse }) {
  const s = data.summary;
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
      <StatCard label="Flares Today" value={s.total_flares_today} badge="24H" />
      <StatCard label="Strongest Flare" value={s.strongest_flare ?? '—'} badge="MAX" accent="from-red-600 to-orange-500" />
      <StatCard label="Activity Level" value={s.current_activity_level} badge="LVL" />
      <StatCard label="Active Regions" value={s.active_regions_count} badge="AR" />
      <StatCard label="Latest Flare" value={s.latest_flare ?? '—'} badge="NEW" />
      <StatCard label="Radio Blackout" value={s.radio_blackout_level} badge="R" accent="from-space-purple to-space-fuchsia" />
    </div>
  );
}

// --- 8. Detail modal ---------------------------------------------------------

export function FlareDetailModal({ alert, onClose }: { alert: FlareAlert; onClose: () => void }) {
  const flux = useQuery({ queryKey: ['flux-6h-modal'], queryFn: () => api.getFluxHistory(6), refetchInterval: LIVE_REFRESH_MS });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60" onClick={onClose}>
      <div
        className="bg-space-dark border border-space-blue/30 rounded-xl max-w-2xl w-full max-h-[85vh] overflow-y-auto p-6 space-y-5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className={`px-2.5 py-1 rounded-md border text-lg font-bold ${severityBadgeClasses(alert.severity)}`}>{alert.flare_class}</span>
              <span className={`px-2 py-0.5 rounded text-xs font-semibold border ${severityBadgeClasses(alert.severity)}`}>{alert.severity}</span>
            </div>
            <p className="text-space-gray text-sm mt-1">{alert.description}</p>
          </div>
          <button type="button" onClick={onClose} className="text-space-gray hover:text-space-light text-xl leading-none px-2">×</button>
        </div>

        <div className="grid grid-cols-2 gap-3 text-sm">
          <div><span className="text-space-gray">Active Region</span><p className="font-medium">{alert.active_region ?? 'Not specified by NOAA'}</p></div>
          <div><span className="text-space-gray">Status</span><p className="font-medium">{alert.status}</p></div>
          <div><span className="text-space-gray">Start Time (UTC)</span><p className="font-medium">{fmtTime(alert.start_time)}</p></div>
          <div><span className="text-space-gray">Peak Time (UTC)</span><p className="font-medium">{fmtTime(alert.peak_time)}</p></div>
          <div><span className="text-space-gray">End Time (UTC)</span><p className="font-medium">{fmtTime(alert.end_time)}</p></div>
          <div><span className="text-space-gray">Peak Flux</span><p className="font-medium">{formatFlux(alert.peak_flux_wm2 ?? undefined)}</p></div>
          <div><span className="text-space-gray">Duration</span><p className="font-medium">{alert.duration_minutes != null ? `${alert.duration_minutes} min` : '—'}</p></div>
          <div><span className="text-space-gray">Radio Blackout Scale</span><p className="font-medium">{alert.radio_scale}</p></div>
        </div>

        <div>
          <p className="text-sm font-semibold text-space-light mb-2">Potential Impact</p>
          {alert.impact.length === 0 ? (
            <p className="text-sm text-space-gray">No significant radio, satellite, GPS, or aviation impact expected at this class.</p>
          ) : (
            <ul className="space-y-1 text-sm text-space-gray list-disc list-inside">
              {alert.impact.map((imp) => <li key={imp}>{imp}</li>)}
            </ul>
          )}
        </div>

        <div>
          <p className="text-sm font-semibold text-space-light mb-2">Recent X-ray Flux (last 6h, live GOES)</p>
          {flux.data ? <DualFluxChart data={flux.data.points} thresholds={flux.data.thresholds} /> : <p className="text-sm text-space-gray">Loading flux chart...</p>}
          <p className="text-xs text-space-gray mt-1">Shows current live flux, not necessarily this specific event's window — NOAA doesn't publish a per-flare flux replay feed.</p>
        </div>
      </div>
    </div>
  );
}

// --- 2+5+6. Notice board with filters + search -------------------------------

const SEVERITIES = ['Low', 'Moderate', 'High', 'Severe', 'Extreme'];
const CLASSES = ['A', 'B', 'C', 'M', 'X'];
const STATUSES = ['Increasing', 'Decaying', 'Ended'];

export function FlareNoticeBoard({ onSelect }: { onSelect: (alert: FlareAlert) => void }) {
  const { data, isLoading, isError } = useQuery({ queryKey: ['flare-alerts'], queryFn: api.getFlareAlerts, refetchInterval: FLARE_ALERTS_REFRESH_MS });
  const [search, setSearch] = useState('');
  const [classFilter, setClassFilter] = useState('');
  const [severityFilter, setSeverityFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [dateFilter, setDateFilter] = useState('');

  const alerts = data?.alerts ?? [];

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return alerts.filter((a) => {
      if (classFilter && a.flare_class[0] !== classFilter) return false;
      if (severityFilter && a.severity !== severityFilter) return false;
      if (statusFilter && a.status !== statusFilter) return false;
      if (dateFilter && !(a.start_time ?? '').startsWith(dateFilter)) return false;
      if (q && !(`${a.id} ${a.flare_class} ${a.active_region ?? ''}`.toLowerCase().includes(q))) return false;
      return true;
    });
  }, [alerts, search, classFilter, severityFilter, statusFilter, dateFilter]);

  if (isLoading) return <p className="text-space-gray text-sm">Loading solar flare notices...</p>;
  if (isError) return <p className="text-red-600 text-sm">Live solar flare data is temporarily unavailable.</p>;
  if (!data) return null;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2 items-center">
        <input
          type="text"
          placeholder="Search by ID, class, or region..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 min-w-[200px] px-3 py-2 text-sm rounded-lg border border-space-blue/20 bg-white"
        />
        <select value={classFilter} onChange={(e) => setClassFilter(e.target.value)} className="px-2 py-2 text-sm rounded-lg border border-space-blue/20 bg-white">
          <option value="">All Classes</option>
          {CLASSES.map((c) => <option key={c} value={c}>{c}-class</option>)}
        </select>
        <select value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value)} className="px-2 py-2 text-sm rounded-lg border border-space-blue/20 bg-white">
          <option value="">All Severities</option>
          {SEVERITIES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="px-2 py-2 text-sm rounded-lg border border-space-blue/20 bg-white">
          <option value="">All Statuses</option>
          {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <input type="date" value={dateFilter} onChange={(e) => setDateFilter(e.target.value)} className="px-2 py-2 text-sm rounded-lg border border-space-blue/20 bg-white" />
      </div>

      {filtered.length === 0 ? (
        <p className="text-sm text-space-gray py-6 text-center">No significant solar flare activity detected at this time. Last updated: {new Date(data.last_updated).toLocaleString()}</p>
      ) : (
        <div className="space-y-3">
          {filtered.slice(0, 20).map((a) => (
            <div key={a.id} className="rounded-xl border border-space-blue/20 bg-white p-4 flex flex-col sm:flex-row sm:items-center gap-3 justify-between">
              <div className="flex items-start gap-3">
                <span className={`shrink-0 px-2.5 py-1 rounded-md border text-base font-bold ${severityBadgeClasses(a.severity)}`}>{a.flare_class}</span>
                <div>
                  <p className="font-semibold text-space-light">{a.flare_class}-class Solar Flare Detected</p>
                  <p className="text-xs text-space-gray mt-0.5">{fmtTime(a.start_time)} · {a.active_region ?? 'Region not specified'} · {a.status}</p>
                  <p className="text-sm text-space-gray mt-1">{a.description}</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => onSelect(a)}
                className="shrink-0 self-start sm:self-center px-3 py-1.5 text-xs font-semibold rounded-md border border-space-blue text-space-blue hover:bg-space-blue hover:text-white transition-colors"
              >
                Read More →
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
