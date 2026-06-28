import unittest

from agent_town import buildings, economy, governor, mood, pawns, schedule
from agent_town.core import FactionState, Good, NEED_FOOD, Pawn, SCHEDULE_ANY


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
)


def make_state() -> FactionState:
    state = FactionState(day=0, time_of_day=7, tax_rate=0.2)
    state.stockpile.add(Good.BREAD, 6)
    for index, (_kind, specialty) in enumerate(SEEDED_BUILDINGS):
        pawn = Pawn(
            id=f"pawn{index:02d}",
            name=f"Pawn {index}",
            skills={specialty: 20},
            traits=("industrious", "optimist", "tough"),
            needs={need: 1.0 for need in pawns.BUILD1_NEEDS},
            mood=1.0,
            schedule="default",
        )
        state.pawns[pawn.id] = pawn

    counts: dict[str, int] = {}
    for index, (kind, _skill) in enumerate(SEEDED_BUILDINGS):
        counts[kind] = counts.get(kind, 0) + 1
        building = buildings.make_building(kind, index, 0, building_id=f"{kind.lower()}{counts[kind]}")
        state.buildings[building.id] = building
    return state


def step_hour(state: FactionState) -> None:
    actions = governor.FallbackGovernor().decide(governor.build_context(state))
    governor.apply_actions(state, actions)

    for pawn in state.pawns.values():
        block = schedule.block_for(pawn.schedule, state.time_of_day)
        pawns.decay_needs(pawn, 1.0)
        pawns.apply_schedule_block(pawn, block, 1.0)
        if block == SCHEDULE_ANY and pawn.needs[NEED_FOOD] < 0.65 and state.stockpile.counts.get(Good.BREAD, 0) > 0:
            state.stockpile.remove(Good.BREAD, 1)
            pawns.restore_need(pawn, NEED_FOOD, 1.0)
        pawn.mood = mood.compute_mood(pawn)
        pawns.update_break_state(pawn)

    economy.production_tick(state)
    if schedule.advance_clock(state, 1):
        economy.apply_daily_tax(state)


class IntegrationI1Tests(unittest.TestCase):
    def test_fallback_governor_sustains_seeded_colony_for_three_days(self):
        state = make_state()

        for _ in range(24 * 3):
            step_hour(state)

        self.assertGreaterEqual(economy.average_mood(state), 0.45)
        self.assertGreaterEqual(state.stockpile.counts.get(Good.BREAD, 0), 1)
        self.assertGreater(state.coin, 0)
        self.assertFalse([pawn for pawn in state.pawns.values() if pawn.state == pawns.STATE_WANDERING])


if __name__ == "__main__":
    unittest.main()
