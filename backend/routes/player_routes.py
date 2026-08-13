# =============================================================================
# PLAYER ROUTES — All player-facing API endpoints
# =============================================================================

from flask import Blueprint, request, jsonify
from supabase_client import supabase
from services.auth_service import get_user_id
from services.game_service import (
    get_game_state, get_player, get_total_loans,
    get_optional_choices, get_trust_scores, get_all_event_logs,
    get_pending_sales, fair_roll, mark_action, get_active_loans,
    get_market_scenario_row, get_month_allocation, allocation_done, allocation_key,
    action_done, apply_player_txn, PlayerTxnError, require_playable
)
from models.constants import (
    INITIAL_BUDGET, SELL_PENALTY_RATE, TRUST_HELP_AMOUNTS, TRUST_SCORE_GAIN,
    VALID_RELATIVE_TYPES,
    LIFESTYLE_COSTS, ARCHETYPES, WEDDING_COST, SPOUSE_BASE_EXPENSE, MARRIAGE_MONTH,
    MONTHLY_INCOME, LOAN_INTEREST_RATE, LOAN_TERM_OPTIONS, LOAN_MIN_AMOUNT,
    MAX_TOTAL_DEBT_MULTIPLE, MAX_EMI_TO_INCOME, INSURANCE_PLANS,
    NEGOTIATION_MAX_ROUNDS, SATISFACTION_START
)
from services import negotiation_service as negsvc
from services import ai_service
from models.negotiation_intents import IntentError, validate
from engine.monthly_processor import _amortized_emi
from engine.scoring import calculate_financial_health_score
from engine.market_engine import (
    calculate_risk_score, resolve_market_scenario, calculate_inflation_adjustment
)

player_bp = Blueprint('player', __name__)


# ──────────────────────────────────────────────
# GAME STATUS
# ──────────────────────────────────────────────
@player_bp.route('/game-status', methods=['GET'])
def get_status():
    game = get_game_state()
    return jsonify(game)


# ──────────────────────────────────────────────
# CASE STUDY
# ──────────────────────────────────────────────
@player_bp.route('/case-study', methods=['GET'])
def get_case_study():
    res = supabase.table('case_study').select('*').limit(1).execute()
    return jsonify(res.data[0] if res.data else {})


# ──────────────────────────────────────────────
# MONTH 1 ALLOCATION
# Backend validates total = ₹1,00,000
# ──────────────────────────────────────────────
@player_bp.route('/allocate', methods=['POST'])
def allocate_month1():
    user_id = get_user_id(request)
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    game = get_game_state()
    if not game or game['game_status'] != 'active':
        return jsonify({"error": "Game is not currently active."}), 400

    # Check if player already allocated
    existing = get_player(user_id)
    if existing:
        return jsonify({"error": "You have already allocated for this game."}), 400

    data = request.json
    try:
        fields = ['rent', 'transport', 'food', 'family', 'stocks',
                   'gold', 'emergency_fund', 'misc', 'bike_down_payment']
        total = sum(float(data.get(f, 0)) for f in fields)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid numerical data."}), 400

    if abs(total - INITIAL_BUDGET) > 0.1:
        return jsonify({
            "error": f"Must allocate exactly ₹{INITIAL_BUDGET:,}. Current total: ₹{total:,.0f}"
        }), 400

    bike_status = bool(data.get('bike_status', False))
    lifestyle = data.get('lifestyle_type', 'city')

    if lifestyle not in ('city', 'outer'):
        return jsonify({"error": "Invalid lifestyle type. Must be 'city' or 'outer'."}), 400

    stocks = float(data.get('stocks', 0))
    gold_val = float(data.get('gold', 0))
    emergency = float(data.get('emergency_fund', 0))

    # Money conservation: everything the player didn't invest and didn't spend
    # on the bike stays as starting CASH. Previously only 'misc' was kept and
    # the rent/transport/food/family buckets silently vanished (and month-1 net
    # worth was hard-coded to the full budget), which made net worth appear to
    # crash between month 1 and month 2. Recurring living costs are charged from
    # month 2 onward by the monthly processor, so month-1 living isn't lost here.
    bike_down_payment = float(data.get('bike_down_payment', 0))
    cash = (float(data.get('misc', 0)) + float(data.get('rent', 0))
            + float(data.get('transport', 0)) + float(data.get('food', 0))
            + float(data.get('family', 0)))

    # The bike down payment is the one bucket genuinely consumed — it buys the
    # bike (which grants the transport discount + EMI). Only deduct it if a bike
    # was actually purchased, so the money can't disappear on a mismatch.
    if not bike_status:
        cash += bike_down_payment  # no bike bought → keep the money as cash
        bike_down_payment = 0

    # Validate no negative values
    if any(v < 0 for v in [cash, stocks, gold_val, emergency, bike_down_payment]):
        return jsonify({"error": "Allocation values cannot be negative."}), 400

    # Honest month-1 net worth = assets actually held (no loans yet). The bike
    # down payment is spent, so it is not counted as an asset.
    initial_net_worth = cash + stocks + gold_val + emergency

    # Initial risk + Financial Health Score (ADR-008) — deterministic from allocation
    initial_state = {"cash": cash, "stocks": stocks, "gold": gold_val,
                     "emergency_fund": emergency, "loans": 0}
    initial_risk = calculate_risk_score(initial_state)
    monthly_expense = LIFESTYLE_COSTS.get(lifestyle, LIFESTYLE_COSTS['city'])['total']
    initial_score = calculate_financial_health_score(
        net_worth=initial_net_worth, month=1,
        emergency_fund=emergency, monthly_expense=monthly_expense,
        loans=0, total_assets=cash + stocks + gold_val + emergency,
        risk_score=initial_risk, discipline_avg=100
    )

    new_state = {
        "user_id": user_id,
        "month": 1,
        "cash": cash,
        "stocks": stocks,
        "gold": gold_val,
        "emergency_fund": emergency,
        "lifestyle_type": lifestyle,
        "bike_status": bike_status,
        "bike_lock_in_months": 3 if bike_status else 0,
        "loans": 0,
        "pending_cash_next_month": 0,
        "net_worth": initial_net_worth,
        "trust_score": 0,
        "risk_level": initial_risk,
        "discipline_score": 100,
        "financial_health_score": initial_score['score'],
        "status": "waiting"
    }

    # D-10: atomically claim the month-1 allocation. The upsert makes player_state
    # idempotent, but the month_log insert is not — two concurrent first-allocations
    # would each pass the get_player() pre-check and write a duplicate month-1 log.
    # The player_month_actions PK makes the second caller lose the claim cleanly.
    if not mark_action(user_id, 1, allocation_key(1)):
        return jsonify({"error": "You have already allocated for this game."}), 400

    try:
        supabase.table('player_state').upsert(new_state).execute()
        supabase.table('player_month_log').insert({
            "user_id": user_id,
            "month": 1,
            "starting_cash": INITIAL_BUDGET,
            "ending_cash": cash,
            "net_worth": initial_net_worth,
            "summary": "💼 Initial Allocation Completed. Your financial journey begins!"
        }).execute()
    except Exception as e:
        print(f"DEBUG: Allocation Database Error: {e}")
        return jsonify({"error": f"Database processing failed: {str(e)}"}), 500

    return jsonify({
        "message": "Month 1 allocation confirmed. Your turn is locked.",
        "state": new_state
    })


