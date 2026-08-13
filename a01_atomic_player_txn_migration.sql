-- ############################################################################
-- ##  A-01 FIX — Cross-action cash race condition                           ##
-- ##  INCREMENTAL PATCH. Apply once to the live project (SQL editor/CLI).    ##
-- ##  Idempotent: CREATE OR REPLACE + REVOKE/GRANT. No data is modified.     ##
-- ############################################################################
--
-- PROBLEM (see FULL_SYSTEM_AUDIT.md A-01):
--   take_loan, allocate_month, handle_relative, choice_service.execute_choice,
--   negotiate_commit and courtship_marry all read player_state in Python, computed
--   a new balance from that snapshot, and wrote it back. The per-action
--   idempotency keys stop a DUPLICATE of the SAME action but do not serialize
--   DIFFERENT actions, so two concurrent same-month actions (e.g. take-loan +
--   allocate) both read cash=X and the last write wins — losing or duplicating money.
--
-- FIX:
--   One serialization primitive, used by every cash-mutating route, following the
--   exact pattern process_month_atomically and sell_asset_atomic already use:
--   lock the player's row FOR UPDATE, re-read the AUTHORITATIVE balance under that
--   lock, re-validate affordability, then apply the caller's ADDITIVE deltas and
--   child-row writes in one transaction. Two concurrent calls block on the row lock
--   and compose correctly (X + loan − invested), so nothing is lost.
--
--   The economic FORMULAS stay in Python (EMI, negotiation outcome, marriage asset
--   injection, scoring). This function only serialises the apply step and re-checks
--   the balance-dependent guard under the lock. Deltas are ADDITIVE — never absolute
--   values derived from a stale read — which is what makes concurrent actions safe.
--
--   Idempotency is folded INTO this function (the claim insert and the mutation are
--   now one transaction), removing the old "claimed-but-then-failed" soft-lock.

CREATE OR REPLACE FUNCTION public.player_apply_atomic(
    p_user_id             UUID,
    p_month               INT,
    p_action_key          TEXT,     -- NULL => no idempotency claim
    p_require_cash        NUMERIC,  -- NULL => no floor; else require cash >= this BEFORE deltas
    p_deltas              JSONB,    -- additive to numeric columns
    p_sets                JSONB,    -- absolute overrides (whitelisted columns only)
    p_clamp_satisfaction  BOOLEAN,
    p_recompute_networth  BOOLEAN,
    p_loan_inserts        JSONB,    -- array of loan rows to INSERT
    p_loan_updates        JSONB     -- array of {id, current_amount, status} to UPDATE
) RETURNS JSON AS $$
DECLARE
    v            public.player_state%ROWTYPE;
    d            JSONB := COALESCE(p_deltas, '{}'::jsonb);
    s            JSONB := COALESCE(p_sets,   '{}'::jsonb);
    v_cash       NUMERIC;
    v_stocks     NUMERIC;
    v_gold       NUMERIC;
    v_ef         NUMERIC;
    v_loans      NUMERIC;
    v_trust      NUMERIC;
    v_sat        NUMERIC;
    v_hmod       NUMERIC;
    v_nw         NUMERIC;
    li           JSONB;
    lu           JSONB;
