import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from models.constants import LIFESTYLE_COSTS, WEDDING_COST, INITIAL_BUDGET

ROOT = Path(__file__).resolve().parents[2]


class FrontendContracts(unittest.TestCase):
    def test_backend_values_drive_expenses_wedding_and_reveals(self):
        fixture = {'courtship': {'wedding_cost': WEDDING_COST,
                   'reveals': [{'archetype_id': 'saver', 'trait_key': 'income',
                                'revealed_value': 'Authoritative reveal'}]},
                   'economy': {'lifestyles': LIFESTYLE_COSTS, 'initial_budget': INITIAL_BUDGET}}
        result = subprocess.run(['node', str(ROOT / 'backend/tests/frontend_contracts.mjs')],
                                input=json.dumps(fixture), text=True, encoding='utf-8',
                                capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
