import React from 'react';

export function DataSourceBadge({ source, updated }: { source?: string; updated?: string }) {
  return (
    <div className="flex flex-wrap items-center gap-2 text-xs">
      <span className="px-2 py-1 rounded-md bg-green-100 text-green-800 border border-green-400/50 font-medium">
        LIVE — {source ?? 'NOAA SWPC'}
      </span>
      {updated && <span className="text-space-gray">Updated: {new Date(updated).toLocaleString()}</span>}
      <span className="text-space-gray">Auto-refresh every 60s</span>
    </div>
  );
}

export function GlossaryPanel({ title, items }: { title: string; items: Record<string, string> }) {
  return (
    <div className="rounded-xl border border-space-blue/20 bg-space-dark/80 p-4">
      <h4 className="text-sm font-semibold text-space-cyan mb-3">{title}</h4>
      <dl className="space-y-2 text-xs">
        {Object.entries(items).map(([key, value]) => (
          <div key={key}>
            <dt className="text-space-light font-medium">{key}</dt>
            <dd className="text-space-gray mt-0.5">{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

export function FlareClassBadge({ flareClass }: { flareClass: string }) {
  const letter = flareClass[0]?.toUpperCase();
  const colors: Record<string, string> = {
    X: 'bg-red-100 text-red-800 border-red-400/50',
    M: 'bg-orange-100 text-orange-800 border-orange-400/50',
    C: 'bg-yellow-100 text-yellow-800 border-yellow-400/50',
    B: 'bg-green-100 text-green-800 border-green-400/50',
    A: 'bg-cyan-100 text-cyan-800 border-cyan-400/50',
  };
  return (
    <span className={`inline-flex px-2.5 py-1 rounded-md border text-sm font-bold ${colors[letter] ?? colors.A}`}>
      {flareClass}
    </span>
  );
}

export function MeaningBox({ title, text }: { title: string; text: string }) {
  return (
    <div className="rounded-lg bg-space-black/50 border border-space-blue/15 p-3 text-sm">
      <p className="text-space-cyan font-medium mb-1">{title}</p>
      <p className="text-space-gray leading-relaxed">{text}</p>
    </div>
  );
}
