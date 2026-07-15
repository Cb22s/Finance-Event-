# =============================================================================
# ADMIN ROUTES — Game control, month processing, event/choice management
# Uses the modular engine for all game logic.
# =============================================================================

import re
from flask import Blueprint, request, jsonify
from supabase_client import supabase
from services.auth_service import admin_required
from services.game_service import (
    get_game_state, get_all_players, get_active_loans, get_player,
    get_admin_events_for_month, get_pending_sales, validate_rpc_payload
)
from engine.monthly_processor import process_month_for_player
from engine.market_engine import calculate_risk_score
from engine.scoring import calculate_financial_health_score
from models.constants import TOTAL_MONTHS, LIFESTYLE_COSTS

admin_bp = Blueprint('admin', __name__)


# ──────────────────────────────────────────────
# START / RESTART GAME
# ──────────────────────────────────────────────
@admin_bp.route('/start-game', methods=['POST'])
@admin_required
def start_game():
    """Reset all game data and start fresh."""
    try:
        supabase.table('game_control').update({
            'current_month': 1,
            'game_status': 'active'
        }).eq('id', 1).execute()

        # Wipe all player data
        dummy = '00000000-0000-0000-0000-000000000000'
        supabase.table('player_state').delete().neq('user_id', dummy).execute()
        supabase.table('player_loans').delete().neq('user_id', dummy).execute()
        supabase.table('player_sales').delete().neq('user_id', dummy).execute()
        supabase.table('player_relative_score').delete().neq('user_id', dummy).execute()
        supabase.table('player_relative_actions').delete().neq('user_id', dummy).execute()
        supabase.table('player_month_log').delete().neq('user_id', dummy).execute()
        supabase.table('player_month_actions').delete().neq('user_id', dummy).execute()

        # Wipe events and choices
        supabase.table('events').delete().neq('id', 0).execute()
        supabase.table('optional_choices').delete().neq('id', 0).execute()

        return jsonify({"message": "Game restarted. All data wiped!"})
    except Exception as e:
        return jsonify({"error": f"Failed to start game: {e}"}), 500


# ──────────────────────────────────────────────
# NEXT MONTH — Core monthly processing using engine
# ──────────────────────────────────────────────
@admin_bp.route('/next-month', methods=['POST'])
@admin_required
def next_month():
    """
    Process next month for ALL players using the modular engine.
    This is the backbone of the game loop.
    """
    req = request.json or {}
    exp_month = req.get('expected_month')
    game = get_game_state()

    if not game:
        return jsonify({"error": "Game control not found."}), 500

    curr_m = game['current_month']

    # Race condition protection
    if exp_month is not None and int(exp_month) != curr_m:
        return jsonify({
            "error": f"Race condition blocked. System is on month {curr_m}."
        }), 409

    if game['game_status'] != 'active':
        return jsonify({"error": "Cannot advance — game is not active."}), 400

    next_m = curr_m + 1

    # End game after 12 months
    if curr_m >= TOTAL_MONTHS:
        supabase.table('game_control').update({
            'game_status': 'ended'
        }).eq('id', 1).execute()
        return jsonify({
            "message": f"Month {TOTAL_MONTHS} completed. Game officially ended!"
        })

    # Fetch all data
    players = get_all_players()
    if not players:
        return jsonify({"error": "No players found to process."}), 400

    admin_events = get_admin_events_for_month(next_m)

    # Accumulate batch operations
    updates_state = []
    updates_loans = []
    inserts_loans = []
    inserts_logs = []
    all_event_summaries = []

    for player in players:
        uid = player['user_id']

        # Fetch player-specific data — engine handles everything else
        active_loans = get_active_loans(uid)
        pending_sales = get_pending_sales(uid, next_m)

        # ── RUN THE ENGINE — route passes data, engine decides what to do ──
        result = process_month_for_player(
            player=player,
            month=next_m,
            admin_events=admin_events,
            active_loans=active_loans,
            pending_sales=pending_sales
        )

        # Collect batch data
        updates_state.append(result['updated_state'])

        for lu in result['loan_updates']:
            # Ensure all required fields for loan updates
            matching_loan = next((l for l in active_loans if l['id'] == lu['id']), {})
            updates_loans.append({
                "id": lu['id'],
                "user_id": uid,
                "principal": float(matching_loan.get('principal', 0)),
                "current_amount": lu['current_amount'],
                "interest_rate": float(matching_loan.get('interest_rate', 0.12)),
                "month_taken": int(matching_loan.get('month_taken', next_m)),
                "status": lu['status']
            })

        inserts_loans.extend(result['new_loans'])

        # Build log entry
        summary = " | ".join(result['event_log'])
        inserts_logs.append({
            "user_id": uid,
            "month": next_m,
            "starting_cash": result['starting_cash'],
            "ending_cash": result['ending_cash'],
            "net_worth": result['net_worth'],
            "summary": summary
        })

        # Collect event summaries for response
        for ev in result.get('events_triggered', []):
            all_event_summaries.append({
                "player": uid[:8],
                "event": ev['name'],
                "category": ev.get('category', 'unknown'),
                "value": ev['value']
            })

    # Validate the batch payload
    err = validate_rpc_payload(updates_state, updates_loans, inserts_loans, inserts_logs)
    if err:
        return jsonify({"error": f"Validation failed: {err}"}), 500

    # Execute atomically via RPC
    payload = {
        "p_updates_player_state": updates_state,
        "p_updates_loans": updates_loans,
        "p_inserts_loans": inserts_loans,
        "p_inserts_logs": inserts_logs,
        "p_next_month": next_m
    }

    try:
        supabase.rpc('process_month_atomically', payload).execute()
        return jsonify({
            "message": f"Success! Advanced to Month {next_m}.",
            "month": next_m,
            "players_processed": len(players),
            "events_triggered": len(all_event_summaries),
            "event_details": all_event_summaries[:20]  # Limit for response size
        })
    except Exception as e:
        return jsonify({"error": f"Database processing failed: {e}"}), 500


