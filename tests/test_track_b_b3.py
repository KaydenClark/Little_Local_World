import unittest

from agent_town import governor, mood, pawns
from agent_town.core import (
    Building,
    FactionState,
    Good,
    NEED_FOOD,
    NEED_RECREATION,
    NEED_REST,
    Pawn,
    Recipe,
)


def starved(**kw):
    base = dict(
        id="p",
        name="P",
        needs={NEED_REST: 0.0, NEED_FOOD: 0.0, NEED_RECREATION: 0.0},
    )
    base.update(kw)
    return Pawn(**base)


def comfortable(**kw):
    base = dict(needs={NEED_REST: 0.5, NEED_FOOD: 0.5, NEED_RECREATION: 0.5})
    base.update(kw)
    return Pawn(**base)


class TraitWantMoodTests(unittest.TestCase):
    def test_optimist_floors_higher_than_pessimist(self):
        opt = comfortable(id="o", name="O", traits=("optimist",))
        pes = comfortable(id="x", name="X", traits=("pessimist",))
        self.assertGreater(mood.compute_mood(opt), mood.compute_mood(pes))

    def test_met_want_lifts_mood_over_ignored(self):
        pawn = comfortable(id="p", name="P", wants=("wants_outdoor_work",))
        met = mood.compute_mood(pawn, met_wants=frozenset({"wants_outdoor_work"}))
        ignored = mood.compute_mood(pawn)
        self.assertGreater(met, ignored)


class BreakMachineTests(unittest.TestCase):
    def test_starved_pawn_slacks(self):
        pawn = starved()
        pawn.mood = mood.compute_mood(pawn)
        pawns.update_break_state(pawn)
        self.assertEqual(pawn.state, pawns.STATE_SLACKING)

    def test_deeply_unhappy_pawn_wanders(self):
        pawn = starved(traits=("pessimist", "frail"))
        pawn.mood = mood.compute_mood(pawn)
        pawns.update_break_state(pawn)
        self.assertEqual(pawn.state, pawns.STATE_WANDERING)

    def test_recovered_pawn_returns_to_idle(self):
        pawn = starved(state=pawns.STATE_SLACKING, mood=0.8)
        pawns.update_break_state(pawn)
        self.assertEqual(pawn.state, pawns.STATE_IDLE)


class ExceptionQueueTests(unittest.TestCase):
    def test_breaking_pawn_and_unstaffed_building_surface(self):
        state = FactionState()
        state.buildings["saw1"] = Building(
            id="saw1",
            kind="Sawmill",
            x=0,
            y=0,
            recipe=Recipe({Good.LOGS: 1}, {Good.PLANKS: 1}, 4.0, "woodcutting"),
            job_slots=2,
        )
        pawn = starved()
        pawn.mood = mood.compute_mood(pawn)
        pawns.update_break_state(pawn)
        state.pawns["p"] = pawn

        kinds = {exc.kind for exc in governor.build_exception_queue(state)}
        self.assertIn("unstaffed_building", kinds)
        self.assertIn("pawn_break", kinds)

    def test_missing_inputs_flagged_for_staffed_building(self):
        state = FactionState()
        state.buildings["saw1"] = Building(
            id="saw1",
            kind="Sawmill",
            x=0,
            y=0,
            recipe=Recipe({Good.LOGS: 2}, {Good.PLANKS: 1}, 4.0, "woodcutting"),
            job_slots=1,
            staffed_by=["p"],
        )
        kinds = {exc.kind for exc in governor.build_exception_queue(state)}
        self.assertIn("missing_inputs", kinds)


if __name__ == "__main__":
    unittest.main()
