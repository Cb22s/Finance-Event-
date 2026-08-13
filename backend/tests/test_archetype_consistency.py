# =============================================================================
# D-01 GUARD — single source of truth for spouse archetypes
# =============================================================================
# The engine reads models.constants.ARCHETYPES. The DB table public.spouse_archetypes
# and its seed in marriage_migration.sql are MIRRORS. If the seed drifts, re-running
# the migration (ON CONFLICT DO UPDATE) silently overwrites the tuned live values
# with wrong ones — the exact D-01 failure. This test fails loudly on any drift so
# nobody can reintroduce a stale seed.

import os
import re
import unittest

from models.constants import ARCHETYPES

MIGRATION = os.path.join(os.path.dirname(__file__), "..", "..", "marriage_migration.sql")

# One INSERT tuple: ('id', 'Name', income, expense_mod, stocks, gold, ef, loan, 'desc...')
_ROW = re.compile(
    r"\(\s*'(?P<id>\w+)'\s*,\s*'[^']*'\s*,\s*"
    r"(?P<income>-?\d+)\s*,\s*(?P<expense_mod>-?\d+)\s*,\s*"
    r"(?P<stocks>-?\d+)\s*,\s*(?P<gold>-?\d+)\s*,\s*"
    r"(?P<ef>-?\d+)\s*,\s*(?P<loan>-?\d+)\s*,",
)

_FIELDS = ("income", "expense_mod", "stocks", "gold", "ef", "loan")


class TestArchetypeSourceConsistency(unittest.TestCase):
    def _parse_seed(self):
        with open(MIGRATION, encoding="utf-8") as f:
            text = f.read()
        # Only look at the INSERT ... VALUES block for spouse_archetypes.
        start = text.index("INSERT INTO public.spouse_archetypes")
        end = text.index("ON CONFLICT", start)
        block = text[start:end]
        return {m.group("id"): m for m in _ROW.finditer(block)}

    def test_migration_seed_matches_constants(self):
        seed = self._parse_seed()
        self.assertEqual(
            set(seed), set(ARCHETYPES),
            "marriage_migration.sql seeds a different set of archetype ids than constants.ARCHETYPES",
        )
        for arch_id, arc in ARCHETYPES.items():
            row = seed[arch_id]
            for field in _FIELDS:
                self.assertEqual(
                    int(row.group(field)), int(arc[field]),
                    f"marriage_migration.sql '{arch_id}.{field}' = {row.group(field)} "
                    f"but constants.ARCHETYPES has {arc[field]} (D-01 drift — re-running the "
                    f"migration would corrupt the live tuned values).",
                )


if __name__ == "__main__":
    unittest.main()
