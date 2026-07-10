import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { ForecastProbabilityChart } from '../components/charts';
import { DataSourceBadge, MeaningBox } from '../components/live';
import { LoadingState, PageHeader, Panel, StatCard } from '../components/ui';
import { LIVE_REFRESH_MS, api } from '../services/api';

function ModelPerformance() {
  const forecast = useQuery({ queryKey: ['forecast'], queryFn: api.getForecasts, refetchInterval: LIVE_REFRESH_MS });
  const status = useQuery({ queryKey: ['status'], queryFn: api.getStatus, refetchInterval: LIVE_REFRESH_MS });

  if (forecast.isLoading) return <LoadingState message="Loading forecast engine status..." />;

  const predictions = forecast.data?.predictions ?? [];
  const chartData = predictions.map((p) => ({
    horizon: p.time_horizon,
    c: p.c_class_chance_pct ?? 0,
    m: p.m_class_chance_pct ?? 0,
    x: p.x_class_chance_pct ?? 0,
  }));

  return (
    <div className="space-y-6">
      <PageHeader title="Forecast Engine Performance" subtitle="Live NOAA-driven auto-forecast — updates every 60s without manual input" status="Active" />
      <DataSourceBadge source={forecast.data?.data_source} updated={forecast.data?.last_updated} />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard label="Data Feed" value="NOAA SWPC" badge="NOAA" />
        <StatCard label="Refresh Rate" value="60 sec" badge="↻" accent="from-green-500 to-teal-500" />
        <StatCard label="Horizons" value={`${predictions.length} windows`} badge="T" accent="from-purple-500 to-pink-500" />
      </div>

      <MeaningBox title="Engine methodology" text={forecast.data?.methodology ?? ''} />

      <Panel title="Probability Output by Horizon">
        <ForecastProbabilityChart data={chartData} />
      </Panel>

      <Panel title="System Services">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {status.data &&
            Object.entries(status.data.services).map(([service, state]) => (
              <div key={service} className="flex justify-between bg-space-black rounded-lg px-4 py-3 border border-space-blue/20 text-sm">
                <span className="capitalize">{service.replace(/_/g, ' ')}</span>
                <span className="text-green-400">{state}</span>
              </div>
            ))}
        </div>
      </Panel>
    </div>
  );
}

export default ModelPerformance;