# ──────────────────────────────────────────────
# END GAME MANUALLY
# ──────────────────────────────────────────────
@admin_bp.route('/end-game', methods=['POST'])
@admin_required
def end_game():
    supabase.table('game_control').update({
        'game_status': 'ended'
    }).eq('id', 1).execute()
    return jsonify({"message": "Game has been ended manually."})


# ──────────────────────────────────────────────
# EVENT MANAGEMENT
# ──────────────────────────────────────────────
# QA-005: event_engine.apply_event_to_state only understands these
# type/target combinations — anything else silently no-ops (the engine
# just doesn't match a branch), so an admin typo previously vanished with
# no error. Validating here surfaces the mistake immediately instead.
_EVENT_TYPES = {'fixed', 'percentage'}
_EVENT_TARGETS = {'cash', 'stocks', 'gold', 'expense_increase'}
_PERCENTAGE_TARGETS = {'cash', 'stocks', 'gold'}  # expense_increase is fixed-only in the engine


@admin_bp.route('/event', methods=['POST'])
@admin_required
def add_event():
    data = request.json
    if not data:
        return jsonify({"error": "No data provided."}), 400

    try:
        month = int(data.get('month'))
    except (TypeError, ValueError):
        return jsonify({"error": "month is required and must be an integer."}), 400

    event_type = data.get('event_type')
    if event_type not in _EVENT_TYPES:
        return jsonify({"error": f"event_type must be one of {sorted(_EVENT_TYPES)}."}), 400

    impact_target = data.get('impact_target')
    if impact_target not in _EVENT_TARGETS:
        return jsonify({"error": f"impact_target must be one of {sorted(_EVENT_TARGETS)}."}), 400
    if event_type == 'percentage' and impact_target not in _PERCENTAGE_TARGETS:
        return jsonify({"error": "expense_increase is only valid for event_type 'fixed'."}), 400

    try:
        value = float(data.get('value'))
    except (TypeError, ValueError):
        return jsonify({"error": "value is required and must be a number."}), 400

    record = {
        "month": month,
        "event_name": data.get('event_name', 'Admin Event'),
        "event_type": event_type,
        "impact_target": impact_target,
        "value": value,
        "description": data.get('description', '')
    }
    supabase.table('events').insert(record).execute()
    return jsonify({"message": "Global event added successfully."})


@admin_bp.route('/event/<int:id>', methods=['DELETE'])
@admin_required
def del_event(id):
    supabase.table('events').delete().eq('id', id).execute()
    return jsonify({"message": "Event deleted."})


# ──────────────────────────────────────────────
# OPTIONAL CHOICE MANAGEMENT
# ──────────────────────────────────────────────
# QA-005: this is a financial mutation path — choice_service.execute_choice
# deducts `cost` and grants `reward_value` against these rows every time a
# player buys the choice. An unvalidated negative cost would pay players to
# "buy" it; an out-of-range probability would break fair_roll's semantics.
_REWARD_TYPES = {'cash', 'stocks', 'gold', 'emergency_fund'}


