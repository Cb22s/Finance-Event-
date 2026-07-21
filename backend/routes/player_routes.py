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
    action_done
)
from models.constants import (
    INITIAL_BUDGET, SELL_PENALTY_RATE, TRUST_HELP_AMOUNTS, TRUST_SCORE_GAIN,
    LIFESTYLE_COSTS, ARCHETYPES, WEDDING_COST, SPOUSE_BASE_EXPENSE, MARRIAGE_MONTH,
    MONTHLY_INCOME, LOAN_INTEREST_RATE, LOAN_TERM_OPTIONS, LOAN_MIN_AMOUNT,
    MAX_TOTAL_DEBT_MULTIPLE, MAX_EMI_TO_INCOME
)
from engine.monthly_processor import _amortized_emi
from engine.scoring import calculate_financial_health_score
from engine.market_engine import calculate_risk_score, resolve_market_scenario

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
        "allocation": allocation
    })


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

    game = get_game_state()
    if not game or game['game_status'] != 'active':
        return jsonify({"error": "Game is not currently active."}), 400

    player = get_player(user_id)
    if not player:
        return jsonify({"error": "No player state found. Complete Month 1 first."}), 404

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
        keep_cash = float(data.get('keep_cash', 0))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid numerical data."}), 400

    buckets = [to_stocks, to_gold, to_ef, to_prepay, keep_cash]
    if any(v < 0 for v in buckets):
        return jsonify({"error": "Allocation values cannot be negative."}), 400

    total = sum(buckets)
    if abs(total - available) > 0.5:
        return jsonify({
            "error": f"Must allocate exactly your available cash of "
                     f"₹{available:,.0f}. Current total: ₹{total:,.0f}"
        }), 400

    # ── Loan prepayment: cannot prepay more than is outstanding ──
    active_loans = get_active_loans(user_id)
    outstanding = sum(float(l['current_amount']) for l in active_loans)
    if to_prepay > outstanding + 0.5:
        return jsonify({
            "error": f"Prepayment ₹{to_prepay:,.0f} exceeds outstanding debt of ₹{outstanding:,.0f}."
        }), 400

    # ── Claim the month atomically BEFORE mutating balances. If two requests race,
    #    the loser gets a unique-violation and no money is moved twice. ──
    if not mark_action(user_id, month, allocation_key(month)):
        return jsonify({"error": f"You have already allocated for Month {month}."}), 400

    # Apply prepayment oldest-loan-first
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

    new_cash = keep_cash
    new_stocks = float(player.get('stocks', 0)) + to_stocks
    new_gold = float(player.get('gold', 0)) + to_gold
    new_ef = float(player.get('emergency_fund', 0)) + to_ef
    new_outstanding = round(outstanding - to_prepay, 2)

    try:
        for lw in loan_writes:
            supabase.table('player_loans').update({
                "current_amount": lw['current_amount'],
                "status": lw['status']
            }).eq('id', lw['id']).execute()

        supabase.table('player_state').update({
            "cash": round(new_cash, 2),
            "stocks": round(new_stocks, 2),
            "gold": round(new_gold, 2),
            "emergency_fund": round(new_ef, 2),
            "loans": max(0, new_outstanding)
        }).eq('user_id', user_id).execute()

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
        print(f"DEBUG: Monthly allocation DB error: {e}")
        return jsonify({"error": f"Database processing failed: {str(e)}"}), 500

    return jsonify({
        "message": f"Month {month} allocation confirmed.",
        "allocated": {
            "stocks": to_stocks, "gold": to_gold, "emergency_fund": to_ef,
            "loan_prepay": to_prepay, "kept_as_cash": keep_cash
        }
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

    game = get_game_state()
    if not game or game['game_status'] != 'active':
        return jsonify({"error": "Game is not currently active."}), 400

    player = get_player(user_id)
    if not player:
        return jsonify({"error": "No player state found."}), 404

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

    # Atomic claim — one voluntary loan per month, and no double-credit on retry.
    if not mark_action(user_id, month, f"loan:{month}"):
        return jsonify({"error": "You have already taken a loan this month."}), 400

    try:
        supabase.table('player_loans').insert({
            "user_id": user_id,
            "principal": round(amount, 2),
            "current_amount": round(amount, 2),
            "interest_rate": LOAN_INTEREST_RATE,
            "month_taken": month,
            "term_months": term,
            "loan_type": "player",
            "emi": round(new_emi, 2),
            "status": "active"
        }).execute()

        supabase.table('player_state').update({
            "cash": round(float(player.get('cash', 0)) + amount, 2),
            "loans": round(outstanding + amount, 2)
        }).eq('user_id', user_id).execute()
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

    data = request.json
    asset_type = data.get('asset')
    amount_to_sell = float(data.get('amount', 0))

    if asset_type not in ('stocks', 'gold', 'emergency_fund'):
        return jsonify({"error": "Invalid asset type. Must be stocks, gold, or emergency_fund."}), 400

    if amount_to_sell <= 0:
        return jsonify({"error": "Amount must be positive."}), 400

    player = get_player(user_id)
    if not player:
        return jsonify({"error": "Player state not found"}), 404

    if player.get('status') == 'waiting':
        return jsonify({"error": "Your turn is locked. Wait for next month."}), 400

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

    player = get_player(user_id)
    if not player:
        return jsonify({"error": "Player not found"}), 404

    if player.get('status') == 'waiting':
        return jsonify({"error": "Your turn is locked. Wait for next month."}), 400

    from services.choice_service import execute_choice
    result = execute_choice(player, request.json.get('choice_id'))

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

    data = request.json
    relative_type = data.get('relative_type')
    action = data.get('action', 'none')

    if action not in ('none', 'medium', 'high'):
        return jsonify({"error": "Invalid action."}), 400

    player = get_player(user_id)
    if not player:
        return jsonify({"error": "Player not found"}), 404

    if player.get('status') == 'waiting':
        return jsonify({"error": "Your turn is locked."}), 400

    cost = TRUST_HELP_AMOUNTS.get(action, 0)
    trust_gain = TRUST_SCORE_GAIN.get(action, 0)

    cash = float(player['cash'])
    month = player['month']

    # A committing action (spending on a relative) can be done ONCE per relative
    # per month. Declining ('none') is free and doesn't consume the slot, so a
    # player can still change their mind. Without this, trust was farmable by
    # calling this endpoint repeatedly in the same month.
    if action != 'none':
        if cash < cost:
            return jsonify({"error": f"Not enough cash. Need ₹{cost:,} but have ₹{cash:,.0f}"}), 400
        # Atomic claim — PRIMARY KEY makes a duplicate insert fail.
        if not mark_action(user_id, month, f"relative:{relative_type}"):
            return jsonify({"error": "You already helped this relative this month."}), 400

    # Apply cash cost + trust gain as a DELTA to the single source of truth
    # (player_state.trust_score). Previously this endpoint OVERWROTE trust_score
    # with the sum of relative rows, which wiped the trust the monthly event
    # engine adds/removes. Both systems now add deltas to the same field.
    if action != 'none':
        cash -= cost
        current_trust = float(player.get('trust_score', 0) or 0)
        supabase.table('player_state').update({
            'cash': cash,
            'trust_score': current_trust + trust_gain
        }).eq('user_id', user_id).execute()

    # Keep the per-relative rows for audit / total_spent (no longer used to
    # reset player_state.trust_score).
    existing = supabase.table('player_relative_score').select('*').eq('user_id', user_id).eq('relative_type', relative_type).execute()
    if existing.data:
        current_rel_trust = int(existing.data[0].get('trust_score', 0))
        current_spent = float(existing.data[0].get('total_spent', 0))
        supabase.table('player_relative_score').update({
            'trust_score': current_rel_trust + trust_gain,
            'total_spent': current_spent + cost
        }).eq('user_id', user_id).eq('relative_type', relative_type).execute()
    else:
        supabase.table('player_relative_score').insert({
            'user_id': user_id,
            'relative_type': relative_type,
            'trust_score': trust_gain,
            'total_spent': cost
        }).execute()

    # Log the action
    supabase.table('player_relative_actions').insert({
        'user_id': user_id,
        'month': month,
        'relative_type': relative_type,
        'action_taken': action,
        'amount_spent': cost
    }).execute()

    if action == 'none':
        return jsonify({"message": f"You chose not to help. No trust gained.", "trust_change": 0})
    else:
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

    player = get_player(user_id)
    if not player:
        return jsonify({"error": "Player state not found"}), 404

    if player.get('status') == 'waiting':
        return jsonify({"error": "Your turn is locked. Wait for next month."}), 400

    game = get_game_state()
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

    player = get_player(user_id)
    if not player:
        return jsonify({"error": "Player state not found"}), 404

    if player.get('status') == 'waiting':
        return jsonify({"error": "Your turn is locked. Wait for next month."}), 400

    game = get_game_state()
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

    summary = ""
    if choice == 'single':
        summary = "💍 You chose to stay single and focus on your individual goals."
        supabase.table('player_state').update({
            'spouse_archetype': 'single'
        }).eq('user_id', user_id).execute()
        
        supabase.table('player_month_log').insert({
            "user_id": user_id,
            "month": 6,
            "starting_cash": cash,
            "ending_cash": cash,
            "net_worth": player.get('net_worth', 0),
            "summary": summary
        }).execute()
        
        return jsonify({"message": "You chose to stay single.", "spouse_archetype": "single"})

    # Wedding cost deduction
    if cash < WEDDING_COST:
        return jsonify({"error": f"Insufficient cash for wedding. Need ₹{WEDDING_COST:,} but have ₹{cash:,.0f}."}), 400

    arc = ARCHETYPES[choice]
    cash -= WEDDING_COST
    stocks += arc['stocks']
    gold += arc['gold']
    ef += arc['ef']
    
    # Handle spouse loan if any
    if arc['loan'] > 0:
        supabase.table('player_loans').insert({
            'user_id': user_id,
            'principal': arc['loan'],
            'current_amount': arc['loan'],
            'interest_rate': 0.12,
            'month_taken': 6,
            'status': 'active'
        }).execute()
        # Fetch updated total loans
        loans = get_total_loans(user_id)

    # Immediately apply Month 6 spouse income/expense
    spouse_income = arc['income']
    spouse_expense = SPOUSE_BASE_EXPENSE + arc['expense_mod']
    net_spouse_flow = spouse_income - spouse_expense
    cash += net_spouse_flow

    # Recalculate net worth
    net_worth = cash + stocks + gold + ef - loans

    # Recalculate risk level
    temp_state = {
        'cash': cash, 'stocks': stocks, 'gold': gold,
        'emergency_fund': ef, 'loans': loans
    }
    risk_level = calculate_risk_score(temp_state)

    # Recalculate score
    score_result = calculate_financial_health_score(
        net_worth=net_worth, month=6,
        emergency_fund=ef, monthly_expense=spouse_expense,
        loans=loans, total_assets=cash + stocks + gold + ef,
        risk_score=risk_level, discipline_avg=discipline_avg,
        spouse_income=spouse_income
    )

    summary = (
        f"💍 Married {arc['name']}! Paid ₹{WEDDING_COST:,} wedding cost. "
        f"Spouse added assets (Stocks +₹{arc['stocks']:,}, Gold +₹{arc['gold']:,}, EF +₹{arc['ef']:,}). "
        f"Month 6 spouse flow net: {net_spouse_flow:+,}."
    )

    updates = {
        "spouse_archetype": choice,
        "cash": round(cash, 2),
        "stocks": round(stocks, 2),
        "gold": round(gold, 2),
        "emergency_fund": round(ef, 2),
        "loans": round(loans, 2),
        "net_worth": round(net_worth, 2),
        "risk_level": risk_level,
        "financial_health_score": score_result['score']
    }

    supabase.table('player_state').update(updates).eq('user_id', user_id).execute()

    supabase.table('player_month_log').insert({
        "user_id": user_id,
        "month": 6,
        "starting_cash": player['cash'],
        "ending_cash": round(cash, 2),
        "net_worth": round(net_worth, 2),
        "summary": summary
    }).execute()

    return jsonify({
        "message": f"Successfully married {arc['name']}!",
        "spouse_archetype": choice,
        "state": updates
    })
