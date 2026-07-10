"""
Headless publisher — pulls this backend's live solar flare data and pushes a
summary row + a flux-history chart to the Space_Weather site's Supabase
project (a different Supabase project from this backend's own — this repo's
own Supabase only tracks prediction accuracy, per backend/sql/schema.sql).

Place this file at: backend/jobs/publish_to_space_weather.py
(run from the `backend/` directory so `services.*` imports resolve, same as
the existing FastAPI app / other jobs in this folder).

Does NOT need this backend's own Postgres DB or a running Render instance —
services.cron_data's get_*() functions fall back to a live NOAA fetch
whenever there's no local cron-job cache, which is always true on a fresh
GitHub Actions runner. Self-contained.

Environment variables required:
    SPACE_WEATHER_SUPABASE_URL          — Space_Weather's Supabase project URL
    SPACE_WEATHER_SUPABASE_SERVICE_KEY  — its service_role/secret key (never
                                            the anon/publishable key)
"""
import io
import os
import sys
import traceback

import matplotlib
matplotlib.use('Agg')
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from datetime import datetime
from supabase import create_client

from services.cron_data import (
    get_summary, get_flux, get_nowcast, get_forecast, get_ensemble_forecast,
    get_regions, get_cme_summary, get_earth_impact, get_storm_watches,
)
from services.noaa_live_service import FLARE_THRESHOLDS

CHART_BUCKET = 'flare_charts'
CHART_FILENAME = 'latest_flare_flux.png'


def safe(fn, default=None):
    """Best-effort — one failing sub-service (e.g. CME feed down) shouldn't
    block publishing everything else, same defensive pattern used throughout
    this backend's own get_*() functions."""
    try:
        return fn()
    except Exception:
        traceback.print_exc()
        return default


