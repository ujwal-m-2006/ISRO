import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { DataSourceBadge } from '../components/live';
import { LoadingState, PageHeader, Panel } from '../components/ui';
import { LIVE_REFRESH_MS, api } from '../services/api';

function Settings() {
  const status = useQuery({ queryKey: ['status'], queryFn: api.getStatus, refetchInterval: LIVE_REFRESH_MS });
  const summary = useQuery({ queryKey: ['live-summary'], queryFn: api.getLiveSummary, refetchInterval: LIVE_REFRESH_MS });
  const jobs = useQuery({ queryKey: ['jobs'], queryFn: api.getJobStatus, refetchInterval: LIVE_REFRESH_MS });

  if (status.isLoading) return <LoadingState message="Loading system status..." />;

  return (
    <div className="space-y-6">
      <PageHeader title="Settings" subtitle="Live data configuration — fully automatic" />
      <DataSourceBadge source={summary.data?.data_source} updated={summary.data?.last_update} />

      <Panel title="Automatic Refresh">
        <p className="text-sm text-space-gray">
          All tabs pull live NOAA SWPC data every <strong className="text-space-light">60 seconds</strong>.
          Forecasting and nowcasting run automatically — no manual input needed.
        </p>
      </Panel>

      <Panel title="System Status">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {status.data &&
            Object.entries(status.data.services).map(([service, state]) => (
              <div key={service} className="flex items-center justify-between bg-space-black rounded-lg px-4 py-3 border border-space-blue/20">
                <span className="text-sm capitalize">{service.replace(/_/g, ' ')}</span>
                <span className="text-sm text-green-400">{state}</span>
              </div>
            ))}
        </div>
      </Panel>

      <Panel title="Cron Job Schedule (UTC)">
        <ul className="text-sm text-space-gray space-y-1">
          <li><span className="text-cyan-400">fetch_flux</span> — every 1 minute</li>
          <li><span className="text-cyan-400">fetch_summary</span> — every 1 minute</li>
          <li><span className="text-purple-400">fetch_nowcast / forecast / alerts</span> — every 5 minutes</li>
          <li><span className="text-orange-400">fetch_flares</span> — every 10 minutes</li>
          <li><span className="text-yellow-400">fetch_regions</span> — every 15 minutes</li>
          <li><span className="text-green-400">full_sync</span> — every hour at :00</li>
        </ul>
      </Panel>

      {jobs.data && (
        <Panel title="Cron Job Run History">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-space-gray border-b border-space-blue/20">
                  <th className="pb-2 pr-4">Job</th>
                  <th className="pb-2 pr-4">Last Run</th>
                  <th className="pb-2 pr-4">Status</th>
                  <th className="pb-2 pr-4">Detail</th>
                  <th className="pb-2">Duration</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(jobs.data.jobs).map(([name, job]) => (
                  <tr key={name} className="border-b border-space-blue/10">
                    <td className="py-2 pr-4 font-mono text-space-cyan">{name}</td>
                    <td className="py-2 pr-4">{new Date(job.last_run).toLocaleString()}</td>
                    <td className={`py-2 pr-4 ${job.success ? 'text-green-400' : 'text-red-400'}`}>{job.success ? 'OK' : 'FAIL'}</td>
                    <td className="py-2 pr-4 text-space-gray">{job.detail}</td>
                    <td className="py-2">{job.duration_ms}ms</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      )}

      <Panel title="Live API Endpoints">
        <ul className="text-sm text-space-gray space-y-1 font-mono">
          <li>GET /api/v1/live/summary — current GOES flux & class</li>
          <li>GET /api/v1/live/flux — flux time series</li>
          <li>GET /api/v1/live/flares — 7-day flare list</li>
          <li>GET /api/v1/live/regions — active regions + probabilities</li>
          <li>GET /api/v1/nowcast — automated nowcast</li>
          <li>GET /api/v1/jobs/status — cron job run history</li>
        </ul>
      </Panel>
    </div>
  );
}

export default Settings;
