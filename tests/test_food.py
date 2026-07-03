"""Slice 0: make the starvation trap escapable and give the governor food-sight.

Covers the four moving parts:
- continuous production (fractional work carry-over) so a slowed/starving pawn
  still finishes cycles instead of contributing nothing every sub-cycle hour;
- the hunger productivity *floor* (food == 0 no longer means zero work);
- ``food_days_of_cover`` and the ``low_food`` governor exception (food-sight);
- the fallback no longer resting a hungry colony into a work stoppage.

Plus two integration proofs of the vision's boundary: the default civ that used
to spiral to a frozen death now sustains under the fallback, while a civ with no
way to bake bread still starves (a real fail state stays reachable for later).
"""

import unittest

from agent_town import buildings, economy, engine, governor, mood, pawns, world
from agent_town.civilization import create_default_civilization
from agent_town.civilization_view import exception_stack_items, governor_card_summary
from agent_town.core import FactionState, Good, NEED_FOOD, NEED_WATER, Pawn


def _fed_pawn(pid: str = "p") -> Pawn:
    return Pawn(id=pid, name=pid, needs={need: 1.0 for need in pawns.BUILD1_NEEDS})


class ProductionCarryoverTests(unittest.TestCase):
    def test_sub_cycle_work_banks_then_produces(self):
        # A malnourished pawn contributes only the hunger floor per hour - well
        # under one whole cycle. The old int(rate // work_units) flooring dropped
        # that to zero forever; carry-over banks it and completes a cycle in time.
        state = FactionState(time_of_day=8)  # a WORK hour
        forester = buildings.make_building("Forester", 0, 0, building_id="f1")
        state.buildings["f1"] = forester
        pawn = Pawn(
            id="p",
            name="p",
            skills={"forestry": 10},
            needs={n: 1.0 for n in pawns.BUILD1_NEEDS} | {NEED_FOOD: 0.0},
        )
        state.pawns["p"] = pawn
        forester.staffed_by.append("p")
        state.resource_nodes.append(world.ResourceNode(Good.LOGS, 500, 1, 1))

        # One hour alone produces nothing, but the work is banked (not lost).
        economy.production_tick(state)
        self.assertEqual(state.stockpile.counts.get(Good.LOGS, 0), 0)
        self.assertGreater(forester.production_progress, 0.0)
        self.assertLess(forester.production_progress, forester.recipe.work_units)

        # Over enough hours the banked fractions complete real cycles.
        for _ in range(20):
            economy.production_tick(state)
        self.assertGreaterEqual(state.stockpile.counts.get(Good.LOGS, 0), 1)

    def test_progress_never_exceeds_one_cycle(self):
        # Banked progress only ever holds a fractional cycle, so a blocked
        # building never accumulates a burst it fires on resume.
        state = FactionState(time_of_day=8)
        forester = buildings.make_building("Forester", 0, 0, building_id="f1")
        state.buildings["f1"] = forester
        pawn = _fed_pawn()
        pawn.skills["forestry"] = 20
        state.pawns["p"] = pawn
        forester.staffed_by.append("p")

        for _ in range(30):
            economy.production_tick(state)
            self.assertLess(forester.production_progress, forester.recipe.work_units)


class HungerFloorTests(unittest.TestCase):
    def test_starving_pawn_keeps_a_work_floor(self):
        self.assertEqual(mood.hunger_productivity_factor(_starving()), mood.HUNGER_STARVING_FLOOR)
        self.assertGreater(mood.HUNGER_STARVING_FLOOR, 0.0)
        self.assertLess(mood.HUNGER_STARVING_FLOOR, 0.25)  # below the ravenous band


def _starving() -> Pawn:
    return Pawn(id="p", name="p", needs={n: 1.0 for n in pawns.BUILD1_NEEDS} | {NEED_FOOD: 0.0})


class FoodCoverTests(unittest.TestCase):
    def test_food_days_of_cover_uses_population_demand(self):
        state = FactionState()
        state.pawns["a"] = _fed_pawn("a")
        state.pawns["b"] = _fed_pawn("b")
        two_days = int(round(2 * 2 * economy.BREAD_UNITS_PER_PAWN_DAY))
        state.stockpile.add(Good.BREAD, two_days)

        self.assertAlmostEqual(
            economy.food_days_of_cover(state),
            two_days / (2 * economy.BREAD_UNITS_PER_PAWN_DAY),
        )

    def test_empty_civ_has_infinite_cover(self):
        self.assertEqual(economy.food_days_of_cover(FactionState()), float("inf"))