@admin_bp.route('/choice-admin', methods=['POST'])
@admin_required
def add_choice():
    data = request.json
    if not data:
        return jsonify({"error": "No data provided."}), 400

    try:
        month = int(data.get('month'))
    except (TypeError, ValueError):
        return jsonify({"error": "month is required and must be an integer."}), 400

    try:
        cost = float(data.get('cost'))
    except (TypeError, ValueError):
        return jsonify({"error": "cost is required and must be a number."}), 400
    if cost < 0:
        return jsonify({"error": "cost cannot be negative."}), 400

    reward_type = data.get('reward_type')
    if reward_type not in _REWARD_TYPES:
        return jsonify({"error": f"reward_type must be one of {sorted(_REWARD_TYPES)}."}), 400

    try:
        reward_value = float(data.get('reward_value'))
    except (TypeError, ValueError):
        return jsonify({"error": "reward_value is required and must be a number."}), 400
    if reward_value < 0:
        return jsonify({"error": "reward_value cannot be negative."}), 400

    try:
        probability = int(data.get('probability'))
    except (TypeError, ValueError):
        return jsonify({"error": "probability is required and must be an integer 0-100."}), 400
    if not (0 <= probability <= 100):
        return jsonify({"error": "probability must be between 0 and 100."}), 400

    record = {
        "month": month,
        "name": data.get('name', 'Optional Choice'),
        "cost": cost,
        "risk_type": data.get('risk_type', ''),
        "reward_type": reward_type,
        "reward_value": reward_value,
        "probability": probability
    }
    supabase.table('optional_choices').insert(record).execute()
    return jsonify({"message": "Optional choice added for players."})


# ──────────────────────────────────────────────
# ADMIN DASHBOARD DATA
# ──────────────────────────────────────────────
@admin_bp.route('/admin/me', methods=['GET'])
@admin_required
def admin_me():
    """Lightweight check the admin login page uses to confirm admin rights."""
    return jsonify({"ok": True})


@admin_bp.route('/admin/players', methods=['GET'])
@admin_required
def admin_players():
    """All players with their name/email, ranked by Financial Health Score (ADR-008)."""
    res = (supabase.table('player_state')
           .select('*, users(name, email)')
           .order('financial_health_score', desc=True)
           .order('net_worth', desc=True)
           .execute())
    game = get_game_state()
    return jsonify({"players": res.data or [], "game": game})


# ──────────────────────────────────────────────
# PLAYER DETAIL — manual edit (admin correction) + reset
# Every edit is written to player_month_log for audit.
# ──────────────────────────────────────────────
_EDITABLE = ['cash', 'stocks', 'gold', 'emergency_fund', 'loans', 'status']
_NUMERIC = ['cash', 'stocks', 'gold', 'emergency_fund', 'loans']


@admin_bp.route('/admin/update-player', methods=['POST'])
@admin_required
def update_player():
    data = request.json or {}
    uid = data.get('user_id')
    if not uid:
        return jsonify({"error": "user_id is required."}), 400

    current = get_player(uid)
    if not current:
        return jsonify({"error": "Player not found."}), 404

    fields = {}
    for k in _EDITABLE:
        if k in data and data[k] is not None and data[k] != '':
            fields[k] = data[k]
    try:
        for k in _NUMERIC:
            if k in fields:
                fields[k] = float(fields[k])
    except (ValueError, TypeError):
        return jsonify({"error": "Financial values must be numbers."}), 400

    if not fields:
        return jsonify({"error": "Nothing to update."}), 400

    # Net worth is always recomputed from components — never trust a typed value.
    merged = {**current, **fields}
    net_worth = (float(merged['cash']) + float(merged['stocks']) + float(merged['gold'])
                 + float(merged['emergency_fund']) - float(merged['loans']))
    fields['net_worth'] = net_worth

    # QA-004 fix: net worth was already recomputed above, but the leaderboard
    # actually ranks by financial_health_score (ADR-008), and risk_level feeds
    # its risk_protection component. Both were previously left stale after a
    # correction, so a fixed data-entry mistake could still show a wrong rank
    # until the next month reprocessed it. Recompute both the same way
    # allocate_month1 does — discipline_score is left untouched (a correction
    # fixes financial figures, not the player's discipline history).
    risk_state = {
        "cash": float(merged['cash']), "stocks": float(merged['stocks']),
        "gold": float(merged['gold']), "emergency_fund": float(merged['emergency_fund']),
        "loans": float(merged['loans'])
    }
    risk_level = calculate_risk_score(risk_state)
    month = int(merged.get('month', 1) or 1)
    lifestyle = merged.get('lifestyle_type') or 'city'
    monthly_expense = LIFESTYLE_COSTS.get(lifestyle, LIFESTYLE_COSTS['city'])['total']
    discipline_avg = float(merged.get('discipline_score', 100) or 100)
    total_assets = (risk_state['cash'] + risk_state['stocks']
                     + risk_state['gold'] + risk_state['emergency_fund'])
    score_result = calculate_financial_health_score(
        net_worth=net_worth, month=month,
        emergency_fund=risk_state['emergency_fund'], monthly_expense=monthly_expense,
        loans=risk_state['loans'], total_assets=total_assets,
        risk_score=risk_level, discipline_avg=discipline_avg
    )
    fields['risk_level'] = risk_level
    fields['financial_health_score'] = score_result['score']

    try:
        supabase.table('player_state').update(fields).eq('user_id', uid).execute()
        # Audit trail — records the correction without touching prior month logs.
        supabase.table('player_month_log').insert({
            "user_id": uid,
            "month": int(merged.get('month', 1)),
            "starting_cash": float(current.get('cash', 0)),
            "ending_cash": float(merged['cash']),
            "net_worth": net_worth,
            "summary": "🛠️ Admin manual adjustment"
        }).execute()
    except Exception as e:
        return jsonify({"error": f"Update failed: {e}"}), 500

    return jsonify({
        "message": "Player updated.",
        "net_worth": net_worth,
        "risk_level": risk_level,
        "financial_health_score": score_result['score']
    })


