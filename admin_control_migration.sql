-- ============================================================================
-- ADMIN CONTROL MIGRATION — manual/automatic toggle for the dynamic layer
-- Money Master. Run ONCE on the live project (Supabase SQL Editor), AFTER
-- supabase.sql. Idempotent — safe to re-run.
--
-- Adds two flags to game_control:
--   auto_events  = engine invents random emergencies/opportunities each month
--   auto_market  = stocks/gold move automatically each month
-- Both default FALSE => admin has full manual control out of the box.
-- ============================================================================
ALTER TABLE public.game_control
  ADD COLUMN IF NOT EXISTS auto_events boolean NOT NULL DEFAULT false;
ALTER TABLE public.game_control
  ADD COLUMN IF NOT EXISTS auto_market boolean NOT NULL DEFAULT false;