class FoodSightTests(unittest.TestCase):
    def test_faction_summary_reports_food_cover(self):
        state = FactionState()
        state.pawns["a"] = _fed_pawn("a")
        summary = governor.build_faction_summary(state)
        self.assertIn("food_days_of_cover", summary)

    def test_low_food_fires_when_hungry_and_out_of_bread(self):
        state = FactionState()
        for pid in ("a", "b"):
            pawn = _fed_pawn(pid)
            pawn.needs[NEED_FOOD] = 0.1  # actually hungry
            state.pawns[pid] = pawn
        state.stockpile.add(Good.BREAD, 1)  # and no buffer to fix it

        kinds = [exc.kind for exc in governor.build_exception_queue(state)]
        self.assertIn("low_food", kinds)

    def test_well_stocked_civ_has_no_low_food(self):
        state = FactionState()
        state.pawns["a"] = _fed_pawn("a")
        state.stockpile.add(Good.BREAD, 200)

        kinds = [exc.kind for exc in governor.build_exception_queue(state)]
        self.assertNotIn("low_food", kinds)


class FoodVisibleToWatcherTests(unittest.TestCase):
    """The watcher must see a food crisis as a food crisis.

    Regression guard: `low_food` shipped firing correctly in the data but buried
    below `low_water`/`skill_mismatch` in the viewer, so a starving civ read as a
    water problem on screen. Food is the survival staple; it must outrank water.
    """

    def _starving_and_dry(self) -> FactionState:
        state = FactionState()
        for pid in ("a", "b"):
            pawn = _fed_pawn(pid)
            pawn.needs[NEED_FOOD] = 0.05  # starving -> low_food
            state.pawns[pid] = pawn
        state.stockpile.counts[Good.WATER] = 0  # also dry -> low_water
        return state

    def test_low_food_outranks_low_water_in_the_stack(self):
        kinds = [item.kind for item in exception_stack_items(self._starving_and_dry())]
        self.assertIn("low_food", kinds)
        self.assertIn("low_water", kinds)
        self.assertLess(kinds.index("low_food"), kinds.index("low_water"))

    def test_low_food_is_critical(self):
        items = exception_stack_items(self._starving_and_dry())
        self.assertEqual(items[0].kind, "low_food")
        self.assertEqual(items[0].severity, "critical")

    def test_governor_card_names_food_as_the_bottleneck(self):
        summary = governor_card_summary(self._starving_and_dry())
        self.assertEqual(summary.top_exception.kind, "low_food")
        self.assertIn("food", summary.plan.lower())
        self.assertIn("food", summary.bottleneck.lower())

    def test_healthy_default_civ_shows_no_low_food(self):
        state = create_default_civilization()
        engine.run_days(state, governor.FallbackGovernor(), days=3)
        self.assertNotIn("low_food", [item.kind for item in exception_stack_items(state)])


class VisionBoundaryTests(unittest.TestCase):
    def test_default_civ_now_sustains_under_fallback(self):
        # The default civ used to drain its bread buffer and freeze into a
        # zero-production death spiral by ~day 9. With continuous production it
        # sustains: bread stays on hand and pawns stay fed and healthy.
        state = create_default_civilization()
        engine.run_days(state, governor.FallbackGovernor(), days=20)

        self.assertGreater(state.stockpile.counts.get(Good.BREAD, 0), 0)
        min_food = min(p.needs.get(NEED_FOOD, 1.0) for p in state.pawns.values())
        self.assertGreater(min_food, 0.25)
        self.assertGreater(economy.average_mood(state), 55.0)

    def test_bakery_less_civ_still_starves(self):
        # A fail state must stay reachable: with no bakery and no governor
        # response, no bread can ever be made, so the reserve empties and pawns
        # go hungry (later slices turn this into an actual death + documented
        # run-end). The governor here is deliberately inert - under the real
        # FallbackGovernor the dig-out now rebuilds a Bakery and the civ
        # recovers (test_dig_out pins that), which is exactly the crisis line's
        # "escapable with good governance, fatal without".
        class InertGovernor:
            def decide(self, context):
                return []

        state = create_default_civilization()
        for bid in [b.id for b in state.buildings.values() if b.kind == "Bakery"]:
            del state.buildings[bid]
        engine.run_days(state, InertGovernor(), days=10)

        self.assertEqual(state.stockpile.counts.get(Good.BREAD, 0), 0)
        avg_food = economy.average_need(state, NEED_FOOD)
        self.assertLess(avg_food, 0.2)


if __name__ == "__main__":
    unittest.main()
