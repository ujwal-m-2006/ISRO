import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { DataSourceBadge, MeaningBox } from '../components/live';
import { LoadingState, PageHeader, Panel } from '../components/ui';
import { api, formatTime } from '../services/api';
import type { TrainedModelVariant } from '../types';

const VARIANT_META = {
  single_model: { label: 'Single Model', accent: 'from-space-blue to-space-cyan' },
  dual_model: { label: 'Dual Model', accent: 'from-space-teal to-space-cyan' },
  multi_model: { label: 'Multi Model', accent: 'from-space-purple to-space-fuchsia' },
} as const;

function VariantCard({ id, variant }: { id: keyof typeof VARIANT_META; variant: TrainedModelVariant }) {
  const meta = VARIANT_META[id];
  return (
    <div className="bg-space-dark rounded-xl p-5 border border-space-blue/20">
      <div className="flex items-center justify-between mb-2">
        <p className="text-sm font-semibold text-space-light">{meta.label}</p>
        <div className={`w-8 h-8 rounded-lg bg-gradient-to-br ${meta.accent} flex items-center justify-center`}>
          <span className="text-white text-xs font-bold">{id === 'single_model' ? '1' : id === 'dual_model' ? '2' : '3'}</span>
        </div>
      </div>

      <p className="text-xs text-space-gray mb-3">
        Trained on: <span className="text-space-light font-medium">{variant.datasets.join(' + ')}</span>
      </p>

      {variant.prediction_available ? (
        <>
          <p className="text-3xl font-bold">{variant.probability_pct}%</p>
          <p className="text-xs text-space-gray mt-1">
            probability of C-class-or-above flare in next 6h — model says{' '}
            <span className={variant.predicted_positive ? 'text-orange-500 font-semibold' : 'text-green-600 font-semibold'}>
              {variant.predicted_positive ? 'likely' : 'unlikely'}
            </span>
          </p>
          {variant.adityal1_feature_as_of && (
            <p className="text-xs text-space-gray mt-1">Aditya-L1 signal as of {formatTime(variant.adityal1_feature_as_of)}</p>
          )}
        </>
      ) : (
        <p className="text-sm text-space-gray py-2">
          Prediction unavailable — {variant.reason}
        </p>
      )}

      <div className="mt-3 pt-3 border-t border-space-blue/10 text-xs text-space-gray space-y-1">
        <p>Real held-out test accuracy: <span className="text-space-light font-medium">{variant.test_accuracy != null ? `${(variant.test_accuracy * 100).toFixed(1)}%` : '—'}</span></p>
        <p>Precision: {variant.test_precision != null ? `${(variant.test_precision * 100).toFixed(1)}%` : '—'} · Recall: {variant.test_recall != null ? `${(variant.test_recall * 100).toFixed(1)}%` : '—'}</p>
        <p>Trained on {variant.train_samples} real samples, tested on {variant.test_samples} held-out real samples (never seen during training)</p>
      </div>
    </div>
  );
}

function TrainedModel() {
  const query = useQuery({ queryKey: ['trained-model'], queryFn: api.getTrainedModelPredictions, refetchInterval: 60_000 });

  if (query.isLoading) return <LoadingState message="Loading trained model predictions..." />;

  const data = query.data;

  if (!data || !data.available) {
    return (
      <div className="space-y-6">
        <PageHeader title="Trained Model Predictions" subtitle="Real scikit-learn classifiers fit on historical NOAA + Aditya-L1 data" />
        <Panel title="Not available yet">
          <p className="text-sm text-space-gray py-6 text-center">{data?.message ?? 'No trained model exists yet.'}</p>
        </Panel>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Trained Model Predictions"
        subtitle="Real scikit-learn classifiers fit on historical data — distinct from the statistical ensemble on the Predictions tab"
        status="ML Model"
      />
      <DataSourceBadge source="NOAA GOES-18 + Aditya-L1 SoLEXS (real training data)" updated={data.trained_at} />

      <MeaningBox
        title="How this differs from the Predictions tab"
        text="The Predictions tab uses a transparent hand-weighted statistical blend of real signals — not a trained model. These three variants are genuine scikit-learn classifiers, each fit on real historical NOAA and Aditya-L1 data with a held-out temporal test split (trained on earlier data, tested on later data it never saw). Reported accuracy comes from that real test set, not asserted."
      />

      {data.training_window && (
        <Panel title="Training Data — Real, Disclosed Limitations">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-space-gray text-xs uppercase">NOAA GOES-18 window</p>
              <p className="font-medium">{formatTime(data.training_window.noaa_start)} — {formatTime(data.training_window.noaa_end)}</p>
            </div>
            <div>
              <p className="text-space-gray text-xs uppercase">Aditya-L1 SoLEXS data</p>
              <p className="font-medium">{data.training_window.adityal1_available ? `${data.training_window.adityal1_points.toLocaleString()} real light-curve points` : 'Not available this training run'}</p>
            </div>
          </div>
          <p className="text-xs text-space-gray mt-3 pt-3 border-t border-space-blue/10">
            Target: {data.target}. This is a genuinely small training window (NOAA's free live API only exposes a rolling 7-day history — a longer multi-year archive would need heavier NCEI archive-file parsing not yet built). Treat these accuracy numbers as an honest preliminary signal, not a final result — a larger training window would give more statistically reliable numbers, especially for the recall metric given how few real M/X-class events occur in any 7-10 day window.
          </p>
        </Panel>
      )}

      <PageHeader title="Live Predictions by Model" subtitle="Same real-time inputs, three different trained models — see which dataset combination each one uses" />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {(Object.keys(VARIANT_META) as (keyof typeof VARIANT_META)[]).map((id) => {
          const variant = data.variants[id];
          return variant ? <VariantCard key={id} id={id} variant={variant} /> : null;
        })}
      </div>

      <p className="text-xs text-space-gray">
        Single Model uses only NOAA GOES-18 X-ray flux. Dual Model adds real Aditya-L1 SoLEXS light-curve data (India's own solar X-ray instrument) alongside NOAA. Multi Model is a voting ensemble combining both trained models. If Dual/Multi show "unavailable," it means this deployment doesn't currently have a fresh live Aditya-L1 signal (needs PRADAN credentials configured and the hourly refresh cron to have run at least once) — reported honestly rather than silently substituting a NOAA-only number.
      </p>
    </div>
  );
}

export default TrainedModel;
