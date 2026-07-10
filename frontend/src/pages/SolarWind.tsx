import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { SolarWindSpeedChart, SolarWindFieldChart } from '../components/charts';
import { DataSourceBadge, MeaningBox } from '../components/live';
import { LoadingState, PageHeader, Panel, StatCard } from '../components/ui';
import { LIVE_REFRESH_MS, api } from '../services/api';

function SolarWind() {
  const summary = useQuery({ queryKey: ['solar-wind'], queryFn: api.getSolarWind, refetchInterval: LIVE_REFRESH_MS });
  const history = useQuery({ queryKey: ['solar-wind-history'], queryFn: api.getSolarWindHistory, refetchInterval: LIVE_REFRESH_MS });

  if (summary.isLoading) return <LoadingState message="Loading solar wind telemetry..." />;

  const d = summary.data;
  const points = history.data?.points ?? [];

  return (
    <div className="space-y-6">
      <PageHeader title="Solar Wind (ASPEX / MAG proxy)" subtitle="Live upstream solar wind plasma and magnetic field at the L1 point" status="Live" />
      <DataSourceBadge source={d?.data_source} updated={d?.last_update} />

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard label="Solar Wind Speed" value={d?.speed_km_s ? `${d.speed_km_s.toFixed(0)} km/s` : '—'} badge="V" />
        <StatCard label="Proton Density" value={d?.density_p_cm3 ? `${d.density_p_cm3.toFixed(2)} p/cm³` : '—'} badge="N" accent="from-cyan-500 to-blue-500" />
        <StatCard label="IMF Bz (south = storm risk)" value={d?.bz_nt != null ? `${d.bz_nt.toFixed(1)} nT` : '—'} badge="Bz" accent={d?.bz_south_alert ? 'from-red-500 to-orange-500' : 'from-space-blue to-space-purple'} />
        <StatCard label="Planetary Kp Index" value={d?.kp_index != null ? d.kp_index.toFixed(1) : '—'} footer={<span className="text-xs text-space-gray">{d?.kp_activity}</span>} badge="Kp" accent="from-purple-500 to-pink-500" />
      </div>

      {d?.bz_south_alert && (
        <MeaningBox
          title="Southward IMF detected"
          text="Bz is pointing south (negative) below -5 nT — this favors magnetic reconnection with Earth's magnetosphere and raises the chance of geomagnetic storming. Check the Earth Impact page for the current G-scale forecast."
        />
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Panel title="Solar Wind Speed & Density">
          {history.isLoading ? <LoadingState /> : <SolarWindSpeedChart points={points} />}
        </Panel>
        <Panel title="Interplanetary Magnetic Field (Bz / Bt)">
          {history.isLoading ? <LoadingState /> : <SolarWindFieldChart points={points} />}
        </Panel>
      </div>

      <MeaningBox
        title="What is this standing in for?"
        text="Aditya-L1's ASPEX (solar wind particles) and Magnetometer payloads measure these same quantities at L1, but don't publish real-time data. This panel uses NOAA's real-time solar wind product (sourced from the DSCOVR spacecraft, the modern successor to the historical ACE real-time feed) as a live proxy until PRADAN access is added."
      />
    </div>
  );
}

export default SolarWind;
