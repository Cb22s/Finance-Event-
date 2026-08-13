# =============================================================================
# CHOICE SERVICE — Handles player optional choice purchases
# Routes call this. No business logic lives in the route.
# =============================================================================

from supabase_client import supabase
from services.game_service import (
    fair_roll, already_bought, apply_player_txn, PlayerTxnError
)


def execute_choice(player: dict, choice_id: int) -> dict:
    """
    Execute an optional choice purchase for a player.

    Handles: cash deduction, fair roll, reward distribution, validation.
    The cash/asset movement + the once-per-month claim are applied atomically by
    player_apply_atomic (A-01), so a concurrent loan/allocate cannot lose or
    duplicate the effect, and the same choice can never be bought twice.

    Returns: {success, message} or {error}.
    """
    user_id = player['user_id']
    current_m = player['month']
    cash = float(player['cash'])

    # Idempotency guard (fast, friendly path; the authoritative claim is in the RPC).
    if already_bought(user_id, current_m, choice_id):
        return {"error": "You already made this choice this month!"}

    res = supabase.table('optional_choices').select('*').eq('id', choice_id).execute()
    if not res.data:
        return {"error": "Choice not found"}

    choice = res.data[0]
    cost = float(choice['cost'])

    if cash < cost:
        return {"error": f"Not enough cash! You need ₹{cost:,.0f} but have ₹{cash:,.0f}"}

    # Probabilistic outcome — seeded per player+month+choice (deterministic, so a
    # concurrent duplicate computes the SAME result before it is rejected).
    did_win = fair_roll(user_id, current_m, choice_id, choice['probability'])

    deltas = {"cash": -cost}
    reward_type = choice['reward_type']
    reward_val = float(choice['reward_value'])
    if did_win:
        if reward_type == 'cash':
            deltas['cash'] = -cost + reward_val
        elif reward_type in ('stocks', 'gold', 'emergency_fund'):
            deltas[reward_type] = deltas.get(reward_type, 0) + reward_val
        message = f"SUCCESS! {choice['name']} paid off. Gained ₹{reward_val:,.0f} in {reward_type}."
    else:
        message = f"{choice['name']} didn't work out. Lost ₹{cost:,.0f}."

    # A-01: claim (choice:{id}) + balance move in one row-locked transaction.
    try:
        apply_player_txn(user_id, current_m, action_key=f"choice:{choice_id}",
                         require_cash=cost, deltas=deltas)
    except PlayerTxnError as e:
        if e.kind == 'DUPLICATE_ACTION':
            return {"error": "You already made this choice this month!"}
        if e.kind == 'INSUFFICIENT_CASH':
            return {"error": f"Not enough cash! You need ₹{cost:,.0f}."}
        if e.kind == 'PLAYER_NOT_FOUND':
            return {"error": "Player not found"}
        return {"error": "Could not process the choice. No money moved."}

    return {"success": did_win, "message": message}
