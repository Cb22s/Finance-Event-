-- ############################################################################
-- ##  INCREMENTAL PATCH — NOT part of a fresh install (F-02).                ##
-- ##  supabase.sql already ships sell_asset_atomic (locked to service_role). ##
-- ##  Use ONLY to retrofit an older live project. Idempotent.                ##
-- ############################################################################

-- ============================================================================
-- ATOMIC SELL — QA-003 fix
-- Money Master — Financial Simulation Game
--
-- HOW TO APPLY:
--   Supabase Dashboard -> SQL Editor -> paste this file -> Run.
--   Safe to run more than once (idempotent — CREATE OR REPLACE + REVOKE/GRANT).
--
-- PROBLEM:
--   POST /sell read the asset balance, validated it in Python, then issued a
--   separate UPDATE + INSERT with no locking or idempotency guard. Two
--   concurrent identical sell requests (double-click, retry-on-timeout)
--   could both pass the stale-read balance check and both insert a
--   player_sales credit row — crediting cash TWICE for a single reduction
--   in the asset balance.
--
-- FIX:
--   sell_asset_atomic() locks the player's row (FOR UPDATE — the same
--   pattern process_month_atomically already uses), re-reads the balance
--   under that lock, and performs the decrement + player_sales insert in
--   one transaction. A second concurrent call blocks until the first
--   commits, then sees the already-decremented balance and correctly fails
--   if there isn't enough left. No behavior change to the 10%
--   penalty / next-month-credit game rule — only the mechanics are atomic.
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

    -- Lock this player's row so a concurrent call blocks until this one commits.
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

-- Server-only, same lesson as QA-001: lock this down at creation time.
REVOKE EXECUTE ON FUNCTION public.sell_asset_atomic(UUID, TEXT, NUMERIC, INT, NUMERIC) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.sell_asset_atomic(UUID, TEXT, NUMERIC, INT, NUMERIC) FROM anon;
REVOKE EXECUTE ON FUNCTION public.sell_asset_atomic(UUID, TEXT, NUMERIC, INT, NUMERIC) FROM authenticated;
GRANT EXECUTE ON FUNCTION public.sell_asset_atomic(UUID, TEXT, NUMERIC, INT, NUMERIC) TO service_role;