# ──────────────────────────────────────────────
# DASHBOARD — Full player state + event history
# ──────────────────────────────────────────────
@player_bp.route('/dashboard', methods=['GET'])
def get_dashboard():
    user_id = get_user_id(request)
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    player = get_player(user_id)
    if not player:
        return jsonify({"error": "No player state found"}), 404

    player['loans'] = get_total_loans(user_id)
    game = get_game_state()
    choices = get_optional_choices(player['month'])
    trust_scores = get_trust_scores(user_id)
    event_logs = get_all_event_logs(user_id)

    # ── Courtship & Spouse metadata ──
    revealed_rows = supabase.table('player_spouse_reveals').select('*').eq('user_id', user_id).execute().data or []
    
    spouse_options = []
    for arch_id, data in ARCHETYPES.items():
        spouse_options.append({
            "id": arch_id,
            "name": data["name"],
            "description": data["description"]
        })
        
    courtship = {
        "marriage_month": MARRIAGE_MONTH,
        "wedding_cost": WEDDING_COST,
        "spouse_base_expense": SPOUSE_BASE_EXPENSE,
        "extra_date_cost": 5000,
        "spouse_options": spouse_options,
        "reveals": revealed_rows,
        "dates_used": len(revealed_rows)
    }

    # ── Market scenario for the month just played (what happened and WHY) ──
    month = int(player.get('month') or 1)
    scenario_row = get_market_scenario_row(month)
    if scenario_row:
        market = {
            "name": scenario_row.get('name'),
            "reason": scenario_row.get('reason'),
            "stock_pct": float(scenario_row.get('stock_pct') or 0),
            "gold_pct": float(scenario_row.get('gold_pct') or 0),
            "source": "admin"
        }
    else:
        game_auto = bool((game or {}).get('auto_market', False))
        market = resolve_market_scenario(month, None, game_auto)

    # ── Loan detail (the dashboard previously showed only a balance number) ──
    loans_detail = get_active_loans(user_id)
    outstanding = sum(float(l['current_amount']) for l in loans_detail)
    debt_cap = MONTHLY_INCOME * MAX_TOTAL_DEBT_MULTIPLE
    existing_emi = sum(float(l.get('emi') or 0) for l in loans_detail)
    loan_info = {
        "active": loans_detail,
        "outstanding": round(outstanding, 2),
        "debt_cap": debt_cap,
        "borrowing_headroom": round(max(0, debt_cap - outstanding), 2),
        "monthly_emi": round(existing_emi, 2),
        "emi_cap": MONTHLY_INCOME * MAX_EMI_TO_INCOME,
        "interest_rate": LOAN_INTEREST_RATE,
        "term_options": LOAN_TERM_OPTIONS,
        "min_amount": LOAN_MIN_AMOUNT,
        "can_borrow_this_month": not action_done(user_id, month, f"loan:{month}")
    }

    # ── Allocation status: what the player must still do this round ──
    allocation = {
        "required": month >= 2 and float(player.get('cash', 0)) > 0.5,
        "done": allocation_done(user_id, month),
        "available_cash": round(float(player.get('cash', 0)), 2),
        "record": get_month_allocation(user_id, month)
    }

    return jsonify({
        "player": player,
        "game": game,
        "choices": choices,
        "trust_scores": trust_scores,
        "event_logs": event_logs,
        "courtship": courtship,
        "market": market,
        "loan_info": loan_info,
        "allocation": allocation,
        "insurance": {
            "current": player.get('insurance_plan') or 'none',
            "plans": [{"id": k, **v} for k, v in INSURANCE_PLANS.items()]
        },
        "negotiation": _dashboard_negotiation(user_id, player, game)
    })


def _dashboard_negotiation(user_id, player, game):
    """Negotiation state for the dashboard. Never raises — it is one panel."""
    try:
        ctx, err = _negotiation_context(user_id, player, game)
        if err:
            return {"active": False, "note": err}
        return {
            "active": True,
            "proposal": ctx['proposal'],
            "round": ctx['round'],
            "max_rounds": NEGOTIATION_MAX_ROUNDS,
            "satisfaction": ctx['satisfaction'],
            "history": [
                {"round": r.get('round'), "raw_text": r.get('raw_text'),
                 "intent": r.get('intent'), "outcome": r.get('outcome')}
                for r in ctx['history'] if r.get('confirmed')
            ],
        }
    except Exception:
        return {"active": False, "note": "unavailable"}


