-- ############################################################################
-- ##  NOT REQUIRED FOR A FRESH INSTALL (F-02).                               ##
-- ##  public.player_month_actions is now created by supabase.sql. A fresh    ##
-- ##  install runs ONLY supabase.sql. Retained only to retrofit an older     ##
-- ##  live project that predates the fold-in. Safe (idempotent) if re-run.   ##
-- ############################################################################

-- ============================================================================
-- IDEMPOTENCY MIGRATION
-- Durable, per-(user, month) action guard for optional-choice purchases and
-- relative-help actions. Replaces the old in-memory _rate_limit dict in
-- game_service.py, which reset on every server restart and was not shared
-- across web workers (letting players re-buy the same choice / farm trust).
--
-- Run this once against your Supabase project (SQL editor or CLI).
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.player_month_actions (
    user_id     UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    month       INTEGER NOT NULL,
    action_key  TEXT NOT NULL,   -- e.g. 'choice:12' or 'relative:parent'
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    PRIMARY KEY (user_id, month, action_key)
);

-- Server-only: RLS enabled with NO client policy, so the browser cannot read
-- or write it. All access goes through the Flask backend (service_role key,
-- which bypasses RLS). Mirrors the pattern used for public.admins.
ALTER TABLE public.player_month_actions ENABLE ROW LEVEL SECURITY;

-- Clean up when an admin resets a player or restarts the game (matches the
-- delete-by-user pattern already used for the other player_* tables).
