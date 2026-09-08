"""Deterministic strategy comparison; no database or score-weight changes."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.monthly_processor import process_month_for_player, _amortized_emi, household_expenses
from engine.scoring import score_player_snapshot, liquidity_component
from models.constants import LOAN_INTEREST_RATE
from tools.seed_content import events_data

STRATEGIES = {
    'A: High risk': (0.85, 0, 0, 0.15),
    'B: Strong emergency fund': (0.25, 0, 0.65, 0.10),
    'C: Cash heavy': (0, 0.10, 0, 0.90),
    'D: Debt and investment': (0.85, 0.05, 0, 0.10),
    'E: Balanced': (0.45, 0.20, 0.25, 0.10),
    'F: Repeated emergency borrowing': (1, 0, 0, 0),
}


def simulate(name, weights, content_stress=True):
    state = {'user_id': 'strategy-player', 'month': 1, 'cash': 100000,
             'stocks': 0, 'gold': 0, 'emergency_fund': 0, 'loans': 0,
             'lifestyle_type': 'city', 'bike_status': False, 'bike_lock_in_months': 0,
             'discipline_score': 100, 'status': 'waiting', 'insurance_plan': 'none',
             'spouse_archetype': 'single', 'spouse_satisfaction': 60,
             'household_expense_modifier': 0}
    loans, history, next_id = [], [], 1
    for month in range(1, 13):
        if month > 1:
            result = process_month_for_player(
                state, month, [e for e in events_data if e['month'] == month] if content_stress else [],
                [l for l in loans if l['status'] == 'active'], [],
                auto_events=False, auto_market=False,
                market_scenario={'stock_pct': -0.06 if month in (5, 9) else 0.04,
                                 'gold_pct': 0.015, 'source': 'admin',
                                 'name': 'Common authored path', 'reason': 'Strategy comparison'})
            state = result['updated_state']
            for update in result['loan_updates']:
                next(l for l in loans if l['id'] == update['id']).update(update)
            for loan in result['new_loans']:
                loans.append(dict(loan, id=next_id))
                next_id += 1
        if name.startswith('D:') and month == 2:
            amount, term = 120000, 12
            loans.append({'id': next_id, 'user_id': state['user_id'], 'principal': amount,
                          'current_amount': amount, 'interest_rate': LOAN_INTEREST_RATE,
                          'month_taken': month, 'term_months': term, 'loan_type': 'player',
                          'emi': round(_amortized_emi(amount, LOAN_INTEREST_RATE, term), 2),
                          'status': 'active'})
            next_id += 1
            state['cash'] += amount
            state['loans'] += amount
        available = state['cash']
        for key, weight in zip(('stocks', 'gold', 'emergency_fund'), weights[:3]):
            allocation = round(available * weight, 2)
            state[key] += allocation
            state['cash'] -= allocation
        state['cash'] = round(state['cash'], 2)
        state.update(score_player_snapshot(state))
        history.append(dict(state))
    expense = household_expenses(state, 12)['adjusted_living']
    return {'strategy': name, 'net_worth': state['net_worth'],
            'cash': state['cash'], 'emergency_fund': state['emergency_fund'],
            'liquidity_months': round(state['emergency_fund'] / expense, 3),
            'liquidity_component': round(liquidity_component(state['emergency_fund'], expense), 2),
            'debt': state['loans'], 'risk_score': state['risk_level'],
            'discipline': state['discipline_score'], 'financial_health_score': state['financial_health_score'],
            'auto_loans': sum(l.get('loan_type') == 'auto' for l in loans), 'history': history}


def run(content_stress=True):
    results = sorted((simulate(name, weights, content_stress) for name, weights in STRATEGIES.items()),
                     key=lambda x: (-x['financial_health_score'], -x['net_worth']))
    for rank, result in enumerate(results, 1):
        result['rank'] = rank
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    results = {'baseline': run(False), 'content_stress': run(True)}
    if args.output:
        args.output.write_text(json.dumps(results, indent=2), encoding='utf-8')
    print(json.dumps({scenario: [{k: v for k, v in r.items() if k != 'history'} for r in rows]
                      for scenario, rows in results.items()}, indent=2))