# ──────────────────────────────────────────────
# MONTHLY ALLOCATION (months 2-12)
# The core loop fix: every month the player must decide where their available
# cash goes. Previously allocation happened ONCE in month 1 and cash simply piled
# up untouched for the remaining 11 rounds, so the player was a spectator and the
# only decision that ever mattered was made before they had seen a single event.
# ──────────────────────────────────────────────
@player_bp.route('/allocate-month', methods=['POST'])
def allocate_month():
    user_id = get_user_id(request)
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    # A-02: unified gate — active game + turn not locked/processing.
    player, game, err = require_playable(user_id)
    if err:
        return jsonify({"error": err[0]}), err[1]

    month = int(player['month'])
    if month < 2:
        return jsonify({"error": "Month 1 uses the initial allocation screen."}), 400

    if allocation_done(user_id, month):
        return jsonify({"error": f"You have already allocated for Month {month}."}), 400

    available = float(player.get('cash', 0))
    if available <= 0:
        return jsonify({"error": "You have no cash available to allocate."}), 400

    data = request.json or {}
    try:
        to_stocks = float(data.get('stocks', 0))
        to_gold = float(data.get('gold', 0))
        to_ef = float(data.get('emergency_fund', 0))
        to_prepay = float(data.get('loan_prepay', 0))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid numerical data."}), 400

    buckets = [to_stocks, to_gold, to_ef, to_prepay]
    if any(v < 0 for v in buckets):
        return jsonify({"error": "Allocation values cannot be negative."}), 400

    # ── Money conservation by CONSTRUCTION ────────────────────────────────────
    # Whatever the player does not invest simply stays as cash. The server derives
    # the residual instead of requiring the client to send a `keep_cash` that sums
    # to exactly `available`.
    #
    # The old "must total exactly" rule was unshippable: `cash` carries decimals
    # from market growth (e.g. 8117.51), the frontend rendered it with Math.floor
    # (8,117) while the backend rendered it with round() (8,118), and the client
    # re-parsed its own DISPLAYED string back into a number. The player allocated
    # every rupee the screen showed them and still got
    # "Must allocate exactly ... 8,118 / current total 8,117" with no way to win.
    # Deriving the remainder here removes the whole class of bug AND the rule the
    # player had to satisfy.
    invested = sum(buckets)
    if invested > available + 1.0:
        return jsonify({
            "error": f"You allocated ₹{invested:,.0f} but only have ₹{available:,.0f} available."
        }), 400

    keep_cash = max(0.0, available - invested)

    # ── Loan prepayment: cannot prepay more than is outstanding ──
    active_loans = get_active_loans(user_id)
    outstanding = sum(float(l['current_amount']) for l in active_loans)
    if to_prepay > outstanding + 0.5:
        return jsonify({
            "error": f"Prepayment ₹{to_prepay:,.0f} exceeds outstanding debt of ₹{outstanding:,.0f}."
        }), 400

    # Prepayment distribution (oldest-loan-first), computed from the snapshot and
    # applied atomically below as loan_updates.
    loan_writes = []
    remaining_prepay = to_prepay
    for loan in sorted(active_loans, key=lambda l: l['id']):
        if remaining_prepay <= 0:
            break
        bal = float(loan['current_amount'])
        pay = min(bal, remaining_prepay)
        new_bal = round(bal - pay, 2)
        remaining_prepay -= pay
        loan_writes.append({
            "id": loan['id'],
            "current_amount": new_bal,
            "status": 'paid' if new_bal <= 0.01 else 'active'
        })

    # A-01: one atomic, row-locked transaction. Balances move as ADDITIVE deltas
    # (cash out, assets in, loans down) so a concurrent loan/relative/etc. composes
    # correctly instead of racing. The alloc:{month} claim is inside the same txn.
    # require_cash carries the ±1 rupee tolerance the old max(0, available-invested)
    # allowed for float/display rounding.
    try:
        apply_player_txn(
            user_id, month, action_key=allocation_key(month),
            require_cash=max(0.0, round(invested, 2) - 1.0),
            deltas={
                "cash": -round(invested, 2),
                "stocks": round(to_stocks, 2),
                "gold": round(to_gold, 2),
                "emergency_fund": round(to_ef, 2),
                "loans": -round(to_prepay, 2),
            },
            loan_updates=loan_writes,
        )
    except PlayerTxnError as e:
        if e.kind == 'DUPLICATE_ACTION':
            return jsonify({"error": f"You have already allocated for Month {month}."}), 400
        if e.kind == 'INSUFFICIENT_CASH':
            return jsonify({"error": "Your available cash changed — refresh and try again."}), 409
        if e.kind == 'PLAYER_NOT_FOUND':
            return jsonify({"error": "No player state found."}), 404
        return jsonify({"error": "Allocation could not be processed. No money moved."}), 400
    except Exception as e:
        print(f"DEBUG: Monthly allocation DB error: {e}")
        return jsonify({"error": f"Database processing failed: {str(e)}"}), 500

    # Best-effort allocation record (audit/dashboard display; not a balance).
    try:
        supabase.table('player_month_allocations').insert({
            "user_id": user_id,
            "month": month,
            "available_cash": round(available, 2),
            "to_stocks": round(to_stocks, 2),
            "to_gold": round(to_gold, 2),
            "to_emergency_fund": round(to_ef, 2),
            "to_loan_prepay": round(to_prepay, 2),
            "kept_as_cash": round(keep_cash, 2)
        }).execute()
    except Exception as e:
        print(f"DEBUG: allocation record insert failed: {e}")

    return jsonify({
        "message": f"Month {month} allocation confirmed.",
        "allocated": {
            "stocks": to_stocks, "gold": to_gold, "emergency_fund": to_ef,
            "loan_prepay": to_prepay, "kept_as_cash": keep_cash
        }
    })


# ──────────────────────────────────────────────
# INSURANCE — buy / change / cancel cover
# Replaces the Social Investment (trust) mechanic, which cost the player real
# money while contributing almost nothing to the ADR-008 score and teaching no
# financial lesson. Insurance is a genuine risk-management decision.
# ──────────────────────────────────────────────
@player_bp.route('/insurance', methods=['POST'])
def set_insurance():
    user_id = get_user_id(request)
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    # A-02: unified gate — active game + turn not locked/processing.
    player, game, err = require_playable(user_id)
    if err:
        return jsonify({"error": err[0]}), err[1]

    plan_id = (request.json or {}).get('plan', 'none')
    if plan_id not in INSURANCE_PLANS:
        return jsonify({"error": f"Unknown plan. Choose one of {list(INSURANCE_PLANS)}."}), 400

    try:
        supabase.table('player_state').update({
            "insurance_plan": plan_id
        }).eq('user_id', user_id).execute()
    except Exception as e:
        return jsonify({"error": f"Database processing failed: {str(e)}"}), 500

    plan = INSURANCE_PLANS[plan_id]
    return jsonify({
        "message": f"Cover set to {plan['name']}."
                   + (f" Rs{plan['premium']:,}/month will be deducted from next month."
                      if plan['premium'] else " No premium."),
        "plan": {"id": plan_id, **plan}
    })