def generate_flux_chart(flux_data, forecast_preds, hours_shown=24):
    """Two panels in one image: observed X-ray flux history on top (with
    GOES flare-class threshold lines), and the extended forecast's flare
    class probability by horizon (1h through however far out the model
    actually predicts, e.g. up to 72h) as a grouped bar chart underneath —
    same data ExtendedForecastResponse.predictions exposes, just rendered as
    a chart instead of only shown as panel text.

    A from-scratch matplotlib version, not a port of any specific frontend
    component (the frontend is TypeScript/React)."""
    points = flux_data.get('points', []) if flux_data else []
    has_flux = bool(points)
    has_forecast = bool(forecast_preds)
    if not has_flux and not has_forecast:
        return None

    fig, axes = plt.subplots(
        2, 1, figsize=(9, 6.4), dpi=110,
        gridspec_kw={'height_ratios': [3, 2]},
    )
    ax_flux, ax_bar = axes

    if has_flux:
        times = [p.get('time_tag') or p.get('time') for p in points]
        times = [datetime.fromisoformat(t.replace('Z', '+00:00')) if isinstance(t, str) else t for t in times]
        soft = [p.get('soft') for p in points]

        ax_flux.plot(times, soft, color='#facc15', linewidth=1.4, label='GOES X-ray flux (0.1-0.8nm)')
        ax_flux.set_yscale('log')
        for label, value in (FLARE_THRESHOLDS or {}).items():
            try:
                v = float(value)
            except (TypeError, ValueError):
                continue
            ax_flux.axhline(y=v, color='#666666', linewidth=0.6, linestyle='dotted')
            ax_flux.text(times[0], v, f' {label}', fontsize=7, color='#888888', va='bottom')
        ax_flux.set_ylabel('W/m²')
        ax_flux.set_title(f'X-ray Flux (observed) — last {hours_shown}h', fontsize=10)
        ax_flux.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %HUTC'))
    else:
        ax_flux.text(0.5, 0.5, 'No flux data available', ha='center', va='center', transform=ax_flux.transAxes, fontsize=9, color='#888')
        ax_flux.set_xticks([]); ax_flux.set_yticks([])

    if has_forecast:
        # Sort by hours_ahead so the bars read left-to-right nearest-to-farthest,
        # regardless of what order the API returned them in.
        preds = sorted(forecast_preds, key=lambda p: p.get('hours_ahead', 0))
        labels = [p.get('time_horizon') or f"{p.get('hours_ahead', '?')}h" for p in preds]
        c_vals = [p.get('c_class_chance_pct') or 0 for p in preds]
        m_vals = [p.get('m_class_chance_pct') or 0 for p in preds]
        x_vals = [p.get('x_class_chance_pct') or 0 for p in preds]

        n = len(preds)
        idx = range(n)
        width = 0.25
        ax_bar.bar([i - width for i in idx], c_vals, width, label='C-class+', color='#facc15')
        ax_bar.bar(idx, m_vals, width, label='M-class+', color='#fb923c')
        ax_bar.bar([i + width for i in idx], x_vals, width, label='X-class+', color='#ef4444')
        ax_bar.set_xticks(list(idx))
        ax_bar.set_xticklabels(labels, fontsize=8)
        ax_bar.set_ylabel('Probability (%)')
        ax_bar.set_ylim(0, 100)
        ax_bar.set_title('Flare Class Probability by Horizon (forecast)', fontsize=10)
        ax_bar.legend(fontsize=7, loc='upper right')
    else:
        ax_bar.text(0.5, 0.5, 'No extended forecast available', ha='center', va='center', transform=ax_bar.transAxes, fontsize=9, color='#888')
        ax_bar.set_xticks([]); ax_bar.set_yticks([])

    fig.autofmt_xdate(rotation=30)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def build_summary():
    summary = get_summary()
    nowcast = safe(get_nowcast, {})
    forecast = safe(get_forecast, {})
    ensemble = safe(get_ensemble_forecast, {})
    cme = safe(get_cme_summary, {})
    earth_impact = safe(get_earth_impact, {})
    storm_watches = safe(get_storm_watches, {})

    # All horizons kept (1h through however far out the model predicts, e.g.
    # 72h) — full C/M/X probabilities intact, not collapsed to one pick. The
    # site renders these as-is, and the bar chart below needs every horizon,
    # not just the first few.
    forecast_preds = (forecast or {}).get('predictions') or []
    ensemble_preds = (ensemble or {}).get('predictions') or []

    row = {
        'current_class':          summary.get('current_class'),
        'current_class_letter':   summary.get('current_class_letter'),
        'class_meaning':          summary.get('class_meaning'),
        'activity_level':         summary.get('activity_level'),
        'flux_trend_pct_30min':   summary.get('flux_trend_pct_30min'),
        'recent_flares_count_7d': summary.get('recent_flares_count_7d'),
        'active_regions_count':   summary.get('active_regions_count'),
        'top_active_region':      summary.get('top_active_region'),
        'global_probabilities':   summary.get('global_probabilities'),  # current C/M/X
        'risk_level':             summary.get('risk_level'),

        'nowcast':  nowcast or None,          # ExtendedNowcastResponse-shaped dict — has its own c/m/x_class_probability_pct
        'forecast': forecast_preds or None,   # list of ExtendedForecastItem (each: c/m/x_class_chance_pct per horizon)
        'ensemble': ensemble_preds or None,   # list of EnsemblePrediction (each: .combined = {class: probability})

        'cme_earth_directed_count': (cme or {}).get('earth_directed_count'),
        'cme_total_count':          (cme or {}).get('total_cmes'),
        'earth_impact_today':       (earth_impact or {}).get('today') or None,
        'storm_watches':            (storm_watches or {}).get('watches') or None,
    }

    flux = safe(lambda: get_flux(hours=24), {})
    chart_png = generate_flux_chart(flux, forecast_preds)

    return row, chart_png


def upload_chart(sb, png_bytes):
    if not png_bytes:
        print('No flux chart generated (no flux points available) — skipping upload.')
        return False
    try:
        sb.storage.from_(CHART_BUCKET).upload(
            CHART_FILENAME, png_bytes,
            {'content-type': 'image/png', 'upsert': 'true'},
        )
        return True
    except Exception:
        traceback.print_exc()
        return False


def main():
    url = os.environ['SPACE_WEATHER_SUPABASE_URL']
    key = os.environ['SPACE_WEATHER_SUPABASE_SERVICE_KEY']
    sb = create_client(url, key)

    row, chart_png = build_summary()
    sb.table('flare_predictions').insert(row).execute()
    print('Inserted flare_predictions row:', row)

    uploaded = upload_chart(sb, chart_png)
    print('Chart uploaded.' if uploaded else 'Chart upload skipped/failed — row was still inserted.')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
