"""Slice 1: the dig-out - the governor grows more food during a shortage.

Covers the mechanism (`food_expansion_action` picks the right stage, one at a
time, bounded), the trigger robustness (fires only on hungry AND no-buffer, never
on a healthy civ's overnight saturation dip), and the behavioral proof (a marginal
civ slides into low_food, the fallback plants farms, and it recovers) plus the
regression guard that a healthy civ never over-builds.
"""

import unittest

from agent_town import economy, engine, governor
from agent_town.civilization import create_default_civilization
from agent_town.core import FactionState, Good, NEED_FOOD, Pawn


def _pawn(pid: str, food: float = 1.0) -> Pawn:
    from agent_town import pawns as pawns_mod

    return Pawn(id=pid, name=pid, needs={n: 1.0 for n in pawns_mod.BUILD1_NEEDS} | {NEED_FOOD: food})


def _chain(farms: int, mills: int, bakeries: int) -> list[dict]:
    rows = [{"kind": "Farm"}] * farms + [{"kind": "Mill"}] * mills + [{"kind": "Bakery"}] * bakeries
    return [dict(r) for r in rows]


class FoodExpansionActionTests(unittest.TestCase):
    def test_grows_wheat_first_when_farms_are_the_shortfall(self):
        action = governor.food_expansion_action(_chain(2, 2, 2), [])
        self.assertIsNotNone(action)
        self.assertEqual(action.building_kind, "Farm")

    def test_adds_a_mill_when_farms_are_enough_but_mills_short(self):
        action = governor.food_expansion_action(_chain(8, 2, 2), [])
        self.assertEqual(action.building_kind, "Mill")

    def test_builds_a_bakery_when_there_is_none(self):
        action = governor.food_expansion_action(_chain(4, 2, 0), [])
        self.assertEqual(action.building_kind, "Bakery")

    def test_stops_at_the_balanced_ratio_no_over_build(self):
        self.assertIsNone(governor.food_expansion_action(_chain(8, 4, 2), []))

    def test_one_building_at_a_time(self):
        pending = [{"building_kind": "Farm"}]
        self.assertIsNone(governor.food_expansion_action(_chain(2, 2, 2), pending))


class LowFoodTriggerTests(unittest.TestCase):
    """The conjunction: hungry AND no buffer. Neither alone fires."""

    def _civ(self, food: float, bread: int) -> FactionState:
        state = FactionState()
        state.pawns["a"] = _pawn("a", food=food)
        state.pawns["b"] = _pawn("b", food=food)
        if bread:
            state.stockpile.add(Good.BREAD, bread)
        return state

    def test_hungry_with_a_full_buffer_does_not_fire(self):
        # A healthy civ craters in saturation overnight (synced pawns cannot eat
        # asleep) but has bread on hand - that must not read as a crisis.
        kinds = [e.kind for e in governor.build_exception_queue(self._civ(food=0.05, bread=500))]
        self.assertNotIn("low_food", kinds)

    def test_empty_buffer_but_well_fed_does_not_fire(self):
        kinds = [e.kind for e in governor.build_exception_queue(self._civ(food=1.0, bread=0))]
        self.assertNotIn("low_food", kinds)

    def test_hungry_and_empty_fires(self):
        kinds = [e.kind for e in governor.build_exception_queue(self._civ(food=0.1, bread=0))]
        self.assertIn("low_food", kinds)


class FallbackDigOutTests(unittest.TestCase):
    def _marginal(self, keep_farms: int = 2, bread: int = 28) -> FactionState:
        state = create_default_civilization()
        farms = [b.id for b in state.buildings.values() if b.kind == "Farm"]
        for bid in farms[keep_farms:]:
            del state.buildings[bid]
        state.stockpile.counts[Good.BREAD] = bread
        return state

    def _farm_count(self, state: FactionState) -> int:
        built = sum(1 for b in state.buildings.values() if b.kind == "Farm")
        pending = sum(1 for s in state.construction_sites.values() if s.building_kind == "Farm")
        return built + pending

    def test_marginal_civ_digs_out_and_recovers(self):
        state = self._marginal()
        gov = governor.FallbackGovernor()
        engine.run_days(state, gov, days=25)

        # It planted more wheat (built beyond the starting 2 farms)...
        self.assertGreater(sum(1 for b in state.buildings.values() if b.kind == "Farm"), 2)
        # ...bounded (never runs away past the balanced ratio for 2 bakeries)...
        self.assertLessEqual(self._farm_count(state), 8)
        # ...and the civ recovered: fed pawns, bread on hand, no active shortage.
        self.assertGreater(economy.average_need(state, NEED_FOOD), 0.6)
        self.assertGreater(state.stockpile.counts.get(Good.BREAD, 0), 0)
        kinds = [e.kind for e in governor.build_exception_queue(state)]
        self.assertNotIn("low_food", kinds)

    def test_healthy_civ_never_over_builds(self):
        state = create_default_civilization()
        gov = governor.FallbackGovernor()
        engine.run_days(state, gov, days=15)
        # The default civ is a surplus; the governor must not spawn spurious farms.
        self.assertEqual(sum(1 for b in state.buildings.values() if b.kind == "Farm"), 4)


if __name__ == "__main__":
    unittest.main()
