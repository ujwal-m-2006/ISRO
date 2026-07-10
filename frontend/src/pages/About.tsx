import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { GlossaryPanel } from '../components/live';
import { PageHeader, Panel } from '../components/ui';
import { api } from '../services/api';

function About() {
  const glossary = useQuery({ queryKey: ['glossary'], queryFn: api.getGlossary, staleTime: 3600000 });

  return (
    <div className="space-y-6">
      <PageHeader title="About" subtitle="Live solar flare monitoring aligned with NOAA SWPC operational data" />

      <Panel title="Data Sources (Live)">
        <ul className="text-sm text-space-gray space-y-2">
          <li><span className="text-space-light font-medium">NOAA SWPC GOES-18 X-ray Sensor</span> — 1-minute X-ray flux (same as spaceweather.com / SWPC plots)</li>
          <li><span className="text-space-light font-medium">NOAA Solar Regions</span> — active region locations, magnetic class, official C/M/X probabilities</li>
          <li><span className="text-space-light font-medium">NOAA Flare List</span> — verified flare begin/peak/end times and classes (7-day rolling)</li>
          <li><span className="text-space-light font-medium">Aditya-L1 context</span> — SoLEXS & HEL1OS instruments mapped to GOES bands for operational comparison</li>
        </ul>
        <p className="text-xs text-space-gray mt-4">Data refreshes automatically every 60 seconds. No manual prediction input required.</p>
      </Panel>

      {glossary.data && (
        <>
          <GlossaryPanel title="Flare Class Meanings (NOAA)" items={glossary.data.flare_classes} />
          <GlossaryPanel
            title="Flux Thresholds (W/m², longwave 0.1–0.8 nm)"
            items={Object.fromEntries(
              Object.entries(glossary.data.flux_thresholds_wm2).map(([k, v]) => [k, `≥ ${Number(v).toExponential(1)} W/m²`]),
            )}
          />
        </>
      )}

      <Panel title="Technology">
        <p className="text-sm text-space-gray">React dashboard · FastAPI backend · NOAA live ingestion · Automated nowcast & hourly forecast engine</p>
      </Panel>
    </div>
  );
}

export default About;
