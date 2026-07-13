-- Migration: allow single-model and dual-model prediction tracking
-- Run this once in the Supabase SQL editor if you already ran schema.sql
-- before this change — `create table if not exists` won't retroactively
-- update an existing table's CHECK constraint, so this migration does it
-- directly.

alter table predictions drop constraint if exists predictions_category_check;

alter table predictions add constraint predictions_category_check
  check (category in ('ensemble_flare', 'storm_watch', 'cme_arrival', 'single_model_flare', 'dual_model_flare'));
