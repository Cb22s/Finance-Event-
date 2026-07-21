-- ============================================================================
-- Money Master V2 Migration (2026-07-21)
--   1. Monthly allocation (recurring, replaces month-1-only)
--   2. Admin-authored market scenarios with narrative reason
--   3. Player-initiated loans (term + purpose)
-- Apply AFTER marriage_migration.sql.
-- ============================================================================

-- ──── 1. MONTHLY ALLOCATION AUDIT TRAIL ────
-- Never overwritten. One immutable row per player per month recording exactly how
-- that month's available cash was distributed.
CREATE TABLE IF NOT EXISTS public.player_month_allocations (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    month INTEGER NOT NULL,
    available_cash NUMERIC NOT NULL DEFAULT 0,
    to_stocks NUMERIC NOT NULL DEFAULT 0,
    to_gold NUMERIC NOT NULL DEFAULT 0,
    to_emergency_fund NUMERIC NOT NULL DEFAULT 0,
    to_loan_prepay NUMERIC NOT NULL DEFAULT 0,
    kept_as_cash NUMERIC NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    UNIQUE (user_id, month)
);

ALTER TABLE public.player_month_allocations ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "allocations read own" ON public.player_month_allocations;
CREATE POLICY "allocations read own" ON public.player_month_allocations
    FOR SELECT USING (auth.uid() = user_id);

-- ──── 2. ADMIN-AUTHORED MARKET SCENARIOS ────
-- One scenario per month drives BOTH stocks and gold, with a reason shown to players.
-- Unauthored months fall back to the engine's correlated auto regime.
CREATE TABLE IF NOT EXISTS public.market_scenarios (
    id BIGSERIAL PRIMARY KEY,
    month INTEGER NOT NULL UNIQUE,
    name TEXT NOT NULL,
    reason TEXT NOT NULL DEFAULT '',
    stock_pct NUMERIC NOT NULL DEFAULT 0,
    gold_pct NUMERIC NOT NULL DEFAULT 0,
    regime TEXT DEFAULT 'authored',
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

ALTER TABLE public.market_scenarios ENABLE ROW LEVEL SECURITY;

-- Players may read the scenario only for months already played; the backend
-- enforces that. Public read is safe here because the admin controls which rows
-- exist and the frontend only ever requests the current month.
DROP POLICY IF EXISTS "market_scenarios read all" ON public.market_scenarios;
CREATE POLICY "market_scenarios read all" ON public.market_scenarios
    FOR SELECT USING (true);

-- ──── 3. PLAYER-INITIATED LOANS ────
ALTER TABLE public.player_loans
    ADD COLUMN IF NOT EXISTS term_months INTEGER NOT NULL DEFAULT 6;
ALTER TABLE public.player_loans
    ADD COLUMN IF NOT EXISTS loan_type TEXT NOT NULL DEFAULT 'auto';
ALTER TABLE public.player_loans
    ADD COLUMN IF NOT EXISTS emi NUMERIC NOT NULL DEFAULT 0;

-- Existing rows predate the distinction and were all involuntary.
UPDATE public.player_loans SET loan_type = 'auto' WHERE loan_type IS NULL;
