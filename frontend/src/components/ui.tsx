import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';

export function Tabs({ tabs, defaultTab }: { tabs: { id: string; label: string; content: React.ReactNode }[]; defaultTab?: string }) {
  const [active, setActive] = useState(defaultTab ?? tabs[0]?.id);
  const activeTab = tabs.find((t) => t.id === active) ?? tabs[0];
  return (
    <div>
      <div className="flex gap-1 border-b border-space-blue/20 mb-4 overflow-x-auto">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setActive(t.id)}
            className={`px-4 py-2 text-sm font-semibold whitespace-nowrap border-b-2 transition-colors ${
              active === t.id ? 'border-space-blue text-space-blue' : 'border-transparent text-space-gray hover:text-space-light'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
      {activeTab?.content}
    </div>
  );
}

const navigationItems = [
  { name: 'Dashboard', path: '/', icon: '🏠' },
  { name: 'Live Data', path: '/live-data', icon: '📡' },
  { name: 'Nowcasting', path: '/nowcasting', icon: '⚡' },
  { name: 'Forecasting', path: '/forecasting', icon: '📈' },
  { name: 'Historical Analysis', path: '/historical', icon: '📊' },
  { name: 'Solar Analytics', path: '/analytics', icon: '🔬' },
  { name: 'AI Model Performance', path: '/model-performance', icon: '🤖' },
  { name: 'Alerts', path: '/alerts', icon: '🔔' },
  { name: 'Settings', path: '/settings', icon: '⚙️' },
  { name: 'About', path: '/about', icon: 'ℹ️' },
];

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  status?: string;
  statusColor?: 'green' | 'yellow' | 'red';
}

export function PageHeader({ title, subtitle, status, statusColor = 'green' }: PageHeaderProps) {
  const dotColor = {
    green: 'bg-green-500',
    yellow: 'bg-yellow-500',
    red: 'bg-red-500',
  }[statusColor];

  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-space-light">{title}</h2>
        {subtitle && <p className="text-sm text-space-gray mt-1">{subtitle}</p>}
      </div>
      {status && (
        <div className="flex items-center space-x-2 text-sm text-space-gray">
          <div className={`w-2 h-2 ${dotColor} rounded-full animate-pulse`} />
          <span>{status}</span>
        </div>
      )}
    </div>
  );
}

interface StatCardProps {
  label: string;
  value: React.ReactNode;
  footer?: React.ReactNode;
  badge?: string;
  accent?: string;
}

export function StatCard({ label, value, footer, badge, accent = 'from-space-blue to-space-purple' }: StatCardProps) {
  return (
    <div className="bg-space-dark rounded-xl p-6 border border-space-blue/20 hover:border-space-blue/40 transition-colors">
      <div className="flex items-center justify-between">
        <div className="min-w-0">
          <p className="text-space-gray text-sm font-medium">{label}</p>
          <p className="text-2xl font-bold mt-1 truncate">{value}</p>
        </div>
        {badge && (
          <div className={`w-12 h-12 bg-gradient-to-br ${accent} rounded-lg flex items-center justify-center shrink-0`}>
            <span className="font-bold text-xs text-white">{badge}</span>
          </div>
        )}
      </div>
      {footer && <div className="mt-4 pt-4 border-t border-space-blue/20">{footer}</div>}
    </div>
  );
}

export function Panel({ title, children, action }: { title: string; children: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div className="bg-space-dark rounded-xl p-6 border border-space-blue/20">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-space-light">{title}</h3>
        {action}
      </div>
      {children}
    </div>
  );
}

export function LoadingState({ message = 'Loading data...' }: { message?: string }) {
  return (
    <div className="flex items-center justify-center py-16">
      <div className="text-center">
        <div className="w-12 h-12 bg-space-blue rounded-full mx-auto mb-3 animate-pulse" />
        <p className="text-space-gray text-sm">{message}</p>
      </div>
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-red-500/30 bg-red-900/20 p-4 text-red-300 text-sm">
      {message}
    </div>
  );
}

export function getRiskColor(riskLevel?: string) {
  switch (riskLevel?.toLowerCase()) {
    case 'critical':
      return 'text-red-700';
    case 'medium':
      return 'text-yellow-700';
    case 'low':
      return 'text-green-700';
    default:
      return 'text-gray-600';
  }
}

export function getRiskBg(riskLevel?: string) {
  switch (riskLevel?.toLowerCase()) {
    case 'critical':
      return 'bg-red-50 border-red-400/40';
    case 'medium':
      return 'bg-yellow-50 border-yellow-400/40';
    case 'low':
      return 'bg-green-50 border-green-400/40';
    default:
      return 'bg-gray-50 border-gray-400/40';
  }
}

export function getAlertStyles(level: string) {
  switch (level) {
    case 'CRITICAL':
      return 'border-red-400/50 bg-red-50 text-red-800';
    case 'WARNING':
      return 'border-yellow-400/50 bg-yellow-50 text-yellow-800';
    default:
      return 'border-space-blue/30 bg-space-blue/5 text-space-cyan';
  }
}

export function SidebarNav() {
  return (
    <nav className="space-y-1">
      {navigationItems.map((item) => (
        <NavLink
          key={item.path}
          to={item.path}
          end={item.path === '/'}
          className={({ isActive }) =>
            `flex items-center px-4 py-3 text-sm font-medium rounded-lg transition-colors group ${
              isActive
                ? 'bg-space-blue/20 text-space-cyan border border-space-blue/30'
                : 'hover:bg-space-blue/10 text-space-light'
            }`
          }
        >
          <span className="mr-3">{item.icon}</span>
          <span>{item.name}</span>
        </NavLink>
      ))}
    </nav>
  );
}

export function formatFlux(value?: number) {
  if (value == null) return '—';
  return `${value.toExponential(1)} W/m²`;
}

export function formatTime(iso?: string) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString();
}
