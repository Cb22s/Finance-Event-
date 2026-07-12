-- =============================================================================
-- FAIRNESS FIXES MIGRATION (ADR-008 + ADR-009, ratified 2026-07-11)
-- Run this in the Supabase SQL editor BETWEEN games (never mid-game, ADR-012).
--
-- ADR-008: composite Financial Health Score replaces net-worth-only ranking.
-- ADR-009 needs no schema change (global market seeding is backend-only),
--          but deploy the backend at the same time as this migration.
-- =============================================================================

-- 1. New player_state columns (additive, safe)
ALTER TABLE public.player_state
    ADD COLUMN IF NOT EXISTS discipline_score NUMERIC DEFAULT 100,
    ADD COLUMN IF NOT EXISTS financial_health_score NUMERIC DEFAULT 0;

-- 2. Extend the atomic month processor to persist the new fields
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

    -- UPDATE PLAYER STATE (now includes ADR-008 score fields)
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

    -- UPDATE LOANS
    UPDATE public.player_loans pl
    SET
        current_amount = (data->>'current_amount')::numeric,
        status = data->>'status'
    FROM json_array_elements(p_updates_loans) AS data
    WHERE pl.id = (data->>'id')::int;

    -- INSERT NEW LOANS
    INSERT INTO public.player_loans (user_id, principal, current_amount, interest_rate, month_taken, status)
    SELECT
        (data->>'user_id')::uuid,
        (data->>'principal')::numeric,
        (data->>'current_amount')::numeric,
        (data->>'interest_rate')::numeric,
        (data->>'month_taken')::int,
        data->>'status'
    FROM json_array_elements(p_inserts_loans) AS data;

    -- INSERT MONTH LOGS
    INSERT INTO public.player_month_log (user_id, month, starting_cash, ending_cash, net_worth, summary)
    SELECT
        (data->>'user_id')::uuid,
        (data->>'month')::int,
        (data->>'starting_cash')::numeric,
        (data->>'ending_cash')::numeric,
        (data->>'net_worth')::numeric,
        data->>'summary'
    FROM json_array_elements(p_inserts_logs) AS data;

    -- Advance the month
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
