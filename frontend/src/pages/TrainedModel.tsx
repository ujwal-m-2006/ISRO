import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { TrainedModelMetricsChart, TrainedModelProbabilityChart } from '../components/charts';
import { DataSourceBadge, MeaningBox } from '../components/live';
import { LoadingState, PageHeader, Panel } from '../components/ui';
import { api, formatTime } from '../services/api';
import type { TrainedModelVariant } from '../types';

const VARIANT_META = {
  single_model: { label: 'Single Model', accent: 'from-space-blue to-space-cyan' },
  dual_model: { label: 'Dual Model', accent: 'from-space-teal to-space-cyan' },
  multi_model: { label: 'Multi Model', accent: 'from-space-purple to-space-fuchsia' },
} as const;

const SCROLL_TEXT =
  "Single Model = trained on NOAA GOES-18 X-ray flux only, one data source.   •   " +
  "Dual Model = trained on NOAA GOES-18 X-ray flux + real Aditya-L1 SoLEXS light-curve data, two data sources combined.   •   " +
  "Multi Model = a voting ensemble that blends the Single and Dual trained models together.   •   " +
  "Target predicted: whether a C-class-or-above GOES longwave flare will occur within the next 6 hours.   •   " +
  "Every model is a genuine scikit-learn classifier fit on real historical data with a temporal train/test split — trained on earlier data, tested on later data it never saw during training.   •   " +
  "Reported accuracy, precision, and recall come from that real held-out test set, not an assumed or asserted number.   •   " +
  "This is distinct from the Predictions tab, which uses a transparent hand-weighted statistical blend of signals, not a trained model.   •   ";

function ScrollingDescription() {
  const loop = SCROLL_TEXT + SCROLL_TEXT;
  return (
    <div className="bg-isro-navy-dark border border-space-blue/30 rounded-lg overflow-hidden">
      <div className="flex items-center">
        <span className="shrink-0 bg-space-blue text-white text-[11px] font-bold uppercase tracking-wide px-3 py-2 z-10">
          Methodology
        </span>
        <div className="overflow-hidden flex-1 group">
          <div className="flex animate-marquee whitespace-nowrap py-2 group-hover:[animation-play-state:paused]">
            <span className="text-xs text-white/85 px-4">{loop}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function WarningBanner({ trainingWindow }: { trainingWindow?: { adityal1_available: boolean } }) {
  return (
    <div className="rounded-xl border-2 border-orange-500/60 bg-orange-50 p-5">
      <div className="flex items-start gap-3">
        <span className="text-2xl leading-none">⚠️</span>
        <div>
          <p className="font-bold text-orange-900 mb-2">Important — Read Before Interpreting These Results</p>
          <ul className="text-sm text-orange-900 space-y-1.5 list-disc list-inside">
            <li>
              <strong>Small training window:</strong> trained on roughly 7–10 days of real data (NOAA's free live API only exposes
              a rolling 7-day history). This is not a multi-year archive-scale dataset.
            </li>
            <li>
              <strong>Target is C-class-or-above, not M/X specifically:</strong> a window this short has too few real M/X-class
              events to fit a statistically meaningful classifier for those specifically.
            </li>
            <li>
              <strong>Preliminary result, not a final one:</strong> accuracy, precision, and recall numbers should be read as an
              honest early signal — a larger training window would give more statistically reliable numbers.
            </li>
            <li>
              <strong>Not for operational decision-making:</strong> this is a research/demonstration model, not a validated
              operational forecasting system. No solar flare prediction system — trained or statistical — can predict with certainty.
            </li>
            <li>
              <strong>Dual/Multi model live predictions depend on infrastructure:</strong> they need a live Aditya-L1 signal
              (PRADAN credentials configured + the hourly refresh job to have run). If unavailable, this is reported explicitly
              rather than silently substituted with a NOAA-only number.
              {trainingWindow && !trainingWindow.adityal1_available && (
                <span className="font-semibold"> Aditya-L1 data was not available during this specific training run.</span>
              )}
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}

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

  const variantOrder: (keyof typeof VARIANT_META)[] = ['single_model', 'dual_model', 'multi_model'];

  const metricsChartData = variantOrder
    .map((id) => {
      const v = data.variants[id];
      if (!v || v.test_accuracy == null) return null;
      return {
        model: VARIANT_META[id].label,
        accuracy: Math.round((v.test_accuracy ?? 0) * 1000) / 10,
        precision: Math.round((v.test_precision ?? 0) * 1000) / 10,
        recall: Math.round((v.test_recall ?? 0) * 1000) / 10,
      };
    })
    .filter((d): d is NonNullable<typeof d> => d !== null);

  const probabilityChartData = variantOrder
    .map((id) => {
      const v = data.variants[id];
      if (!v || !v.prediction_available || v.probability_pct == null) return null;
      return { model: VARIANT_META[id].label, probability: v.probability_pct };
    })
    .filter((d): d is NonNullable<typeof d> => d !== null);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Trained Model Predictions"
        subtitle="Real scikit-learn classifiers fit on historical data — distinct from the statistical ensemble on the Predictions tab"
        status="ML Model"
      />
      <DataSourceBadge source="NOAA GOES-18 + Aditya-L1 SoLEXS (real training data)" updated={data.trained_at} />

      <ScrollingDescription />

      <WarningBanner trainingWindow={data.training_window} />

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

      {metricsChartData.length > 0 && (
        <Panel title="Model Comparison — Real Held-Out Test Metrics">
          <TrainedModelMetricsChart data={metricsChartData} />
        </Panel>
      )}

      {probabilityChartData.length > 0 && (
        <Panel title="Live Probability by Model — Right Now">
          <TrainedModelProbabilityChart data={probabilityChartData} />
        </Panel>
      )}

      <PageHeader title="Live Predictions by Model" subtitle="Same real-time inputs, three different trained models — see which dataset combination each one uses" />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {variantOrder.map((id) => {
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