# ──────────────────────────────────────────────
# TAKE A LOAN (player-initiated)
# Previously the dashboard rendered a loan BALANCE but there was no way to
# borrow — the only loans that existed were the involuntary auto-loans issued
# when a player went cash-negative. This makes debt a strategy, not a punishment.
# ──────────────────────────────────────────────
@player_bp.route('/loan', methods=['POST'])
def take_loan():
    user_id = get_user_id(request)
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    # A-02: unified gate — active game + turn not locked/processing.
    player, game, err = require_playable(user_id)
    if err:
        return jsonify({"error": err[0]}), err[1]

    month = int(player['month'])
    data = request.json or {}
    try:
        amount = float(data.get('amount', 0))
        term = int(data.get('term_months', 6))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid loan request."}), 400

    if term not in LOAN_TERM_OPTIONS:
        return jsonify({"error": f"Term must be one of {LOAN_TERM_OPTIONS} months."}), 400

    if amount < LOAN_MIN_AMOUNT:
        return jsonify({"error": f"Minimum loan is ₹{LOAN_MIN_AMOUNT:,}."}), 400

    # ── Debt ceiling ──
    active_loans = get_active_loans(user_id)
    outstanding = sum(float(l['current_amount']) for l in active_loans)
    debt_cap = MONTHLY_INCOME * MAX_TOTAL_DEBT_MULTIPLE
    if outstanding + amount > debt_cap:
        headroom = max(0, debt_cap - outstanding)
        return jsonify({
            "error": f"Debt ceiling is ₹{debt_cap:,.0f}. You can borrow at most "
                     f"₹{headroom:,.0f} more."
        }), 400

    # ── EMI affordability: total EMIs may not exceed MAX_EMI_TO_INCOME of income ──
    new_emi = _amortized_emi(amount, LOAN_INTEREST_RATE, term)
    existing_emi = sum(float(l.get('emi') or 0) for l in active_loans)
    emi_cap = MONTHLY_INCOME * MAX_EMI_TO_INCOME
    if existing_emi + new_emi > emi_cap:
        return jsonify({
            "error": f"EMI ₹{new_emi:,.0f} would push your total monthly repayment to "
                     f"₹{existing_emi + new_emi:,.0f}, above the ₹{emi_cap:,.0f} limit "
                     f"({int(MAX_EMI_TO_INCOME*100)}% of income). Borrow less or pick a longer term."
        }), 400

    # A-01: atomic apply. loan:{month} idempotency (one voluntary loan/month) is now
    # claimed inside the row-locked transaction, and cash/loans move as ADDITIVE deltas
    # so a concurrent allocate/relative/etc. cannot lose or duplicate the credit.
    try:
        apply_player_txn(
            user_id, month, action_key=f"loan:{month}",
            deltas={"cash": round(amount, 2), "loans": round(amount, 2)},
            loan_inserts=[{
                "principal": round(amount, 2), "current_amount": round(amount, 2),
                "interest_rate": LOAN_INTEREST_RATE, "month_taken": month,
                "term_months": term, "loan_type": "player",
                "emi": round(new_emi, 2), "status": "active",
            }],
        )
    except PlayerTxnError as e:
        if e.kind == 'DUPLICATE_ACTION':
            return jsonify({"error": "You have already taken a loan this month."}), 400
        if e.kind == 'PLAYER_NOT_FOUND':
            return jsonify({"error": "No player state found."}), 404
        return jsonify({"error": "Loan could not be processed. No money moved."}), 400
    except Exception as e:
        print(f"DEBUG: Loan DB error: {e}")
        return jsonify({"error": f"Database processing failed: {str(e)}"}), 500

    total_repay = new_emi * term
    return jsonify({
        "message": f"Loan of ₹{amount:,.0f} approved and credited to your cash.",
        "emi": round(new_emi, 2),
        "term_months": term,
        "interest_rate": LOAN_INTEREST_RATE,
        "total_repayment": round(total_repay, 2),
        "total_interest": round(total_repay - amount, 2)
    })


# ──────────────────────────────────────────────
# LOAN QUOTE — preview EMI before committing
# ──────────────────────────────────────────────
@player_bp.route('/loan/quote', methods=['POST'])
def loan_quote():
    user_id = get_user_id(request)
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json or {}
    try:
        amount = float(data.get('amount', 0))
        term = int(data.get('term_months', 6))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid request."}), 400

    if term not in LOAN_TERM_OPTIONS or amount <= 0:
        return jsonify({"error": "Invalid amount or term."}), 400

    emi = _amortized_emi(amount, LOAN_INTEREST_RATE, term)
    total = emi * term
    return jsonify({
        "amount": amount,
        "term_months": term,
        "interest_rate": LOAN_INTEREST_RATE,
        "emi": round(emi, 2),
        "total_repayment": round(total, 2),
        "total_interest": round(total - amount, 2)
    })


# ──────────────────────────────────────────────
# SPOUSE NEGOTIATION (ADR-014)
#
# TWO-STEP by design. /negotiate only INTERPRETS — it moves no money and writes
# no state beyond the audit row. The player must then confirm the interpretation
# via /negotiate/commit before the rules engine runs. That confirmation gate is
# an ADR-003 constraint: we never spend someone's money on an inference they
# have not seen and agreed to.
# ──────────────────────────────────────────────
def _negotiation_context(user_id, player, game):
    """Shared state for both negotiation endpoints."""
    arch = player.get('spouse_archetype')
    if not arch or arch == 'single':
        return None, "You are not married."
    if not (game or {}).get('negotiation_enabled'):
        return None, "The organizer has not opened conversations yet."

    month = int(player['month'])

    try:
        catalogue = supabase.table('spouse_proposals').select('*').execute().data or []
    except Exception:
        catalogue = []

    proposal = negsvc.generate_proposal(user_id, month, arch, catalogue)
    if not proposal:
        return None, "She has nothing to raise this month."

    try:
        rows = (supabase.table('player_negotiations')
                .select('*').eq('user_id', user_id).eq('month', month)
                .order('round').execute().data or [])
    except Exception:
        rows = []

    if any(r.get('outcome') in ('accepted_full', 'accepted_counter', 'refused',
                                'delayed', 'auto_resolved') for r in rows):
        return None, "This month's conversation is already settled."

    committed = [r for r in rows if r.get('confirmed')]
    return {
        "archetype": arch, "month": month, "proposal": proposal,
        "round": len(committed) + 1, "history": rows,
        "satisfaction": float(player.get('spouse_satisfaction', SATISFACTION_START) or SATISFACTION_START),
    }, None


