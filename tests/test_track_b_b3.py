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

# A roll that always fires (0.0 < any break chance) and one that never does.
SURE_ROLL = 0.0
SAFE_ROLL = 0.999


def comfortable(**kw):
    base = dict(needs={NEED_REST: 0.5, NEED_FOOD: 0.5, NEED_RECREATION: 0.5})
    base.update(kw)
    return Pawn(**base)


class TraitWantMoodTests(unittest.TestCase):
    def test_optimist_floors_higher_than_pessimist(self):
        opt = comfortable(id="o", name="O", traits=("optimist",))
        pes = comfortable(id="x", name="X", traits=("pessimist",))
        self.assertGreater(mood.mood_target(opt), mood.mood_target(pes))

    def test_met_want_lifts_mood_over_ignored(self):
        pawn = comfortable(id="p", name="P", wants=("wants_outdoor_work",))
        met = mood.mood_target(pawn, met_wants=frozenset({"wants_outdoor_work"}))
        ignored = mood.mood_target(pawn)
        self.assertGreater(met, ignored)


class BreakMachineTests(unittest.TestCase):
    def test_minor_band_pawn_slacks_on_a_sure_roll(self):
        pawn = Pawn(id="p", name="P", mood=30.0)  # minor band (20 <= mood < 35)
        pawns.advance_break_state(pawn, SURE_ROLL)
        self.assertEqual(pawn.state, pawns.STATE_SLACKING)

    def test_major_band_pawn_wanders_on_a_sure_roll(self):
        pawn = Pawn(id="p", name="P", mood=10.0)  # major band (mood < 20)
        pawns.advance_break_state(pawn, SURE_ROLL)
        self.assertEqual(pawn.state, pawns.STATE_WANDERING)

    def test_safe_roll_leaves_a_low_pawn_idle(self):
        pawn = Pawn(id="p", name="P", mood=30.0)
        pawns.advance_break_state(pawn, SAFE_ROLL)
        self.assertEqual(pawn.state, pawns.STATE_IDLE)

    def test_content_pawn_never_breaks(self):
        pawn = Pawn(id="p", name="P", mood=70.0)
        pawns.advance_break_state(pawn, SURE_ROLL)
        self.assertEqual(pawn.state, pawns.STATE_IDLE)

    def test_recovered_pawn_returns_to_idle_with_catharsis(self):
        pawn = Pawn(id="p", name="P", state=pawns.STATE_SLACKING, mood=80.0)
        pawns.advance_break_state(pawn, 0.5)
        self.assertEqual(pawn.state, pawns.STATE_IDLE)
        self.assertTrue(any(t.kind == "catharsis" for t in pawn.thoughts))

    def test_tough_trait_resists_breaking(self):
        # tough lowers the bands by 6, so mood 30 is no longer in the minor band.
        tough = Pawn(id="t", name="T", mood=30.0, traits=("tough",))
        normal = Pawn(id="n", name="N", mood=30.0)
        pawns.advance_break_state(tough, SURE_ROLL)
        pawns.advance_break_state(normal, SURE_ROLL)
        self.assertEqual(tough.state, pawns.STATE_IDLE)
        self.assertEqual(normal.state, pawns.STATE_SLACKING)


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
        pawn = Pawn(id="p", name="P", mood=10.0)
        pawns.advance_break_state(pawn, SURE_ROLL)
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
