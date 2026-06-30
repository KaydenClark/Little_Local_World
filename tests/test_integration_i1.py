import unittest

from agent_town import buildings, economy, engine, pawns
from agent_town.core import FactionState, Good, Pawn


SEEDED_BUILDINGS = (
    ("Farm", "farming"),
    ("Farm", "farming"),
    ("Farm", "farming"),
    ("Farm", "farming"),
    ("Farm", "farming"),
    ("Farm", "farming"),
    ("Mill", "milling"),
    ("Mill", "milling"),
    ("Mill", "milling"),
    ("Bakery", "baking"),
    ("Bakery", "baking"),
    ("Bakery", "baking"),
    ("Water Well", "water"),
)


def make_state() -> FactionState:
    state = FactionState(day=0, time_of_day=7, tax_rate=0.2)
    state.stockpile.add(Good.BREAD, 24)
    state.stockpile.add(Good.WATER, 24)
    for index, (_kind, specialty) in enumerate(SEEDED_BUILDINGS):
        pawn = Pawn(
            id=f"pawn{index:02d}",
            name=f"Pawn {index}",
            skills={specialty: 20},
            traits=("industrious", "optimist", "tough"),
            needs={need: 1.0 for need in pawns.BUILD1_NEEDS},
            mood=80.0,
            schedule="default",
        )
        state.pawns[pawn.id] = pawn

    counts: dict[str, int] = {}
    for index, (kind, _skill) in enumerate(SEEDED_BUILDINGS):
        counts[kind] = counts.get(kind, 0) + 1
        building = buildings.make_building(kind, index, 0, building_id=f"{kind.lower().replace(' ', '')}{counts[kind]}")
        state.buildings[building.id] = building
    return state


class IntegrationI1Tests(unittest.TestCase):
    def test_fallback_governor_sustains_seeded_civilization_for_three_days(self):
        # The survival proof now runs through the reusable engine stepper rather
        # than a test-local loop; the seeded food-only civilization exercises the same
        # assign/needs/mood/production/tax path.
        state = make_state()

        engine.run_days(state, days=3)

        self.assertGreaterEqual(economy.average_mood(state), 45)
        self.assertGreaterEqual(state.stockpile.counts.get(Good.BREAD, 0), 1)
        self.assertGreater(state.coin, 0)
        self.assertFalse([pawn for pawn in state.pawns.values() if pawn.state == pawns.STATE_WANDERING])


if __name__ == "__main__":
    unittest.main()