@player_bp.route('/negotiate', methods=['POST'])
def negotiate_interpret():
    """STEP 1 — interpret only. No money moves here."""
    user_id = get_user_id(request)
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    # A-02: unified gate — active game + turn not locked/processing.
    player, game, gerr = require_playable(user_id)
    if gerr:
        return jsonify({"error": gerr[0]}), gerr[1]

    ctx, err = _negotiation_context(user_id, player, game)
    if err:
        return jsonify({"error": err}), 400

    text = (request.json or {}).get('message', '')
    try:
        extracted = ai_service.extract_intent(text, ctx['proposal'])
    except IntentError as e:
        # Rejected, never guessed. Hand it back for rephrasing.
        return jsonify({"error": str(e), "needs_rephrase": True}), 400

    try:
        supabase.table('player_negotiations').insert({
            "user_id": user_id, "month": ctx['month'], "round": ctx['round'],
            "raw_text": text, "intent": extracted['intent'],
            "params": extracted['params'], "confirmed": False,
            "outcome": "pending", "ai_source": extracted['ai_source'],
        }).execute()
    except Exception as e:
        print(f"DEBUG: negotiation audit insert failed: {e}")

    return jsonify({
        "intent": extracted['intent'],
        "params": extracted['params'],
        "ai_source": extracted['ai_source'],
        "confirmation": _confirmation_text(extracted, ctx['proposal']),
        "round": ctx['round'],
        "max_rounds": NEGOTIATION_MAX_ROUNDS,
    })


def _confirmation_text(extracted, proposal):
    i, p = extracted['intent'], extracted['params']
    if i == 'COUNTER_OFFER':
        return f"Offer her Rs{p['amount']:,} towards {proposal['title']}?"
    if i == 'ACCEPT_PROPOSAL':
        return f"Agree to the full Rs{proposal['ask']:,}?"
    if i == 'REQUEST_DELAY':
        return f"Ask her to postpone this by {p['months']} month(s)?"
    if i == 'PROPOSE_ALTERNATIVE':
        return f"Suggest '{p['alternative_id'].replace('_', ' ')}' instead?"
    if i == 'ASK_QUESTION':
        return f"Ask her about '{p['topic']}'? (costs nothing)"
    if i == 'REFUSE':
        return "Refuse outright? She will not take it well."
    return "Proceed?"


@player_bp.route('/negotiate/commit', methods=['POST'])
def negotiate_commit():
    """STEP 2 — the player confirmed. NOW the rules engine decides."""
    user_id = get_user_id(request)
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    # A-02: unified gate — active game + turn not locked/processing.
    player, game, gerr = require_playable(user_id)
    if gerr:
        return jsonify({"error": gerr[0]}), gerr[1]

    ctx, err = _negotiation_context(user_id, player, game)
    if err:
        return jsonify({"error": err}), 400

    body = request.json or {}
    try:
        params = validate(body.get('intent'), body.get('params') or {})
    except IntentError as e:
        return jsonify({"error": str(e)}), 400
    intent = body['intent']

    # ── D-05: enforce the confirmation gate. commit may only execute an intent
    # that /negotiate first interpreted and showed the player. We require a
    # matching pending (unconfirmed) interpretation row for this exact
    # (month, round, intent); without it we refuse — money never moves on an
    # inference the player never saw (ADR-003), and the audit chain
    # (interpretation → confirmation → commit) stays complete. If the earlier
    # interpretation write was lost, the player simply re-sends via chat, which
    # re-creates the pending row: self-healing, never a money hole.
    try:
        pending = (supabase.table('player_negotiations')
                   .select('id')
                   .eq('user_id', user_id).eq('month', ctx['month'])
                   .eq('round', ctx['round']).eq('intent', intent)
                   .eq('confirmed', False).eq('outcome', 'pending')
                   .limit(1).execute().data or [])
    except Exception:
        pending = []
    if not pending:
        return jsonify({
            "error": "Send your message to her first, then confirm what she understood.",
            "needs_rephrase": True,
        }), 400

    # ── DETERMINISTIC. No network. This is the only thing that decides money. ──
    result = negsvc.evaluate(
        intent=intent, params=params, proposal=ctx['proposal'],
        round_no=ctx['round'], satisfaction=ctx['satisfaction'],
        player_cash=float(player.get('cash', 0)),
    )

    new_sat = negsvc.clamp_satisfaction(ctx['satisfaction'] + result['satisfaction_delta'])

    # ── A-01 + D-04: apply satisfaction + any financial effects atomically under
    # the row lock, as ADDITIVE deltas, with the per-(month,round) claim inside the
    # same transaction. A double-click / two tabs / replay collide on the claim and
    # only one turn applies; a concurrent allocate/loan cannot lose the cash effect.
    deltas = {"spouse_satisfaction": result['satisfaction_delta']}
    require_cash = None
    if result['resolved']:
        for field, delta in (result['effects'] or {}).items():
            deltas[field] = deltas.get(field, 0) + delta
        cash_out = -float((result['effects'] or {}).get('cash', 0) or 0)
        if cash_out > 0:
            require_cash = cash_out

    try:
        apply_player_txn(
            user_id, ctx['month'],
            action_key=f"negotiate:{ctx['month']}:{ctx['round']}",
            require_cash=require_cash, deltas=deltas, clamp_satisfaction=True,
        )
    except PlayerTxnError as e:
        if e.kind == 'DUPLICATE_ACTION':
            return jsonify({"error": "This negotiation turn has already been submitted."}), 409
        if e.kind == 'INSUFFICIENT_CASH':
            return jsonify({"error": "You do not have the cash to honour that. Counter lower."}), 400
        if e.kind == 'PLAYER_NOT_FOUND':
            return jsonify({"error": "No player state found."}), 404
        return jsonify({"error": "Negotiation could not be processed. No money moved."}), 400
    except Exception as e:
        print(f"DEBUG: negotiation commit failed: {e}")
        return jsonify({"error": f"Database processing failed: {str(e)}"}), 500

    # Best-effort audit row (money already moved atomically above).
    try:
        supabase.table('player_negotiations').insert({
            "user_id": user_id, "month": ctx['month'], "round": ctx['round'],
            "raw_text": body.get('message'), "intent": intent, "params": params,
            "confirmed": True,
            "rule_input": {"ask": ctx['proposal']['ask'], "round": ctx['round'],
                           "satisfaction": ctx['satisfaction'],
                           "required_minimum": result['required_minimum']},
            "rule_output": {"outcome": result['outcome'],
                            "agreed_amount": result['agreed_amount'],
                            "effects": result['effects']},
            "outcome": result['outcome'], "ai_source": "rules",
        }).execute()
    except Exception as e:
        print(f"DEBUG: negotiation audit insert failed: {e}")

    try:
        dialogue = (supabase.table('spouse_dialogue').select('*')
                    .eq('archetype_id', ctx['archetype']).execute().data or [])
    except Exception:
        dialogue = []

    spouse_name = ARCHETYPES.get(ctx['archetype'], {}).get('name', 'Your spouse')
    voice = ai_service.narrate(result['outcome'], result['reason'], ctx['proposal'],
                               spouse_name, new_sat, dialogue)

    return jsonify({
        "outcome": result['outcome'],
        "resolved": result['resolved'],
        "agreed_amount": result['agreed_amount'],
        "reason": result['reason'],
        "spouse_line": voice['line'],
        "ai_source": voice['ai_source'],
        "satisfaction": new_sat,
        "satisfaction_delta": result['satisfaction_delta'],
        "round": ctx['round'],
        "max_rounds": NEGOTIATION_MAX_ROUNDS,
        "effects": result['effects'],
    })


