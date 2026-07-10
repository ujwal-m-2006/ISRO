import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { CMEVelocityChart } from '../components/charts';
import { DataSourceBadge, FlareClassBadge, MeaningBox } from '../components/live';
import { ErrorState, LoadingState, PageHeader, Panel, StatCard, Tabs } from '../components/ui';
import { LIVE_REFRESH_MS, api, formatTime } from '../services/api';
import type { CMEIndicatorEvent } from '../types';

function ArrivalCard({ e }: { e: CMEIndicatorEvent }) {
  const est = e.arrival_estimate;
  if (!est?.estimable) return null;
  return (
    <div className="rounded-lg border border-red-400/40 bg-red-50 p-4">
      <div className="flex items-center justify-between mb-2">
        <p className="text-sm font-semibold text-red-900">
          {e.type} detected {formatTime(e.begin_time)} — shock velocity {e.velocity_km_s?.toFixed(0)} km/s
        </p>
        {e.associated_flare?.flare_class && (
          <FlareClassBadge flareClass={e.associated_flare.flare_class} />
        )}
      </div>
      {e.associated_flare && (
        <p className="text-xs text-space-gray mb-2">
          Associated flare peaked {e.associated_flare.time_diff_minutes?.toFixed(0)} min from detection — same eruption.
        </p>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm">
        <div>
          <p className="text-xs text-space-gray uppercase">Earliest Plausible</p>
          <p className="font-medium">{formatTime(est.earliest_plausible?.arrival_time)}</p>
        </div>
        <div className="bg-white/50 rounded p-1 -m-1">
          <p className="text-xs text-space-gray uppercase">Nominal Estimate</p>
          <p className="font-bold text-red-800">{formatTime(est.nominal?.arrival_time)}</p>
          <p className="text-xs text-space-gray">{est.nominal?.hours_after_launch}h transit</p>
        </div>
        <div>
          <p className="text-xs text-space-gray uppercase">Latest Plausible</p>
          <p className="font-medium">{formatTime(est.latest_plausible?.arrival_time)}</p>
        </div>
      </div>
      <p className="text-xs text-space-gray mt-3">{est.uncertainty_note}</p>

      {e.donki_cross_check && (
        <div className="mt-3 pt-3 border-t border-red-400/20">
          <p className="text-xs font-semibold text-space-gray uppercase mb-1">Cross-check vs NASA DONKI</p>
          <p className="text-sm">
            NOAA (radio-burst shock): <strong>{e.velocity_km_s?.toFixed(0)} km/s</strong> &middot; DONKI (coronagraph leading-edge): <strong>{e.donki_cross_check.donki_speed_km_s?.toFixed(0)} km/s</strong>
            {e.donki_cross_check.speed_difference_pct != null && <span className="text-space-gray"> ({e.donki_cross_check.speed_difference_pct}% difference)</span>}
          </p>
          <p className="text-xs text-space-gray mt-1">{e.donki_cross_check.note}</p>
        </div>
      )}
    </div>
  );
}

function LiveCMETab() {
  const cme = useQuery({ queryKey: ['cme'], queryFn: api.getCME, refetchInterval: LIVE_REFRESH_MS });
  const indicators = useQuery({ queryKey: ['cme-indicators', 2], queryFn: () => api.getCMEIndicators(2), refetchInterval: LIVE_REFRESH_MS });
  const watches = useQuery({ queryKey: ['storm-watches'], queryFn: api.getStormWatches, refetchInterval: LIVE_REFRESH_MS });

  if (cme.isLoading || indicators.isLoading) return <LoadingState message="Loading live CME data..." />;

  const d = cme.data;
  const ind = indicators.data;
  const activeWatch = watches.data?.latest_current;
  const staleWatch = !activeWatch ? watches.data?.latest : null;

  return (
    <div className="space-y-6">
      <DataSourceBadge source={ind?.data_source} updated={new Date().toISOString()} />

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard label="Radio-Burst CME Detections (48h)" value={ind?.count ?? 0} badge="⚡" accent={ind && ind.count > 0 ? 'from-red-500 to-orange-500' : 'from-space-blue to-space-purple'} />
        <StatCard label="NASA DONKI CMEs (7d)" value={d?.total_cmes ?? 0} badge="CME" />
        <StatCard
          label="Current Storm Watch"
          value={activeWatch?.peak_category ?? 'None active'}
          footer={!activeWatch && staleWatch && (
            <span className="text-xs text-space-gray">Last issued {formatTime(staleWatch.issued)} — expired, no longer in effect</span>
          )}
          badge="G"
          accent={activeWatch ? 'from-yellow-500 to-orange-500' : 'from-space-blue to-space-purple'}
        />
      </div>

      {ind && ind.events.filter((e) => e.arrival_estimate?.estimable).length > 0 && (
        <Panel title="Earth-Arrival Predictions (Drag-Based Model)">
          <div className="space-y-4">
            {ind.events.filter((e) => e.arrival_estimate?.estimable).map((e, i) => (
              <ArrivalCard key={i} e={e} />
            ))}
          </div>
        </Panel>
      )}

      <Panel title="Recent Radio-Burst CME Detections (NOAA, last 48h)">
        {!ind || ind.events.length === 0 ? (
          <p className="text-sm text-space-gray py-8 text-center">No CME-shock radio bursts detected in the last 48 hours — quiet conditions.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-space-gray border-b border-space-blue/20">
                  <th className="pb-2 pr-4">Detected</th>
                  <th className="pb-2 pr-4">Type</th>
                  <th className="pb-2 pr-4">Flare Class</th>
                  <th className="pb-2 pr-4">NOAA Speed</th>
                  <th className="pb-2">DONKI Speed</th>
                </tr>
              </thead>
              <tbody>
                {ind.events.map((e, i) => (
                  <tr key={i} className="border-b border-space-blue/10">
                    <td className="py-2 pr-4">{formatTime(e.begin_time)}</td>
                    <td className="py-2 pr-4">{e.type}</td>
                    <td className="py-2 pr-4">{e.associated_flare?.flare_class ? <FlareClassBadge flareClass={e.associated_flare.flare_class} /> : '—'}</td>
                    <td className="py-2 pr-4">{e.velocity_km_s ? `${e.velocity_km_s.toFixed(0)} km/s` : '—'}</td>
                    <td className="py-2">{e.donki_cross_check?.donki_speed_km_s ? `${e.donki_cross_check.donki_speed_km_s.toFixed(0)} km/s` : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      {d && (
        <Panel title={`NASA DONKI Catalogue (last ${d.window_days} days)`}>
          {d.note && <div className="rounded-lg border border-yellow-400/40 bg-yellow-50 text-yellow-800 p-3 text-sm mb-3">{d.note}</div>}
          {d.events.length === 0 ? (
            <p className="text-sm text-space-gray py-4 text-center">No DONKI events available right now.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-space-gray border-b border-space-blue/20">
                    <th className="pb-2 pr-4">Start</th>
                    <th className="pb-2 pr-4">Speed</th>
                    <th className="pb-2">Earth-Directed</th>
                  </tr>
                </thead>
                <tbody>
                  {d.events.map((e) => (
                    <tr key={e.id} className="border-b border-space-blue/10">
                      <td className="py-2 pr-4">{formatTime(e.start_time)}</td>
                      <td className="py-2 pr-4">{e.speed_km_s ? `${e.speed_km_s.toFixed(0)} km/s` : '—'}</td>
                      <td className="py-2">{e.earth_directed ? 'Yes' : 'No'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>
      )}
    </div>
  );
}

function HistoricalCMETab() {
  const indicators = useQuery({ queryKey: ['cme-indicators', 90], queryFn: () => api.getCMEIndicators(90) });

  if (indicators.isLoading) return <LoadingState message="Loading historical CME detections..." />;
  if (indicators.isError) return <ErrorState message="Could not reach the CME indicators endpoint." />;

  const d = indicators.data!;

  return (
    <div className="space-y-6">
      <DataSourceBadge source={d.data_source} updated={new Date().toISOString()} />
      <StatCard label="Radio-Burst CME Detections (90 days)" value={d.count} badge="⚡" />

      <Panel title="Shock Velocity Over Time">
        {d.events.length === 0 ? (
          <p className="text-sm text-space-gray py-8 text-center">No events in this window.</p>
        ) : (
          <CMEVelocityChart events={d.events} />
        )}
      </Panel>

      <Panel title="All Detections (90 days)">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-space-gray border-b border-space-blue/20">
                <th className="pb-2 pr-4">Detected</th>
                <th className="pb-2 pr-4">Type</th>
                <th className="pb-2 pr-4">Flare Class</th>
                <th className="pb-2 pr-4">NOAA Speed</th>
                <th className="pb-2">DONKI Speed</th>
              </tr>
            </thead>
            <tbody>
              {d.events.map((e, i) => (
                <tr key={i} className="border-b border-space-blue/10">
                  <td className="py-2 pr-4">{formatTime(e.begin_time)}</td>
                  <td className="py-2 pr-4">{e.type}</td>
                  <td className="py-2 pr-4">{e.associated_flare?.flare_class ? <FlareClassBadge flareClass={e.associated_flare.flare_class} /> : '—'}</td>
                  <td className="py-2 pr-4">{e.velocity_km_s ? `${e.velocity_km_s.toFixed(0)} km/s` : '—'}</td>
                  <td className="py-2">{e.donki_cross_check?.donki_speed_km_s ? `${e.donki_cross_check.donki_speed_km_s.toFixed(0)} km/s` : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}

function CMETracker() {
  return (
    <div className="space-y-6">
      <PageHeader title="Coronal Mass Ejection (CME) Tracker" subtitle="NOAA radio-burst shock detection + NASA DONKI catalogue" status="Live" />

      <Tabs
        tabs={[
          { id: 'live', label: 'Live', content: <LiveCMETab /> },
          { id: 'historical', label: 'Historical (90 days)', content: <HistoricalCMETab /> },
        ]}
      />

      <MeaningBox
        title="Why CMEs matter"
        text="CMEs are billion-ton clouds of magnetized plasma ejected from the Sun. A Type II radio burst indicates a CME-driven shock wave has formed — its estimated velocity feeds our Drag-Based Model arrival prediction. Earth-directed CMEs typically take 1-5 days to arrive and, on impact, can trigger geomagnetic storms — see the Earth Impact page for the current storm-scale forecast."
      />
    </div>
  );
}

export default CMETracker;
