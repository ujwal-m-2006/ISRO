-- Prediction accuracy tracking — Supabase schema
-- Run this once in the Supabase SQL editor (Project -> SQL Editor -> New query).
--
-- Replaces backend/data/predictions/*.jsonl (see services/prediction_store.py).
-- One table, category-partitioned by a check constraint, category-specific
-- fields kept in `data` jsonb so this doesn't need a migration every time a
-- new predicted field is added — matches the current dict-shaped JSONL entries.

create table if not exists predictions (
  id bigint generated always as identity primary key,
  category text not null check (category in ('ensemble_flare', 'storm_watch', 'cme_arrival', 'single_model_flare', 'dual_model_flare')),
  dedup_key text not null,
  data jsonb not null default '{}'::jsonb,
  verified boolean not null default false,
  correct boolean,
  recorded_at timestamptz not null default now(),
  verified_at timestamptz,
  unique (category, dedup_key)
);

create index if not exists predictions_category_verified_idx
  on predictions (category, verified);

create index if not exists predictions_recorded_at_idx
  on predictions (recorded_at desc);

-- RLS on, no public policies — only the service_role key (used server-side by
-- the FastAPI backend) can read/write, since service_role bypasses RLS
-- entirely. The frontend never talks to Supabase directly, only to the
-- backend API, so no anon policy is needed.
alter table predictions enable row level security;