# ──────────────────────────────────────────────
# LOCK TURN — Player confirms they're done
# ──────────────────────────────────────────────
@player_bp.route('/lock-turn', methods=['POST'])
def lock_turn():
    user_id = get_user_id(request)
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    player = get_player(user_id)
    if not player:
        return jsonify({"error": "Player state not found"}), 404

    # A-02: never lock a turn mid-processing (the batch would overwrite it anyway).
    game = get_game_state()
    if game and game.get('game_status') == 'processing':
        return jsonify({"error": "The month is being processed — try again in a moment."}), 409

    # Guard: from Month 2 onward the player must allocate their available cash
    # before the round can be locked. This is what makes the game a decision every
    # month instead of a single month-1 decision followed by 11 months of watching.
    month = int(player.get('month') or 1)
    if month >= 2 and float(player.get('cash', 0)) > 0.5 and not allocation_done(user_id, month):
        return jsonify({
            "error": f"You still have ₹{float(player['cash']):,.0f} unallocated. "
                     f"Distribute it before completing Month {month}."
        }), 400

    # Guard: in Month 6, players must choose a spouse or single before locking
    if player.get('month') == 6 and not player.get('spouse_archetype'):
        game = get_game_state()
        if game.get('marriage_round_active'):
            return jsonify({"error": "You must choose to marry or stay single before completing Month 6."}), 400

    supabase.table('player_state').update({
        'status': 'waiting'
    }).eq('user_id', user_id).execute()

    return jsonify({"message": "Turn confirmed. Waiting for next month to be processed."})


# ──────────────────────────────────────────────
# SELL ASSET
# 10% penalty, cash credited next month
# ──────────────────────────────────────────────
@player_bp.route('/sell', methods=['POST'])
def sell_asset():
    user_id = get_user_id(request)
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    # A-02: unified gate — active game + turn not locked/processing.
    player, game, gerr = require_playable(user_id)
    if gerr:
        return jsonify({"error": gerr[0]}), gerr[1]

    data = request.json
    asset_type = data.get('asset')
    amount_to_sell = float(data.get('amount', 0))

    if asset_type not in ('stocks', 'gold', 'emergency_fund'):
        return jsonify({"error": "Invalid asset type. Must be stocks, gold, or emergency_fund."}), 400

    if amount_to_sell <= 0:
        return jsonify({"error": "Amount must be positive."}), 400

    current_val = float(player.get(asset_type, 0))
    if amount_to_sell > current_val:
        return jsonify({"error": f"Insufficient {asset_type} balance. You have ₹{current_val:,.0f}"}), 400

    # Bike lock-in check
    if asset_type == 'emergency_fund' and player.get('bike_lock_in_months', 0) > 0:
        # Allow but warn
        pass

    # QA-003 fix: the balance check above is a friendly pre-check only — the
    # actual decrement + credit-row insert is done atomically in the DB via
    # sell_asset_atomic (locks the player row, re-checks the balance under
    # that lock). This closes a race where two concurrent identical sell
    # requests could both pass the stale Python-side check above and both
    # insert a player_sales row, crediting cash twice for one sale.
    try:
        result = supabase.rpc('sell_asset_atomic', {
            "p_user_id": user_id,
            "p_asset_type": asset_type,
            "p_amount": amount_to_sell,
            "p_month": player['month'],
            "p_penalty_rate": SELL_PENALTY_RATE
        }).execute()
    except Exception as e:
        return jsonify({"error": f"Sale failed: {e}"}), 400

    data = result.data or {}
    penalty = float(data.get('penalty', amount_to_sell * SELL_PENALTY_RATE))
    receive_val = float(data.get('cash_to_receive', amount_to_sell - penalty))

    return jsonify({
        "message": f"Sold ₹{amount_to_sell:,.0f} of {asset_type}. After {SELL_PENALTY_RATE*100:.0f}% penalty, ₹{receive_val:,.0f} will be credited next month.",
        "penalty": penalty,
        "credited_next_month": receive_val
    })


# ──────────────────────────────────────────────
# BUY OPTIONAL CHOICE
# ──────────────────────────────────────────────
@player_bp.route('/buy-choice', methods=['POST'])
def buy_choice():
    user_id = get_user_id(request)
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    # A-02: unified gate — active game + turn not locked/processing.
    player, game, err = require_playable(user_id)
    if err:
        return jsonify({"error": err[0]}), err[1]

    from services.choice_service import execute_choice
    result = execute_choice(player, (request.json or {}).get('choice_id'))

    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


