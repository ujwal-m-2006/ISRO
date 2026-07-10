import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { CHART_COLORS, DualFluxChart } from '../components/charts';
import { DataSourceBadge, FlareClassBadge, GlossaryPanel, MeaningBox } from '../components/live';
import { LoadingState, PageHeader, Panel } from '../components/ui';
import { LIVE_REFRESH_MS, api, formatFlux, formatTime } from '../services/api';

function LiveData() {
  const latest = useQuery({ queryKey: ['latest'], queryFn: api.getLatestData, refetchInterval: LIVE_REFRESH_MS });
  const flux = useQuery({ queryKey: ['flux', 6], queryFn: () => api.getFluxHistory(6), refetchInterval: LIVE_REFRESH_MS });
  const glossary = useQuery({ queryKey: ['glossary'], queryFn: api.getGlossary, staleTime: 3600000 });

  if (latest.isLoading) return <LoadingState message="Loading live instrument flux..." />;

  const d = latest.data;
  const points = flux.data?.points ?? [];

  return (
    <div className="space-y-6">
      <PageHeader title="Live Data" subtitle="Real-time GOES-18 X-ray flux — same source as NOAA SWPC & spaceweather.com" status="Streaming" />
      <DataSourceBadge source={d?.data_source} updated={d?.last_updated} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Panel title="SoLEXS Analog — GOES Shortwave (0.05–0.4 nm)">
          <div className="grid grid-cols-2 gap-3 mb-4 text-sm">
            <Metric label="Soft X-ray Flux" value={formatFlux(d?.solexs?.soft_xray_flux)} />
            <Metric label="Energy Band" value={d?.solexs?.energy_band ?? '0.05–0.4 nm'} />
            <Metric label="Status" value={d?.solexs?.instrument_status ?? 'online'} good />
            <Metric label="Last Reading" value={formatTime(d?.solexs?.timestamp)} />
          </div>
          <MeaningBox title="Meaning" text="Soft X-rays from hot coronal plasma (~2–20 MK). Rising flux often precedes flare impulsive phase. Aditya-L1 SoLEXS covers 2–22 keV; GOES shortwave is the operational space-weather proxy." />
        </Panel>

        <Panel title="HEL1OS Analog — GOES Longwave (0.1–0.8 nm)">
          <div className="grid grid-cols-2 gap-3 mb-4 text-sm">
            <Metric label="Longwave Flux" value={formatFlux(d?.hel1os?.hard_xray_flux)} />
            <Metric label="NOAA Class" value={<FlareClassBadge flareClass={d?.hel1os?.current_class ?? 'A0.0'} />} />
            <Metric label="Energy Band" value={d?.hel1os?.energy_band ?? '0.1–0.8 nm'} />
            <Metric label="Last Reading" value={formatTime(d?.hel1os?.timestamp)} />
          </div>
          <MeaningBox title="Meaning" text="NOAA uses this band for official flare classification (A/B/C/M/X). Matches SWPC live plots. Aditya-L1 HEL1OS extends to higher energies (10–150 keV) for hard X-ray diagnostics." />
        </Panel>
      </div>

      <Panel title="Live Flux Timeline">
        <DualFluxChart data={points} thresholds={flux.data?.thresholds} />
        <p className="text-xs text-space-gray mt-2">
          Cyan = shortwave (0.05–0.4 nm) · Orange = longwave (0.1–0.8 nm) · Dashed lines = C/M/X class thresholds
        </p>
      </Panel>

      {glossary.data && (
        <GlossaryPanel title="Instrument & Flux Definitions" items={glossary.data.instruments} />
      )}
    </div>
  );
}

function Metric({ label, value, good }: { label: string; value: React.ReactNode; good?: boolean }) {
  return (
    <div className="bg-space-black rounded-lg p-3 border border-space-blue/20">
      <p className="text-space-gray text-xs">{label}</p>
      <p className={`font-bold mt-1 ${good ? 'text-green-400' : ''}`}>{value}</p>
    </div>
  );
}

export default LiveData;
