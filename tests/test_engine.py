import unittest

from agent_town import buildings, engine, work
from agent_town.core import FactionState, Good, JobRef, Pawn
from agent_town import pawns


def _wood_ready_state() -> FactionState:
    """A civilization with the coin and goods to build the first chain link (Forester)."""
    state = FactionState(day=0, time_of_day=7, coin=10)
    state.stockpile.add(Good.PLANKS, 4)
    state.stockpile.add(Good.STONE, 2)
    return state


def _farm_civilization() -> FactionState:
    """A minimal deterministic civilization: one farmer, one Farm, some bread on hand."""
    state = FactionState(day=0, time_of_day=7, tax_rate=0.2)
    state.stockpile.add(Good.BREAD, 16)
    state.pawns["farmer"] = Pawn(
        id="farmer",
        name="Farmer",
        skills={"farming": 18},
        traits=("industrious", "optimist", "tough"),
        needs={need: 1.0 for need in pawns.BUILD1_NEEDS},
        mood=80.0,
        schedule="default",
    )
    farm = buildings.make_building("Farm", 0, 0, building_id="farm1")
    state.buildings[farm.id] = farm
    return state


class EngineConstructionTests(unittest.TestCase):
    def test_fallback_placement_is_realized_and_completes(self):
        state = _wood_ready_state()

        results = engine.run(state, hours=6)

        # The first missing build-1 chain link is placed, built, and the site
        # is consumed once its goods and work are satisfied.
        self.assertIn("Forester", {b.kind for b in state.buildings.values()})
        self.assertEqual(state.construction_sites, {})
        self.assertTrue(any(r.buildings_completed for r in results))
        # Build goods were hauled out of the stockpile to the site.
        self.assertEqual(state.stockpile.counts.get(Good.PLANKS, 0), 0)
        self.assertEqual(state.stockpile.counts.get(Good.STONE, 0), 0)

    def test_unaffordable_placement_is_skipped_not_ghosted(self):
        # No goods, no coin: the proposed placement must not become a site that
        # can never complete.
        state = FactionState(day=0, time_of_day=7, coin=0)

        engine.run(state, hours=3)

        self.assertEqual(state.construction_sites, {})
        self.assertEqual(state.buildings, {})


class EngineArbiterTests(unittest.TestCase):
    def test_step_hour_seats_pawns_through_the_arbiter(self):
        # No governor assign_pawn: the arbiter staffs the farmer into the Farm and
        # leaves a decision trace the viewer can read.
        state = _farm_civilization()

        engine.step_hour(state)

        self.assertEqual(state.pawns["farmer"].assignment, JobRef("farm1", "farming"))
        self.assertEqual(state.buildings["farm1"].staffed_by, ["farmer"])
        self.assertEqual(state.work_decisions["farmer"].lane, work.LANE_NORMAL_WORK)

    def test_priority_change_reroutes_a_pawn(self):
        state = _farm_civilization()
        bakery = buildings.make_building("Bakery", 4, 0, building_id="bake1")
        state.buildings[bakery.id] = bakery

        engine.step_hour(state)
        self.assertEqual(state.pawns["farmer"].assignment.building_id, "farm1")

        # The player/governor disables farming and prioritises baking; the pawn
        # releases the Farm and re-routes to the Bakery on the next replan.
        work.set_priority(state.pawns["farmer"], "farming", 0)
        work.set_priority(state.pawns["farmer"], "baking", 1)
        engine.step_hour(state)

        self.assertEqual(state.pawns["farmer"].assignment.building_id, "bake1")
        self.assertEqual(state.buildings["farm1"].staffed_by, [])


class EngineDeterminismTests(unittest.TestCase):
    def test_same_setup_same_outcome(self):
        first = _farm_civilization()
        second = _farm_civilization()

        engine.run_days(first, days=2)
        engine.run_days(second, days=2)

        self.assertEqual(first.coin, second.coin)
        self.assertEqual(first.day, second.day)
        self.assertEqual(first.stockpile.counts, second.stockpile.counts)
        self.assertEqual(
            {pid: round(p.mood, 6) for pid, p in first.pawns.items()},
            {pid: round(p.mood, 6) for pid, p in second.pawns.items()},
        )

    def test_run_days_advances_whole_days(self):
        state = _farm_civilization()

        results = engine.run_days(state, days=2)

        self.assertEqual(len(results), 48)
        self.assertEqual(state.day, 2)
        self.assertEqual(sum(r.days_rolled for r in results), 2)


if __name__ == "__main__":
    unittest.main()
