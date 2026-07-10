import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { HistoryTimelineChart } from '../components/charts';
import { ErrorState, LoadingState, PageHeader, Panel } from '../components/ui';
import { formatTime, api } from '../services/api';

function InstrumentArchive({ name, color, data }: { name: string; color: string; data: { files: any[]; summary: any } | undefined }) {
  if (!data) return null;
  const { summary, files } = data;
  const recent = [...files].reverse().slice(0, 10);

  return (
    <Panel title={`${name} — Full Mission Archive`}>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
        <div>
          <p className="text-xs text-space-gray uppercase">Total Files</p>
          <p className="text-2xl font-bold">{summary.count}</p>
        </div>
        <div>
          <p className="text-xs text-space-gray uppercase">Earliest</p>
          <p className="text-sm font-medium">{formatTime(summary.earliest)}</p>
        </div>
        <div>
          <p className="text-xs text-space-gray uppercase">Latest</p>
          <p className="text-sm font-medium">{formatTime(summary.latest)}</p>
        </div>
      </div>
      <HistoryTimelineChart byMonth={summary.by_month} color={color} />
      <p className="text-xs text-space-gray mt-3 mb-2">Most recent 10 files (of {summary.count} total):</p>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-left text-space-gray border-b border-space-blue/20">
              <th className="pb-1 pr-3">Filename</th>
              <th className="pb-1 pr-3">Observation Start</th>
              <th className="pb-1">Size</th>
            </tr>
          </thead>
          <tbody>
            {recent.map((f) => (
              <tr key={f.url} className="border-b border-space-blue/10">
                <td className="py-1 pr-3"><a href={f.url} target="_blank" rel="noreferrer" className="text-space-blue hover:underline break-all">{f.filename}</a></td>
                <td className="py-1 pr-3">{formatTime(f.start_time)}</td>
                <td className="py-1">{f.size_kb ? `${Number(f.size_kb).toFixed(0)} KB` : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}

function HistoricalArchive() {
  const history = useQuery({ queryKey: ['pradan-history'], queryFn: api.getPradanHistory });

  if (history.isLoading) return <LoadingState message="Loading full-mission archive..." />;
  if (history.isError) return <ErrorState message="Could not reach the PRADAN history endpoint." />;

  const d = history.data!;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Aditya-L1 Historical Archive"
        subtitle="Full-mission SoLEXS & HEL1OS data catalogue from PRADAN, launch to date"
        status={d.authenticated ? 'Connected' : 'Not connected'}
        statusColor={d.authenticated ? 'green' : 'yellow'}
      />

      {!d.authenticated && (
        <div className="rounded-xl border border-yellow-400/40 bg-yellow-50 text-yellow-800 p-4 text-sm">
          {d.error ?? 'PRADAN is not connected — historical archive unavailable.'}
        </div>
      )}

      {d.authenticated && (
        <>
          <InstrumentArchive name="SoLEXS" color="#0e7490" data={d.instruments.solexs} />
          <InstrumentArchive name="HEL1OS" color="#c2410c" data={d.instruments.hel1os} />
        </>
      )}

      <div className="rounded-xl border border-space-blue/20 bg-space-dark p-4 text-xs text-space-gray">
        This archive is refreshed once daily from PRADAN's real data-product catalogue (not simulated). Monthly counts
        reflect actual file publication cadence — SoLEXS publishes roughly daily, HEL1OS roughly twice-daily.
      </div>
    </div>
  );
}

export default HistoricalArchive;
