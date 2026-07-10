import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { HistoryTimelineChart } from '../components/charts';
import { ErrorState, LoadingState, PageHeader, Panel, Tabs } from '../components/ui';
import { formatTime, api } from '../services/api';
import type { PradanHistoryInstrument, SatellitePayload } from '../types';

const PAYLOAD_COLORS: Record<string, string> = {
  VELC: '#7e22ce',
  SUIT: '#0e7490',
  SoLEXS: '#0e7490',
  HEL1OS: '#c2410c',
  ASPEX: '#1a3d8f',
  PAPA: '#a16207',
  Magnetometer: '#15803d',
};

function LivePanel({ payload }: { payload: SatellitePayload }) {
  if (!payload.proxy_available) {
    return (
      <div className="rounded-lg border border-gray-300 bg-gray-50 p-4 text-sm text-space-gray">
        No public real-time proxy exists for {payload.code} — {payload.note}
      </div>
    );
  }
  return (
    <div className="rounded-lg border border-green-400/40 bg-green-50 p-4">
      <p className="text-sm font-semibold text-green-800 mb-1">Live proxy active</p>
      <p className="text-sm text-space-gray">{payload.proxy_source}</p>
      <p className="text-xs text-space-gray mt-2 italic">{payload.note}</p>
    </div>
  );
}

function HistoricalPanel({ payload, instrument }: { payload: SatellitePayload; instrument: PradanHistoryInstrument | undefined }) {
  if (!payload.archive_available || !instrument) {
    return <p className="text-sm text-space-gray py-6 text-center">No PRADAN archive data loaded yet for {payload.code}.</p>;
  }
  const recent = [...instrument.files].reverse().slice(0, 8);
  const isHighCadence = ['VELC', 'SUIT', 'ASPEX'].includes(payload.code);
  return (
    <div className="space-y-4">
      {isHighCadence && (
        <p className="text-xs text-yellow-800 bg-yellow-50 border border-yellow-400/40 rounded px-3 py-2">
          This instrument images far more frequently than others — showing the most recent ~1,500 files rather than the full multi-year archive, to avoid excessive load on PRADAN's server.
        </p>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div>
          <p className="text-xs text-space-gray uppercase">Total Files</p>
          <p className="text-xl font-bold">{payload.archive_file_count}</p>
        </div>
        <div>
          <p className="text-xs text-space-gray uppercase">Earliest</p>
          <p className="text-sm font-medium">{formatTime(payload.archive_earliest ?? undefined)}</p>
        </div>
        <div>
          <p className="text-xs text-space-gray uppercase">Latest</p>
          <p className="text-sm font-medium">{formatTime(payload.archive_latest ?? undefined)}</p>
        </div>
      </div>
      <HistoryTimelineChart byMonth={instrument.summary.by_month} color={PAYLOAD_COLORS[payload.code] ?? '#1a3d8f'} />
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-left text-space-gray border-b border-space-blue/20">
              <th className="pb-1 pr-3">Filename</th>
              <th className="pb-1">Observation Start</th>
            </tr>
          </thead>
          <tbody>
            {recent.map((f) => (
              <tr key={f.url} className="border-b border-space-blue/10">
                <td className="py-1 pr-3"><a href={f.url} target="_blank" rel="noreferrer" className="text-space-blue hover:underline break-all">{f.filename}</a></td>
                <td className="py-1">{formatTime(f.start_time)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Satellites() {
  const roster = useQuery({ queryKey: ['satellite-roster'], queryFn: api.getSatelliteRoster });
  const history = useQuery({ queryKey: ['pradan-history'], queryFn: api.getPradanHistory });

  if (roster.isLoading) return <LoadingState message="Loading satellite roster..." />;
  if (roster.isError) return <ErrorState message="Could not reach the satellite roster endpoint." />;

  const d = roster.data!;
  const instruments = history.data?.instruments ?? {};

  return (
    <div className="space-y-6">
      <PageHeader
        title={`${d.mission} Payload Roster`}
        subtitle={`${d.agency} — ${d.payload_count} instruments · ${d.proxied_count} live proxy · ${d.archived_count} with real PRADAN archive`}
      />

      <div className="rounded-xl border border-space-blue/20 bg-space-dark p-4 text-sm text-space-gray">
        {d.disclosure}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {d.payloads.map((p) => {
          // ASPEX has two PRADAN ids (swis+steps); merge their file lists for the historical tab.
          const merged: PradanHistoryInstrument | undefined = p.pradan_ids.length > 1
            ? p.pradan_ids.reduce<PradanHistoryInstrument | undefined>((acc, id) => {
                const inst = instruments[id];
                if (!inst) return acc;
                if (!acc) return inst;
                return { files: [...acc.files, ...inst.files], summary: acc.summary };
              }, undefined)
            : instruments[p.pradan_ids[0]];

          return (
            <div key={p.code} className="bg-space-dark rounded-xl p-5 border border-space-blue/20">
              <div className="flex items-center justify-between mb-1">
                <h3 className="font-bold text-lg">{p.code}</h3>
                <div className="flex gap-1">
                  {p.proxy_available && <span className="px-2 py-0.5 rounded-md bg-green-100 text-green-800 border border-green-400/50 text-xs font-semibold">Live</span>}
                  {p.archive_available && <span className="px-2 py-0.5 rounded-md bg-blue-100 text-blue-800 border border-blue-400/50 text-xs font-semibold">{p.archive_file_count} archived</span>}
                </div>
              </div>
              <p className="text-sm font-medium text-space-light mb-1">{p.name}</p>
              <p className="text-sm text-space-gray mb-3">{p.measures}</p>

              <Tabs
                tabs={[
                  { id: 'live', label: 'Live', content: <LivePanel payload={p} /> },
                  { id: 'historical', label: 'Past Data', content: <HistoricalPanel payload={p} instrument={merged} /> },
                ]}
              />
            </div>
          );
        })}
      </div>

      <Panel title="Real Aditya-L1 Data Access (PRADAN)">
        <p className="text-sm text-space-gray leading-relaxed">
          All seven payloads' real archives are reachable via ISRO's PRADAN portal (
          <a href="https://pradan1.issdc.gov.in/al1/" target="_blank" rel="noreferrer" className="text-space-blue hover:underline">
            pradan1.issdc.gov.in/al1
          </a>
          ) once authenticated. The "Past Data" tab above shows each instrument's real backfilled file catalogue —
          refreshed once daily. Only 4 payloads have a public live-data equivalent (see "Live" tab); VELC, SUIT, and
          PAPA have no real-time public proxy but their genuine archival history is fully browsable above.
        </p>
      </Panel>
    </div>
  );
}

export default Satellites;