BEGIN
    -- 1. Idempotency claim, atomic with the mutation below. A concurrent SAME-action
    --    call blocks on the PK until this txn commits, then gets a unique_violation.
    IF p_action_key IS NOT NULL THEN
        BEGIN
            INSERT INTO public.player_month_actions (user_id, month, action_key)
            VALUES (p_user_id, p_month, p_action_key);
        EXCEPTION WHEN unique_violation THEN
            RAISE EXCEPTION 'DUPLICATE_ACTION';
        END;
    END IF;

    -- 2. Lock this player's row. A concurrent DIFFERENT action blocks here until we
    --    commit, so both compose on the authoritative balance instead of racing.
    SELECT * INTO v FROM public.player_state WHERE user_id = p_user_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'PLAYER_NOT_FOUND';
    END IF;

    -- 3. Affordability guard, re-checked under the lock against authoritative cash.
    IF p_require_cash IS NOT NULL AND v.cash < p_require_cash THEN
        RAISE EXCEPTION 'INSUFFICIENT_CASH';
    END IF;

    -- 4. Apply ADDITIVE deltas (missing keys => 0 => no change).
    v_cash   := v.cash                                  + COALESCE((d->>'cash')::numeric, 0);
    v_stocks := v.stocks                                + COALESCE((d->>'stocks')::numeric, 0);
    v_gold   := v.gold                                  + COALESCE((d->>'gold')::numeric, 0);
    v_ef     := v.emergency_fund                        + COALESCE((d->>'emergency_fund')::numeric, 0);
    v_loans  := v.loans                                 + COALESCE((d->>'loans')::numeric, 0);
    v_trust  := COALESCE(v.trust_score, 0)              + COALESCE((d->>'trust_score')::numeric, 0);
    v_sat    := COALESCE(v.spouse_satisfaction, 60)     + COALESCE((d->>'spouse_satisfaction')::numeric, 0);
    v_hmod   := COALESCE(v.household_expense_modifier,0)+ COALESCE((d->>'household_expense_modifier')::numeric, 0);

    -- Floors: assets and trust cannot go negative; satisfaction clamps 0..100.
    -- Cash: only sub-Rs2 rounding noise is snapped to 0 (this reproduces the
    -- max(0, available - invested) tolerance allocate_month used for float/display
    -- rounding). Larger negatives are PRESERVED so behaviour that intentionally
    -- allows negative cash (e.g. wedding + a negative month-6 spouse flow, which
    -- the safety net covers next month) is unchanged. p_require_cash still guards
    -- every genuine spend, so cash never drops materially below zero here.
    IF v_cash < 0 AND v_cash >= -2 THEN v_cash := 0; END IF;
    IF v_stocks < 0 THEN v_stocks := 0; END IF;
    IF v_gold   < 0 THEN v_gold   := 0; END IF;
    IF v_ef     < 0 THEN v_ef     := 0; END IF;
    IF v_loans  < 0 THEN v_loans  := 0; END IF;
    IF v_trust  < 0 THEN v_trust  := 0; END IF;
    IF p_clamp_satisfaction THEN
        v_sat := GREATEST(0, LEAST(100, v_sat));
    END IF;

    IF p_recompute_networth THEN
        v_nw := v_cash + v_stocks + v_gold + v_ef - v_loans;
    ELSE
        v_nw := v.net_worth;   -- preserve existing behaviour (these routes never set it)
    END IF;

    -- 5. Persist balances.
    UPDATE public.player_state SET
        cash                       = v_cash,
        stocks                     = v_stocks,
        gold                       = v_gold,
        emergency_fund             = v_ef,
        loans                      = v_loans,
        trust_score                = v_trust,
        spouse_satisfaction        = v_sat,
        household_expense_modifier = v_hmod,
        net_worth                  = v_nw
    WHERE user_id = p_user_id;

    -- 6. Absolute sets — only these columns may be set this way.
    IF s ? 'spouse_archetype' THEN
        UPDATE public.player_state SET spouse_archetype = (s->>'spouse_archetype') WHERE user_id = p_user_id;
    END IF;
    IF s ? 'insurance_plan' THEN
        UPDATE public.player_state SET insurance_plan = (s->>'insurance_plan') WHERE user_id = p_user_id;
    END IF;
    IF s ? 'risk_level' THEN
        UPDATE public.player_state SET risk_level = (s->>'risk_level')::int WHERE user_id = p_user_id;
    END IF;
    IF s ? 'financial_health_score' THEN
        UPDATE public.player_state SET financial_health_score = (s->>'financial_health_score')::numeric WHERE user_id = p_user_id;
    END IF;
    IF s ? 'status' THEN
        UPDATE public.player_state SET status = (s->>'status') WHERE user_id = p_user_id;
    END IF;

    -- 7. Loan inserts (e.g. a new voluntary loan, or a spouse's brought loan).
    IF p_loan_inserts IS NOT NULL THEN
        FOR li IN SELECT * FROM jsonb_array_elements(p_loan_inserts) LOOP
            INSERT INTO public.player_loans
                (user_id, principal, current_amount, interest_rate, month_taken, term_months, loan_type, emi, status)
            VALUES (
                p_user_id,
                (li->>'principal')::numeric,
                (li->>'current_amount')::numeric,
                (li->>'interest_rate')::numeric,
                (li->>'month_taken')::int,
                (li->>'term_months')::int,       -- NULL-safe: missing => NULL
                COALESCE(li->>'loan_type', 'player'),
                (li->>'emi')::numeric,            -- NULL-safe
                COALESCE(li->>'status', 'active')
            );
        END LOOP;
    END IF;

    -- 8. Loan updates (e.g. allocate-month prepayment applied oldest-first in Python).
    IF p_loan_updates IS NOT NULL THEN
        FOR lu IN SELECT * FROM jsonb_array_elements(p_loan_updates) LOOP
            UPDATE public.player_loans
               SET current_amount = (lu->>'current_amount')::numeric,
                   status         = COALESCE(lu->>'status', 'active')
             WHERE id = (lu->>'id')::int AND user_id = p_user_id;
        END LOOP;
    END IF;

    -- 9. Return the fresh authoritative row.
    SELECT * INTO v FROM public.player_state WHERE user_id = p_user_id;
    RETURN row_to_json(v);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Server-only, same lockdown as sell_asset_atomic / process_month_atomically.
REVOKE EXECUTE ON FUNCTION public.player_apply_atomic(UUID, INT, TEXT, NUMERIC, JSONB, JSONB, BOOLEAN, BOOLEAN, JSONB, JSONB) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.player_apply_atomic(UUID, INT, TEXT, NUMERIC, JSONB, JSONB, BOOLEAN, BOOLEAN, JSONB, JSONB) FROM anon;
REVOKE EXECUTE ON FUNCTION public.player_apply_atomic(UUID, INT, TEXT, NUMERIC, JSONB, JSONB, BOOLEAN, BOOLEAN, JSONB, JSONB) FROM authenticated;
GRANT EXECUTE ON FUNCTION public.player_apply_atomic(UUID, INT, TEXT, NUMERIC, JSONB, JSONB, BOOLEAN, BOOLEAN, JSONB, JSONB) TO service_role;