# --------------------------------------------------
# PLAYER ROSTER - every provisioned login, and whether they have started.
# public.users has a row per created account (via the signup trigger). A
# player only gets a player_state row once they do their month-1 allocation,
# so "played" distinguishes started vs. waiting. Admins (public.admins) excluded.
# --------------------------------------------------
@admin_bp.route('/admin/roster', methods=['GET'])
@admin_required
def admin_roster():
    users = supabase.table('users').select('id, name, email').execute().data or []
    admin_rows = supabase.table('admins').select('user_id').execute().data or []
    played_rows = supabase.table('player_state').select('user_id').execute().data or []
    admin_ids = {r['user_id'] for r in admin_rows}
    played_ids = {r['user_id'] for r in played_rows}
    roster = []
    for u in users:
        if u['id'] in admin_ids:
            continue
        email = u.get('email') or ''
        username = email.split('@')[0] if '@' in email else email
        roster.append({
            'user_id': u['id'],
            'username': username,
            'name': u.get('name') or username,
            'played': u['id'] in played_ids,
        })
    roster.sort(key=lambda r: r['username'])
    return jsonify({'roster': roster})


# --------------------------------------------------
# CREATE PLAYER - admin provisions a login (username + password).
# Uses the service_role admin API to create the auth user; the
# on_auth_user_created trigger then creates the public.users profile row.
# Players log in with just a username; the real email is username@event.local.
# --------------------------------------------------
PLAYER_EMAIL_DOMAIN = 'event.local'
_USERNAME_RE = re.compile(r'^[a-z0-9_.-]{3,32}$')


@admin_bp.route('/admin/create-player', methods=['POST'])
@admin_required
def create_player():
    data = request.json or {}
    username = str(data.get('username', '')).strip().lower()
    password = str(data.get('password', ''))
    name = str(data.get('name', '')).strip() or username

    if not _USERNAME_RE.match(username):
        return jsonify({"error": "Username must be 3-32 chars: letters, numbers, . _ - only."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400

    email = f"{username}@{PLAYER_EMAIL_DOMAIN}"
    try:
        supabase.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {"name": name},
        })
    except Exception as e:
        msg = str(e)
        if 'already' in msg.lower() or 'registered' in msg.lower() or 'exists' in msg.lower():
            return jsonify({"error": f"Username '{username}' already exists."}), 409
        return jsonify({"error": f"Could not create player: {msg}"}), 500

    return jsonify({"message": f"Player '{username}' created. They can log in now.", "username": username})


@admin_bp.route('/admin/reset-player', methods=['POST'])
@admin_required
def reset_player():
    data = request.json or {}
    uid = data.get('user_id')
    if not uid:
        return jsonify({"error": "user_id is required."}), 400
    try:
        for table in ['player_state', 'player_loans', 'player_sales',
                      'player_relative_score', 'player_relative_actions',
                      'player_month_log', 'player_month_actions']:
            supabase.table(table).delete().eq('user_id', uid).execute()
    except Exception as e:
        return jsonify({"error": f"Reset failed: {e}"}), 500
    return jsonify({"message": "Player reset — they can allocate again."})
