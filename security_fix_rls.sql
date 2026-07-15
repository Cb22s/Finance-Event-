-- ############################################################################
-- ##  INCREMENTAL PATCH — NOT part of a fresh install (F-02).                ##
-- ##  supabase.sql already ships the SELECT-own-row policies. Use ONLY to    ##
-- ##  retrofit an older live project that still has the FOR ALL policies.     ##
-- ############################################################################

-- ============================================================================
-- SECURITY FIX — Lock down player financial tables (Row Level Security)
-- Money Master — Financial Simulation Game
--
-- HOW TO APPLY:
--   Supabase Dashboard -> SQL Editor -> paste this file -> Run.
--   Safe to run more than once (idempotent).
--
-- PROBLEM:
--   The old policies used "FOR ALL USING (auth.uid() = user_id)". FOR ALL
--   includes INSERT / UPDATE / DELETE, so any logged-in player could write
--   their OWN financial rows directly from the browser using the public anon
--   key — e.g. run supabase.from('player_state').update({ net_worth: 9e9 })
--   and top the leaderboard. This breaks fair competition entirely.
--
-- FIX:
--   Clients get SELECT-only, and only on their OWN rows. Every write must go
--   through the Flask backend, which connects with the SERVICE_ROLE key and
--   bypasses RLS. No frontend flow writes these tables directly (verified),
--   so nothing legitimate breaks. The leaderboard is served by the backend
--   (service role), so restricting client reads to own rows also stops
--   players from inspecting each other's portfolios.
-- ============================================================================

-- Make sure RLS is on (no-op if already enabled).
ALTER TABLE public.player_state            ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.player_sales            ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.player_loans            ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.player_relative_score   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.player_relative_actions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.player_month_log        ENABLE ROW LEVEL SECURITY;

-- ── player_state ─────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "Enable all for user state"       ON public.player_state;
DROP POLICY IF EXISTS "Enable all for leaderboard read" ON public.player_state;
CREATE POLICY "player_state read own"
    ON public.player_state FOR SELECT
    USING (auth.uid() = user_id);

-- ── player_sales ─────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "Enable all for user sales" ON public.player_sales;
CREATE POLICY "player_sales read own"
    ON public.player_sales FOR SELECT
    USING (auth.uid() = user_id);

-- ── player_loans ─────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "Enable all for user loans" ON public.player_loans;
CREATE POLICY "player_loans read own"
    ON public.player_loans FOR SELECT
    USING (auth.uid() = user_id);

-- ── player_relative_score ────────────────────────────────────────────────
DROP POLICY IF EXISTS "Enable all for user score" ON public.player_relative_score;
CREATE POLICY "player_relative_score read own"
    ON public.player_relative_score FOR SELECT
    USING (auth.uid() = user_id);

-- ── player_relative_actions ──────────────────────────────────────────────
DROP POLICY IF EXISTS "Enable all for user actions" ON public.player_relative_actions;
CREATE POLICY "player_relative_actions read own"
    ON public.player_relative_actions FOR SELECT
    USING (auth.uid() = user_id);

-- ── player_month_log ─────────────────────────────────────────────────────
DROP POLICY IF EXISTS "Enable all for user logs" ON public.player_month_log;
CREATE POLICY "player_month_log read own"
    ON public.player_month_log FOR SELECT
    USING (auth.uid() = user_id);

-- ============================================================================
-- VERIFY (optional): list remaining policies — each table should show ONLY a
-- SELECT ("r") policy for the authenticated role and NO write policies.
-- ============================================================================
SELECT tablename, policyname, cmd
FROM   pg_policies
WHERE  schemaname = 'public'
  AND  tablename IN (
        'player_state', 'player_sales', 'player_loans',
        'player_relative_score', 'player_relative_actions', 'player_month_log'
  )
ORDER  BY tablename, cmd;
