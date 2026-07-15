-- ============================================================================
-- Supabase Schema for Money Master — Financial Simulation Game
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ──── Users ────
CREATE TABLE public.users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT,
    email TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- ──── Case Study (Scenario Setup) ────
CREATE TABLE public.case_study (
    id SERIAL PRIMARY KEY,
    title TEXT,
    description TEXT,
    rent NUMERIC,
    food NUMERIC,
    transport NUMERIC,
    family NUMERIC
);

INSERT INTO public.case_study (title, description, rent, food, transport, family)
VALUES ('The First Job', 'Manage ₹1,00,000 monthly income across 12 months.', 20000, 10000, 5000, 5000);

-- ──── Admin Events (Global per-month events) ────
CREATE TABLE public.events (
    id SERIAL PRIMARY KEY,
    month INTEGER,
    event_name TEXT,
    event_type TEXT,       -- 'fixed', 'percentage'
    impact_target TEXT,    -- 'cash', 'stocks', 'gold', 'expense_increase'
    value NUMERIC,
    description TEXT
);

-- ──── Optional Choices (player decisions per month) ────
CREATE TABLE public.optional_choices (
    id SERIAL PRIMARY KEY,
    month INTEGER,
    name TEXT,
    cost NUMERIC,
    risk_type TEXT,
    reward_type TEXT,
    reward_value NUMERIC,
    probability INTEGER
);

-- ──── Game Control (Singleton) ────
CREATE TABLE public.game_control (
    id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    current_month INTEGER DEFAULT 1,
    game_status TEXT DEFAULT 'waiting',
    auto_events BOOLEAN NOT NULL DEFAULT false,
    auto_market BOOLEAN NOT NULL DEFAULT false
);

INSERT INTO public.game_control (id, current_month, game_status) VALUES (1, 1, 'waiting');

-- ──── Player State (Single Source of Truth) ────
CREATE TABLE public.player_state (
    user_id UUID REFERENCES public.users(id) PRIMARY KEY,
    month INTEGER DEFAULT 1,
    cash NUMERIC DEFAULT 0,
    stocks NUMERIC DEFAULT 0,
    gold NUMERIC DEFAULT 0,
    emergency_fund NUMERIC DEFAULT 0,
    loans NUMERIC DEFAULT 0,
    pending_cash_next_month NUMERIC DEFAULT 0,
    lifestyle_type TEXT,
    bike_status BOOLEAN DEFAULT false,
    bike_lock_in_months INTEGER DEFAULT 0,
    net_worth NUMERIC DEFAULT 0,
    trust_score NUMERIC DEFAULT 0,
    risk_level INTEGER DEFAULT 50,
    discipline_score NUMERIC DEFAULT 100,        -- ADR-008: running discipline average
    financial_health_score NUMERIC DEFAULT 0,    -- ADR-008: composite leaderboard score
    status TEXT DEFAULT 'active'  -- 'active' = needs to play, 'waiting' = turn locked
);

-- ──── Player Loans ────
CREATE TABLE public.player_loans (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES public.users(id),
    principal NUMERIC,
    current_amount NUMERIC,
    interest_rate NUMERIC DEFAULT 0.12,
    month_taken INTEGER,
    status TEXT DEFAULT 'active'  -- 'active', 'paid'
);

-- ──── Player Asset Sales ────
CREATE TABLE public.player_sales (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES public.users(id),
    asset_type TEXT,
    amount_sold NUMERIC,
    penalty NUMERIC,
    cash_to_receive NUMERIC,
    month_sold_in INTEGER,
    month_to_credit INTEGER
);

-- ──── Relative Events (Admin-defined social scenarios) ────
CREATE TABLE public.relative_events (
    id SERIAL PRIMARY KEY,
    month INTEGER,
    relative_type TEXT,
    scenario TEXT
);

-- ──── Player Relative Trust Scores ────
CREATE TABLE public.player_relative_score (
    user_id UUID REFERENCES public.users(id),
    relative_type TEXT,
    total_spent NUMERIC DEFAULT 0,
    trust_score INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, relative_type)
);

-- ──── Player Relative Actions Log ────
CREATE TABLE public.player_relative_actions (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES public.users(id),
    month INTEGER,
    relative_type TEXT,
    action_taken TEXT,     -- 'none', 'medium', 'high'
    amount_spent NUMERIC
);

