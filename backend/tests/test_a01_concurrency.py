# =============================================================================
# A-01 CONCURRENCY PROOF — player_apply_atomic serialises cross-action cash writes
# =============================================================================
# This spins up a REAL local Postgres (via the `pgserver` pip package), loads the
# ACTUAL a01_atomic_player_txn_migration.sql, and hammers one player row with many
# concurrent threads doing loan(+A) and allocate(-B). If the row lock did not
# serialise, lost updates would make the final balances wrong. It also proves the
# in-transaction idempotency claim: N threads with the SAME action_key => exactly
# one applies.
#
# It is SKIPPED automatically if `pgserver`/`psycopg` are not installed, so the
# normal unit suite still runs everywhere. To run it:
#     pip install pgserver "psycopg[binary]"
#     python -m unittest tests.test_a01_concurrency -v
#
# NOTE: this validates the DB function's serialisation directly. It does not spin
# up Flask; the routes call this exact function, so the guarantee carries through.

import json
import os
import threading
import unittest

try:
    import pgserver
    import psycopg
    _HAVE_PG = True
except Exception:
    _HAVE_PG = False

MIGRATION = os.path.join(os.path.dirname(__file__), "..", "..",
                         "a01_atomic_player_txn_migration.sql")

_SCHEMA = """
CREATE ROLE anon; CREATE ROLE authenticated; CREATE ROLE service_role;
CREATE TABLE player_state (
  user_id uuid PRIMARY KEY, month int default 1,
  cash numeric default 0, stocks numeric default 0, gold numeric default 0,
  emergency_fund numeric default 0, loans numeric default 0, net_worth numeric default 0,
  trust_score numeric default 0, spouse_satisfaction int default 60,
  household_expense_modifier numeric default 0, risk_level int default 50,
  financial_health_score numeric default 0, status text default 'active',
  spouse_archetype text, insurance_plan text default 'none'
);
CREATE TABLE player_loans (
  id serial PRIMARY KEY, user_id uuid, principal numeric, current_amount numeric,
  interest_rate numeric, month_taken int, term_months int, loan_type text, emi numeric, status text
);
CREATE TABLE player_month_actions (
  user_id uuid, month int, action_key text, PRIMARY KEY (user_id, month, action_key)
);
"""
_UID = '11111111-1111-1111-1111-111111111111'


@unittest.skipUnless(_HAVE_PG, "pgserver/psycopg not installed")
class TestA01Concurrency(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import tempfile
        cls._dir = tempfile.mkdtemp()
        cls.srv = pgserver.get_server(cls._dir)
        cls.uri = cls.srv.get_uri()
        with psycopg.connect(cls.uri, autocommit=True) as c:
            c.execute(_SCHEMA)
            c.execute(open(MIGRATION, encoding="utf-8").read())

    @classmethod
    def tearDownClass(cls):
        try:
            cls.srv.cleanup()
        except Exception:
            pass

    def _reset(self, cash):
        with psycopg.connect(self.uri, autocommit=True) as c:
            c.execute("DELETE FROM player_month_actions; DELETE FROM player_loans; DELETE FROM player_state;")
            c.execute("INSERT INTO player_state(user_id,cash,net_worth) VALUES (%s,%s,%s)", (_UID, cash, cash))

    def _call(self, deltas=None, action_key=None, require_cash=None):
        with psycopg.connect(self.uri, autocommit=True) as c:
            c.execute(
                "SELECT public.player_apply_atomic(%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s,%s,%s::jsonb,%s::jsonb)",
                (_UID, 1, action_key, require_cash, json.dumps(deltas or {}), json.dumps({}),
                 False, False, json.dumps([]), json.dumps([])),
            )

    def _cash_loans_stocks(self):
        with psycopg.connect(self.uri, autocommit=True) as c:
            return c.execute("SELECT cash,loans,stocks FROM player_state WHERE user_id=%s", (_UID,)).fetchone()

    def test_no_lost_update_under_concurrency(self):
        A, B, M, N = 5000, 3000, 40, 40
        self._reset(1_000_000)
        errors = []

        def loan(i):
            try: self._call({"cash": A, "loans": A}, action_key=f"loan:{i}")
            except Exception as e: errors.append(str(e))

        def alloc(i):
            try: self._call({"cash": -B, "stocks": B}, action_key=f"alloc:{i}", require_cash=B)
            except Exception as e: errors.append(str(e))

        ts = [threading.Thread(target=loan, args=(i,)) for i in range(M)] + \
             [threading.Thread(target=alloc, args=(i,)) for i in range(N)]
        for t in ts: t.start()
        for t in ts: t.join()

        cash, loans, stocks = self._cash_loans_stocks()
        self.assertEqual(errors, [])
        self.assertEqual(float(cash), 1_000_000 + M * A - N * B)   # no lost update
        self.assertEqual(float(loans), M * A)
        self.assertEqual(float(stocks), N * B)

    def test_same_action_key_applies_once(self):
        self._reset(1_000_000)
        K = 25
        oks, dups, other = [], [], []

        def worker(i):
            try:
                self._call({"cash": -1000}, action_key="samekey", require_cash=1000); oks.append(i)
            except Exception as e:
                (dups if 'DUPLICATE_ACTION' in str(e) else other).append(i)

        ts = [threading.Thread(target=worker, args=(i,)) for i in range(K)]
        for t in ts: t.start()
        for t in ts: t.join()

        cash, _, _ = self._cash_loans_stocks()
        self.assertEqual(other, [])
        self.assertEqual(len(oks), 1)
        self.assertEqual(len(dups), K - 1)
        self.assertEqual(float(cash), 999000)


if __name__ == "__main__":
    unittest.main()