# ──────────────────────────────────────────────
# HANDLE RELATIVE / SOCIAL EVENT
# ──────────────────────────────────────────────
@player_bp.route('/handle-relative', methods=['POST'])
def handle_relative():
    user_id = get_user_id(request)
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    # A-02: unified gate — active game + turn not locked/processing.
    player, game, err = require_playable(user_id)
    if err:
        return jsonify({"error": err[0]}), err[1]

    data = request.json or {}
    relative_type = str(data.get('relative_type', '')).strip().lower()
    action = data.get('action', 'none')

    if action not in ('none', 'medium', 'high'):
        return jsonify({"error": "Invalid action."}), 400

    # C-01: relative_type must be a KNOWN relative. The backend is authoritative —
    # without this, any invented string is a fresh idempotency key, so the
    # "one help per relative per month" cap was bypassable and trust was farmable.
    if relative_type not in VALID_RELATIVE_TYPES:
        return jsonify({"error": f"Unknown relative. Choose one of {sorted(VALID_RELATIVE_TYPES)}."}), 400

    cost = TRUST_HELP_AMOUNTS.get(action, 0)
    trust_gain = TRUST_SCORE_GAIN.get(action, 0)
    month = int(player['month'])

    # Declining is free and does NOT consume the per-relative slot.
    if action == 'none':
        return jsonify({"message": "You chose not to help. No trust gained.", "trust_change": 0})

    # Friendly pre-check; the authoritative affordability check is under the lock.
    if float(player.get('cash', 0)) < cost:
        return jsonify({"error": f"Not enough cash. Need ₹{cost:,} but have ₹{float(player.get('cash', 0)):,.0f}"}), 400

    # A-01: atomic apply. cash out + trust up as ADDITIVE deltas (so the monthly
    # event engine's trust changes are never clobbered), with the once-per-relative
    # claim (relative:{type}) inside the same row-locked transaction.
    try:
        apply_player_txn(
            user_id, month, action_key=f"relative:{relative_type}",
            require_cash=float(cost),
            deltas={"cash": -float(cost), "trust_score": float(trust_gain)},
        )
    except PlayerTxnError as e:
        if e.kind == 'DUPLICATE_ACTION':
            return jsonify({"error": "You already helped this relative this month."}), 400
        if e.kind == 'INSUFFICIENT_CASH':
            return jsonify({"error": f"Not enough cash. Need ₹{cost:,}."}), 400
        if e.kind == 'PLAYER_NOT_FOUND':
            return jsonify({"error": "Player not found"}), 404
        return jsonify({"error": "Could not process. No money moved."}), 400

    # Best-effort per-relative audit rows (trust/spend history; not a balance).
    try:
        existing = supabase.table('player_relative_score').select('*').eq('user_id', user_id).eq('relative_type', relative_type).execute()
        if existing.data:
            supabase.table('player_relative_score').update({
                'trust_score': int(existing.data[0].get('trust_score', 0)) + trust_gain,
                'total_spent': float(existing.data[0].get('total_spent', 0)) + cost
            }).eq('user_id', user_id).eq('relative_type', relative_type).execute()
        else:
            supabase.table('player_relative_score').insert({
                'user_id': user_id, 'relative_type': relative_type,
                'trust_score': trust_gain, 'total_spent': cost
            }).execute()
        supabase.table('player_relative_actions').insert({
            'user_id': user_id, 'month': month, 'relative_type': relative_type,
            'action_taken': action, 'amount_spent': cost
        }).execute()
    except Exception as e:
        print(f"DEBUG: relative audit rows failed: {e}")

    return jsonify({
        "message": f"Helped {relative_type} relative ({action}). Spent ₹{cost:,}. Trust +{trust_gain}.",
        "trust_change": trust_gain,
        "amount_spent": cost
    })


# ──────────────────────────────
# LEADERBOARD
# ──────────────────────────────
@player_bp.route('/leaderboard', methods=['GET'])
def get_leaderboard():
    from services.game_service import get_leaderboard
    data = get_leaderboard()
    return jsonify(data)


# ──────────────────────────────
# EVENT HISTORY — Get all logs for the player
# ──────────────────────────────
@player_bp.route('/event-history', methods=['GET'])
def event_history():
    user_id = get_user_id(request)
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    logs = get_all_event_logs(user_id)
    return jsonify({"logs": logs})


# ──────────────────────────────────────────────
# COURTSHIP & MARRIAGE ENDPOINTS (ADR-002)
# ──────────────────────────────────────────────

@player_bp.route('/courtship/reveal', methods=['POST'])
def courtship_reveal():
    user_id = get_user_id(request)
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    # A-02: unified gate — active game + turn not locked/processing.
    player, game, gerr = require_playable(user_id)
    if gerr:
        return jsonify({"error": gerr[0]}), gerr[1]

    if player['month'] != 6 or not game.get('marriage_round_active'):
        return jsonify({"error": "Courtship is only available when the marriage round is active in Month 6."}), 400

    data = request.json or {}
    archetype_id = data.get('archetype_id')
    trait_key = data.get('trait_key')  # 'income', 'expense_mod', 'assets'

    if archetype_id not in ARCHETYPES:
        return jsonify({"error": "Invalid spouse archetype."}), 400
    if trait_key not in ('income', 'expense_mod', 'assets'):
        return jsonify({"error": "Invalid trait key. Must be income, expense_mod, or assets."}), 400

    # Check if already revealed
    existing = supabase.table('player_spouse_reveals').select('*').eq('user_id', user_id).eq('archetype_id', archetype_id).eq('trait_key', trait_key).execute()
    if existing.data:
        return jsonify({
            "message": "Already revealed.",
            "revealed_value": _get_revealed_value(archetype_id, trait_key)
        })

    # Count existing reveals to check cost
    reveals = supabase.table('player_spouse_reveals').select('*').eq('user_id', user_id).execute().data or []
    count = len(reveals)
    cost = 0
    if count >= 3:
        cost = 5000
        cash = float(player.get('cash', 0))
        if cash < cost:
            return jsonify({"error": f"Not enough cash for an extra date. Need ₹{cost:,}."}), 400
        new_cash = cash - cost
        supabase.table('player_state').update({'cash': new_cash}).eq('user_id', user_id).execute()
        player['cash'] = new_cash

    # Insert reveal record
    supabase.table('player_spouse_reveals').insert({
        'user_id': user_id,
        'archetype_id': archetype_id,
        'trait_key': trait_key
    }).execute()

    return jsonify({
        "message": f"Successfully went on a date! Spent ₹{cost:,} cash.",
        "cost": cost,
        "revealed_value": _get_revealed_value(archetype_id, trait_key)
    })


def _get_revealed_value(archetype_id, trait_key):
    arc = ARCHETYPES[archetype_id]
    if trait_key == 'income':
        return f"+₹{arc['income']:,}/mo"
    elif trait_key == 'expense_mod':
        net_expense = SPOUSE_BASE_EXPENSE + arc['expense_mod']
        return f"₹{net_expense:+,}/mo (Base: ₹{SPOUSE_BASE_EXPENSE:,}, mod: {arc['expense_mod']:+,})"
    elif trait_key == 'assets':
        parts = []
        if arc['stocks'] > 0:
            parts.append(f"Stocks: ₹{arc['stocks']:,}")
        if arc['gold'] > 0:
            parts.append(f"Gold: ₹{arc['gold']:,}")
        if arc['ef'] > 0:
            parts.append(f"Emergency Fund: ₹{arc['ef']:,}")
        if arc['loan'] > 0:
            parts.append(f"Debt: ₹{arc['loan']:,}")
        return " | ".join(parts) if parts else "Brings no assets/liabilities."


