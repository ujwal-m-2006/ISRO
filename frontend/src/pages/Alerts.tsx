import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { DataSourceBadge, FlareClassBadge } from '../components/live';
import { LoadingState, PageHeader, Panel, formatTime, getAlertStyles } from '../components/ui';
import { LIVE_REFRESH_MS, api } from '../services/api';

function Alerts() {
  const alerts = useQuery({ queryKey: ['alerts'], queryFn: api.getAlerts, refetchInterval: LIVE_REFRESH_MS });
  const summary = useQuery({ queryKey: ['live-summary'], queryFn: api.getLiveSummary, refetchInterval: LIVE_REFRESH_MS });

  if (alerts.isLoading) return <LoadingState message="Loading live alerts..." />;

  const list = alerts.data?.alerts ?? [];
  const activeCount = alerts.data?.total_active ?? 0;

  return (
    <div className="space-y-6">
      <PageHeader title="Alerts" subtitle={`${activeCount} active — derived from live GOES flux & NOAA flare catalogue`} statusColor={activeCount > 0 ? 'yellow' : 'green'} />
      <DataSourceBadge source={alerts.data?.data_source} updated={alerts.data?.last_checked} />

      {summary.data && (
        <Panel title="Current Conditions">
          <div className="flex flex-wrap items-center gap-4">
            <FlareClassBadge flareClass={summary.data.current_class} />
            <span className="text-sm text-space-gray">Risk: <span className="text-space-light">{summary.data.risk_level}</span></span>
            <span className="text-sm text-space-gray">Trend 30m: {summary.data.flux_trend_pct_30min}%</span>
          </div>
        </Panel>
      )}

      <div className="space-y-4">
        {list.map((alert) => (
          <div key={alert.id} className={`rounded-xl p-5 border ${getAlertStyles(alert.alert_level)}`}>
            <div className="flex flex-col sm:flex-row sm:justify-between gap-2">
              <div>
                <p className="font-semibold">{alert.alert_type.replace(/_/g, ' ')}</p>
                <p className="text-sm mt-1 opacity-90">{alert.reason}</p>
              </div>
              <div className="text-sm opacity-80 text-right">
                <p>{alert.alert_level}</p>
                <p>{formatTime(alert.timestamp)}</p>
                {alert.confidence != null && <p>{(alert.confidence * 100).toFixed(0)}% confidence</p>}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default Alerts;
