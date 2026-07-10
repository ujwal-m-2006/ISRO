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
    get_summary, get_flux, get_forecast, get_ensemble_forecast,
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


def generate_flux_chart(flux_data, hours_shown=24):
    """X-ray flux history with GOES flare-class threshold lines (B/C/M/X),
    same shape as the standard GOES flux plot this project's own frontend
    likely already renders — a from-scratch matplotlib version for a static
    PNG export, not a port of any specific frontend chart component (the
    frontend is TypeScript/React, not something to port into Python)."""
    points = flux_data.get('points', [])
    if not points:
        return None

    times = [p.get('time_tag') or p.get('time') for p in points]
    times = [datetime.fromisoformat(t.replace('Z', '+00:00')) if isinstance(t, str) else t for t in times]
    soft = [p.get('soft') for p in points]

    fig, ax = plt.subplots(figsize=(9, 3.2), dpi=110)
    ax.plot(times, soft, color='#facc15', linewidth=1.4, label='GOES X-ray flux (0.1-0.8nm)')
    ax.set_yscale('log')

    for label, value in (FLARE_THRESHOLDS or {}).items():
        try:
            v = float(value)
        except (TypeError, ValueError):
            continue
        ax.axhline(y=v, color='#666666', linewidth=0.6, linestyle='dotted')
        ax.text(times[0], v, f' {label}', fontsize=7, color='#888888', va='bottom')

    ax.set_ylabel('W/m²')
    ax.set_title(f'X-ray Flux — last {hours_shown}h', fontsize=10)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %HUTC'))
    fig.autofmt_xdate(rotation=30)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def build_summary():
    summary = get_summary()
    forecast = safe(get_forecast, {})
    ensemble = safe(get_ensemble_forecast, {})
    cme = safe(get_cme_summary, {})
    earth_impact = safe(get_earth_impact, {})
    storm_watches = safe(get_storm_watches, {})

    forecast_preds = (forecast or {}).get('predictions') or []
    next_forecast = forecast_preds[0] if forecast_preds else {}

    ensemble_preds = (ensemble or {}).get('predictions') or []
    next_ensemble = ensemble_preds[0] if ensemble_preds else {}

    today_impact = (earth_impact or {}).get('today') or {}
    impact_parts = []
    for scale_key in ('radio_blackout', 'radiation_storm', 'geomagnetic_storm'):
        detail = today_impact.get(scale_key)
        if detail and detail.get('text') and detail.get('text') != 'None':
            impact_parts.append(detail['text'])
    earth_impact_summary = '; '.join(impact_parts) if impact_parts else None

    watches = (storm_watches or {}).get('watches') if isinstance(storm_watches, dict) else None
    storm_watch_text = None
    if watches:
        storm_watch_text = '; '.join(str(w) for w in watches[:3])

    row = {
        'current_class':          summary.get('current_class'),
        'current_class_letter':   summary.get('current_class_letter'),
        'class_meaning':          summary.get('class_meaning'),
        'activity_level':         summary.get('activity_level'),
        'flux_trend_pct_30min':   summary.get('flux_trend_pct_30min'),
        'recent_flares_count_7d': summary.get('recent_flares_count_7d'),
        'active_regions_count':   summary.get('active_regions_count'),
        'top_active_region':      summary.get('top_active_region'),
        'global_probabilities':   summary.get('global_probabilities'),
        'risk_level':             summary.get('risk_level'),

        'forecast_horizon':       next_forecast.get('time_horizon'),
        'forecast_flare_class':   next_forecast.get('flare_class'),
        'forecast_probability':   next_forecast.get('probability'),
        'forecast_confidence':    next_forecast.get('confidence'),

        'ensemble_flare_class':   next_ensemble.get('flare_class'),
        'ensemble_probability':   next_ensemble.get('probability'),
        'ensemble_horizon':       next_ensemble.get('time_horizon'),

        'cme_earth_directed_count': (cme or {}).get('earth_directed_count'),
        'cme_total_count':          (cme or {}).get('total_cmes'),
        'earth_impact_summary':     earth_impact_summary,
        'earth_impact_max_scale':   (earth_impact or {}).get('max_scale_today'),

        'storm_watch_text': storm_watch_text,
    }

    flux = safe(lambda: get_flux(hours=24), {})
    chart_png = generate_flux_chart(flux) if flux else None

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
