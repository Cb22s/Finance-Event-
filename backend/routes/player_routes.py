# =============================================================================
# PLAYER ROUTES — All player-facing API endpoints
# =============================================================================

from flask import Blueprint, request, jsonify
from supabase_client import supabase
from services.auth_service import get_user_id
from services.game_service import (
    get_game_state, get_player, get_total_loans,
    get_optional_choices, get_trust_scores, get_all_event_logs,
    get_pending_sales, fair_roll, mark_action
)
from models.constants import (
    INITIAL_BUDGET, SELL_PENALTY_RATE, TRUST_HELP_AMOUNTS, TRUST_SCORE_GAIN,
    LIFESTYLE_COSTS
)
from engine.scoring import calculate_financial_health_score
from engine.market_engine import calculate_risk_score

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

    return jsonify({
        "player": player,
        "game": game,
        "choices": choices,
        "trust_scores": trust_scores,
        "event_logs": event_logs
    })


# ──────────────────────────────────────────────
# LOCK TURN — Player confirms they're done
# ──────────────────────────────────────────────
@player_bp.route('/lock-turn', methods=['POST'])
def lock_turn():
    user_id = get_user_id(request)
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

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

    penalty = amount_to_sell * SELL_PENALTY_RATE
    receive_val = amount_to_sell - penalty

    new_val = current_val - amount_to_sell
    supabase.table('player_state').update({
        asset_type: new_val
    }).eq('user_id', user_id).execute()

    supabase.table('player_sales').insert({
        "user_id": user_id,
        "asset_type": asset_type,
        "amount_sold": amount_to_sell,
        "penalty": penalty,
        "cash_to_receive": receive_val,
        "month_sold_in": player['month'],
        "month_to_credit": player['month'] + 1
    }).execute()

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