@player_bp.route('/courtship/marry', methods=['POST'])
def courtship_marry():
    user_id = get_user_id(request)
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    # A-02: unified gate — active game + turn not locked/processing.
    player, game, gerr = require_playable(user_id)
    if gerr:
        return jsonify({"error": gerr[0]}), gerr[1]

    if player['month'] != 6 or not game.get('marriage_round_active'):
        return jsonify({"error": "Marriage round is only available when active in Month 6."}), 400

    if player.get('spouse_archetype'):
        return jsonify({"error": "You have already made a marriage decision."}), 400

    data = request.json or {}
    choice = data.get('choice')

    if choice != 'single' and choice not in ARCHETYPES:
        return jsonify({"error": "Invalid selection."}), 400

    cash = float(player.get('cash', 0))
    stocks = float(player.get('stocks', 0))
    gold = float(player.get('gold', 0))
    ef = float(player.get('emergency_fund', 0))
    loans = float(player.get('loans', 0))
    discipline_avg = float(player.get('discipline_score', 100))

    if choice == 'single':
        # A-01: the one-time 'marry' claim + the state set are one atomic txn.
        try:
            apply_player_txn(user_id, MARRIAGE_MONTH, action_key='marry',
                             sets={"spouse_archetype": "single"})
        except PlayerTxnError as e:
            if e.kind == 'DUPLICATE_ACTION':
                return jsonify({"error": "You have already made a marriage decision."}), 400
            if e.kind == 'PLAYER_NOT_FOUND':
                return jsonify({"error": "Player state not found"}), 404
            return jsonify({"error": "Could not process. No changes made."}), 400
        try:
            supabase.table('player_month_log').insert({
                "user_id": user_id, "month": 6,
                "starting_cash": cash, "ending_cash": cash,
                "net_worth": player.get('net_worth', 0),
                "summary": "💍 You chose to stay single and focus on your individual goals."
            }).execute()
        except Exception as e:
            print(f"DEBUG: single month_log insert failed: {e}")
        return jsonify({"message": "You chose to stay single.", "spouse_archetype": "single"})

    # Friendly pre-check; the authoritative wedding-cost check is under the lock.
    if cash < WEDDING_COST:
        return jsonify({"error": f"Insufficient cash for wedding. Need ₹{WEDDING_COST:,} but have ₹{cash:,.0f}."}), 400

    # ── Formulas (UNCHANGED) computed in Python; the RPC only applies them atomically ──
    arc = ARCHETYPES[choice]
    spouse_income = arc['income']
    spouse_expense = SPOUSE_BASE_EXPENSE + arc['expense_mod']
    net_spouse_flow = spouse_income - spouse_expense

    proj_cash = cash - WEDDING_COST + net_spouse_flow
    proj_stocks = stocks + arc['stocks']
    proj_gold = gold + arc['gold']
    proj_ef = ef + arc['ef']
    proj_loans = loans + arc['loan']
    net_worth = proj_cash + proj_stocks + proj_gold + proj_ef - proj_loans

    risk_level = calculate_risk_score({
        'cash': proj_cash, 'stocks': proj_stocks, 'gold': proj_gold,
        'emergency_fund': proj_ef, 'loans': proj_loans
    })

    # ── D-07: score against the real household living expense (inflation-adjusted
    # lifestyle cost, with the bike discount), matching monthly_processor's basis. ──
    lifestyle = player.get('lifestyle_type', 'city')
    living = LIFESTYLE_COSTS.get(lifestyle, LIFESTYLE_COSTS['city'])
    adjusted_living = calculate_inflation_adjustment(living['total'], MARRIAGE_MONTH)
    if player.get('bike_status'):
        adjusted_living -= living['transport'] * 0.5

    # ── D-03: fold the spouse's one-time resource injection into scoring. ──
    spouse_assets = arc['stocks'] + arc['gold'] + arc['ef'] - arc['loan']

    score_result = calculate_financial_health_score(
        net_worth=net_worth, month=6,
        emergency_fund=proj_ef, monthly_expense=adjusted_living,
        loans=proj_loans, total_assets=proj_cash + proj_stocks + proj_gold + proj_ef,
        risk_score=risk_level, discipline_avg=discipline_avg,
        spouse_income=spouse_income,
        spouse_assets=spouse_assets, wedding_cost=WEDDING_COST
    )

    loan_inserts = []
    if arc['loan'] > 0:
        loan_inserts.append({
            "principal": arc['loan'], "current_amount": arc['loan'],
            "interest_rate": 0.12, "month_taken": 6, "status": "active",
        })

    # A-01: wedding cost, spouse asset/liability injection, month-6 spouse flow, the
    # 'marry' claim and the spouse-loan insert all commit in ONE row-locked txn.
    try:
        apply_player_txn(
            user_id, MARRIAGE_MONTH, action_key='marry', require_cash=float(WEDDING_COST),
            deltas={
                "cash": round(net_spouse_flow - WEDDING_COST, 2),
                "stocks": round(arc['stocks'], 2),
                "gold": round(arc['gold'], 2),
                "emergency_fund": round(arc['ef'], 2),
                "loans": round(arc['loan'], 2),
            },
            sets={"spouse_archetype": choice, "risk_level": risk_level,
                  "financial_health_score": score_result['score']},
            recompute_networth=True, loan_inserts=loan_inserts,
        )
    except PlayerTxnError as e:
        if e.kind == 'DUPLICATE_ACTION':
            return jsonify({"error": "You have already made a marriage decision."}), 400
        if e.kind == 'INSUFFICIENT_CASH':
            return jsonify({"error": f"Insufficient cash for wedding. Need ₹{WEDDING_COST:,}."}), 400
        if e.kind == 'PLAYER_NOT_FOUND':
            return jsonify({"error": "Player state not found"}), 404
        return jsonify({"error": "Marriage could not be processed. No money moved."}), 400

    summary = (
        f"💍 Married {arc['name']}! Paid ₹{WEDDING_COST:,} wedding cost. "
        f"Spouse added assets (Stocks +₹{arc['stocks']:,}, Gold +₹{arc['gold']:,}, EF +₹{arc['ef']:,}). "
        f"Month 6 spouse flow net: {net_spouse_flow:+,}."
    )
    try:
        supabase.table('player_month_log').insert({
            "user_id": user_id, "month": 6,
            "starting_cash": player['cash'], "ending_cash": round(proj_cash, 2),
            "net_worth": round(net_worth, 2), "summary": summary
        }).execute()
    except Exception as e:
        print(f"DEBUG: marriage month_log insert failed: {e}")

    updates = {
        "spouse_archetype": choice,
        "cash": round(proj_cash, 2), "stocks": round(proj_stocks, 2),
        "gold": round(proj_gold, 2), "emergency_fund": round(proj_ef, 2),
        "loans": round(proj_loans, 2), "net_worth": round(net_worth, 2),
        "risk_level": risk_level, "financial_health_score": score_result['score']
    }
    return jsonify({
        "message": f"Successfully married {arc['name']}!",
        "spouse_archetype": choice,
        "state": updates
    })