-- ──── Monthly Audit Logs ────
CREATE TABLE public.player_month_log (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES public.users(id),
    month INTEGER,
    starting_cash NUMERIC,
    ending_cash NUMERIC,
    net_worth NUMERIC,
    summary TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- ============================================================================
-- ROW LEVEL SECURITY
-- ============================================================================
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.case_study ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.optional_choices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.game_control ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.player_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.player_sales ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.player_loans ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.relative_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.player_relative_score ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.player_relative_actions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.player_month_log ENABLE ROW LEVEL SECURITY;

-- Public read policies
CREATE POLICY "Enable read/write for own user" ON public.users FOR ALL USING (auth.uid() = id);
CREATE POLICY "Enable read for all" ON public.case_study FOR SELECT USING (true);
CREATE POLICY "Enable read for all" ON public.events FOR SELECT USING (true);
CREATE POLICY "Enable read for all" ON public.optional_choices FOR SELECT USING (true);
CREATE POLICY "Enable read for all" ON public.game_control FOR SELECT USING (true);
CREATE POLICY "Enable read for all" ON public.relative_events FOR SELECT USING (true);

-- Player-specific policies
-- SECURITY: clients get SELECT-only on their OWN rows. All writes go through
-- the Flask backend using the service_role key (which bypasses RLS). Using
-- "FOR ALL" here would let players write their own financial state (cash,
-- net_worth, ...) straight from the browser and cheat the leaderboard.
-- Do NOT restore FOR ALL on these tables. See security_fix_rls.sql.
CREATE POLICY "player_state read own" ON public.player_state FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "player_sales read own" ON public.player_sales FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "player_loans read own" ON public.player_loans FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "player_relative_score read own" ON public.player_relative_score FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "player_relative_actions read own" ON public.player_relative_actions FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "player_month_log read own" ON public.player_month_log FOR SELECT USING (auth.uid() = user_id);

-- ============================================================================
-- ATOMIC MONTHLY PROCESSING RPC
-- Updated to handle trust_score and risk_level
-- ============================================================================
CREATE OR REPLACE FUNCTION public.process_month_atomically(
    p_updates_player_state JSON,
    p_updates_loans JSON,
    p_inserts_loans JSON,
    p_inserts_logs JSON,
    p_next_month INT
) RETURNS BOOLEAN AS $$
DECLARE
    current_m INT;
BEGIN
    -- Lock game control row
    SELECT current_month INTO current_m
    FROM public.game_control
    WHERE id = 1
    FOR UPDATE;

    -- Validate month transition
    IF p_next_month != current_m + 1 THEN
        RAISE EXCEPTION 'Invalid month transition: expected %, got %', current_m + 1, p_next_month;
    END IF;

    -- Idempotency check
    IF EXISTS (
        SELECT 1 FROM public.player_month_log
        WHERE month = p_next_month
    ) THEN
        RAISE EXCEPTION 'Month % already processed', p_next_month;
    END IF;

    -- Lock all player rows
    PERFORM 1 FROM public.player_state FOR UPDATE;

    -- ✅ UPDATE PLAYER STATE
    UPDATE public.player_state ps
    SET
        month = (data->>'month')::int,
        cash = (data->>'cash')::numeric,
        stocks = (data->>'stocks')::numeric,
        gold = (data->>'gold')::numeric,
        emergency_fund = (data->>'emergency_fund')::numeric,
        lifestyle_type = data->>'lifestyle_type',
        bike_status = (data->>'bike_status')::boolean,
        loans = (data->>'loans')::numeric,
        pending_cash_next_month = (data->>'pending_cash_next_month')::numeric,
        bike_lock_in_months = (data->>'bike_lock_in_months')::int,
        net_worth = (data->>'net_worth')::numeric,
        trust_score = COALESCE((data->>'trust_score')::numeric, ps.trust_score),
        risk_level = COALESCE((data->>'risk_level')::int, ps.risk_level),
        discipline_score = COALESCE((data->>'discipline_score')::numeric, ps.discipline_score),
        financial_health_score = COALESCE((data->>'financial_health_score')::numeric, ps.financial_health_score),
        status = data->>'status'
    FROM json_array_elements(p_updates_player_state) AS data
    WHERE ps.user_id = (data->>'user_id')::uuid;

    -- ✅ UPDATE LOANS
    UPDATE public.player_loans pl
    SET
        current_amount = (data->>'current_amount')::numeric,
        status = data->>'status'
    FROM json_array_elements(p_updates_loans) AS data
    WHERE pl.id = (data->>'id')::int;

    -- ✅ INSERT NEW LOANS
    INSERT INTO public.player_loans (
        user_id, principal, current_amount, interest_rate, month_taken, status
    )
    SELECT
        (data->>'user_id')::uuid,
        (data->>'principal')::numeric,
        (data->>'current_amount')::numeric,
        (data->>'interest_rate')::numeric,
        (data->>'month_taken')::int,
        data->>'status'
    FROM json_array_elements(p_inserts_loans) AS data;

    -- ✅ INSERT LOGS
    INSERT INTO public.player_month_log (
        user_id, month, starting_cash, ending_cash, net_worth, summary
    )
    SELECT
        (data->>'user_id')::uuid,
        (data->>'month')::int,
        (data->>'starting_cash')::numeric,
        (data->>'ending_cash')::numeric,
        (data->>'net_worth')::numeric,
        data->>'summary'
    FROM json_array_elements(p_inserts_logs) AS data;

    -- ✅ ADVANCE GAME MONTH
    UPDATE public.game_control
    SET
        current_month = p_next_month,
        game_status = 'active'
    WHERE id = 1;

    RETURN TRUE;

EXCEPTION
    WHEN OTHERS THEN
        RAISE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- SECURITY (QA-001): this SECURITY DEFINER function mutates every player's
-- financial state and advances the game month, with no internal admin check
-- of its own — it relies entirely on only being callable by the trusted
-- Flask backend (service_role). Without this revoke, Postgres' default
-- EXECUTE-to-PUBLIC grant lets PostgREST expose it to anon/authenticated at
-- /rest/v1/rpc/process_month_atomically, bypassing admin_required entirely.
-- See security_fix_rpc_grants.sql for the standalone fix on existing projects.
REVOKE EXECUTE ON FUNCTION public.process_month_atomically(json, json, json, json, integer) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.process_month_atomically(json, json, json, json, integer) FROM anon;
REVOKE EXECUTE ON FUNCTION public.process_month_atomically(json, json, json, json, integer) FROM authenticated;
GRANT EXECUTE ON FUNCTION public.process_month_atomically(json, json, json, json, integer) TO service_role;

-- ============================================================================
-- ATOMIC SELL RPC (QA-003)
-- Locks the player row and performs check-decrement-credit as one atomic
-- unit, closing the read-then-write race in the old /sell implementation.
-- See sell_asset_atomic_migration.sql for the standalone fix on existing projects.
-- ============================================================================
CREATE OR REPLACE FUNCTION public.sell_asset_atomic(
    p_user_id UUID,
    p_asset_type TEXT,
    p_amount NUMERIC,
    p_month INT,
    p_penalty_rate NUMERIC
) RETURNS JSON AS $$
DECLARE
    v_current NUMERIC;
    v_new_val NUMERIC;
    v_penalty NUMERIC;
    v_receive NUMERIC;
BEGIN
    IF p_asset_type NOT IN ('stocks', 'gold', 'emergency_fund') THEN
        RAISE EXCEPTION 'Invalid asset type: %', p_asset_type;
    END IF;
    IF p_amount IS NULL OR p_amount <= 0 THEN
        RAISE EXCEPTION 'Amount must be positive';
    END IF;

    PERFORM 1 FROM public.player_state WHERE user_id = p_user_id FOR UPDATE;

    EXECUTE format('SELECT %I FROM public.player_state WHERE user_id = $1', p_asset_type)
        INTO v_current USING p_user_id;

    IF v_current IS NULL THEN
        RAISE EXCEPTION 'Player not found';
    END IF;

    IF v_current < p_amount THEN
        RAISE EXCEPTION 'Insufficient % balance', p_asset_type;
    END IF;

    v_new_val := v_current - p_amount;
    v_penalty := p_amount * p_penalty_rate;
    v_receive := p_amount - v_penalty;

    EXECUTE format('UPDATE public.player_state SET %I = $1 WHERE user_id = $2', p_asset_type)
        USING v_new_val, p_user_id;

    INSERT INTO public.player_sales (
        user_id, asset_type, amount_sold, penalty, cash_to_receive, month_sold_in, month_to_credit
    ) VALUES (
        p_user_id, p_asset_type, p_amount, v_penalty, v_receive, p_month, p_month + 1
    );

    RETURN json_build_object(
        'new_balance', v_new_val,
        'penalty', v_penalty,
        'cash_to_receive', v_receive
    );
EXCEPTION
    WHEN OTHERS THEN
        RAISE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

REVOKE EXECUTE ON FUNCTION public.sell_asset_atomic(UUID, TEXT, NUMERIC, INT, NUMERIC) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.sell_asset_atomic(UUID, TEXT, NUMERIC, INT, NUMERIC) FROM anon;
REVOKE EXECUTE ON FUNCTION public.sell_asset_atomic(UUID, TEXT, NUMERIC, INT, NUMERIC) FROM authenticated;
GRANT EXECUTE ON FUNCTION public.sell_asset_atomic(UUID, TEXT, NUMERIC, INT, NUMERIC) TO service_role;

-- ============================================================================
-- COMPLETENESS (F-02): objects the backend depends on that used to live in
-- separate SQL files. Folded in here so a FRESH INSTALL IS THIS ONE FILE, with
-- no missing files or hidden manual steps. All statements are idempotent.
-- The standalone files (admin_setup.sql, idempotency_migration.sql,
-- supabase_signup_trigger.sql) are retained ONLY for retrofitting an older
-- live project and for the admin-granting data step; they are NOT needed for a
-- fresh install. See DEPLOY_FRESH.md §2.
-- ============================================================================

-- ──── Admin allowlist (server-only; gates every admin route) ────
-- RLS ON with NO policies => anon/authenticated clients are fully denied; only
-- the Flask backend (service_role key) can read it, which is who checks admin.
CREATE TABLE IF NOT EXISTS public.admins (
    user_id    UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.admins ENABLE ROW LEVEL SECURITY;
-- (Grant a specific person admin AFTER install — see DEPLOY_FRESH.md §4a /
--  admin_setup.sql: insert their auth.users.id into public.admins.)

-- ──── Per-(user, month) action idempotency guard ────
-- Backs buy-choice / relative-help claims (game_service.mark_action). Without
-- this table those actions silently fail. RLS ON, no client policy (server-only).
CREATE TABLE IF NOT EXISTS public.player_month_actions (
    user_id     UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    month       INTEGER NOT NULL,
    action_key  TEXT NOT NULL,   -- e.g. 'choice:12' or 'relative:parent'
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    PRIMARY KEY (user_id, month, action_key)
);
ALTER TABLE public.player_month_actions ENABLE ROW LEVEL SECURITY;

-- ──── Signup trigger: auto-create a public.users row on account creation ────
-- public.player_state.user_id REFERENCES public.users(id); nothing in the Flask
-- backend inserts into public.users, so without this trigger the first
-- /allocate call FK-fails. SECURITY DEFINER so it can write public.users.
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public
AS $$
BEGIN
    INSERT INTO public.users (id, email, name)
    VALUES (
        new.id,
        new.email,
        COALESCE(
            new.raw_user_meta_data->>'name',
            new.raw_user_meta_data->>'full_name',
            split_part(new.email, '@', 1)
        )
    )
    ON CONFLICT (id) DO NOTHING;   -- never clobber an existing profile
    RETURN new;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Backfill profiles for any auth users that already exist (harmless on a truly
-- fresh project; useful if test users were created before this ran).
INSERT INTO public.users (id, email, name)
SELECT u.id, u.email,
       COALESCE(u.raw_user_meta_data->>'name',
                u.raw_user_meta_data->>'full_name',
                split_part(u.email, '@', 1))
FROM auth.users u
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- FRESH INSTALL COMPLETE. Running this single file on an empty Supabase project
-- creates every table, RPC, function, trigger, RLS policy, and grant the
-- backend requires. The only post-install step is granting a specific admin
-- (data, not schema) — see DEPLOY_FRESH.md §4a.
-- ============================================================================
