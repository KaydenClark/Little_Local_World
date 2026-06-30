"""Build-2 water slice: reserve, need pressure, readout, and governor exception."""

import unittest

from agent_town import buildings, economy, engine, governor, pawns
from agent_town.core import FactionState, Good, NEED_WATER, Pawn


def _pawn(pid: str = "p", water: float = 1.0) -> Pawn:
    return Pawn(id=pid, name=pid, needs={need: 1.0 for need in pawns.BUILD1_NEEDS} | {NEED_WATER: water})


class WaterContractTests(unittest.TestCase):
    def test_water_well_produces_water(self):
        state = FactionState(time_of_day=8)
        state.buildings["well1"] = buildings.make_building("Water Well", 0, 0, building_id="well1")
        state.pawns["p"] = _pawn()
        state.pawns["p"].skills["water"] = 20
        state.buildings["well1"].staffed_by.append("p")

        economy.production_tick(state)

        self.assertGreaterEqual(state.stockpile.counts.get(Good.WATER, 0), 1)

    def test_drink_consumes_one_water_unit_and_refills_need(self):
        pawn = _pawn(water=0.2)
        state = FactionState()
        state.stockpile.add(Good.WATER, 2)

        self.assertTrue(pawns.drink(pawn, state.stockpile))

        self.assertEqual(state.stockpile.counts.get(Good.WATER, 0), 1)
        self.assertEqual(pawn.needs[NEED_WATER], 1.0)

    def test_drink_without_water_is_noop(self):
        pawn = _pawn(water=0.2)

        self.assertFalse(pawns.drink(pawn, FactionState().stockpile))
        self.assertEqual(pawn.needs[NEED_WATER], 0.2)


class WaterEngineTests(unittest.TestCase):
    def test_step_hour_drinks_when_water_need_is_low(self):
        state = FactionState(time_of_day=8)
        state.stockpile.add(Good.WATER, 1)
        state.pawns["p"] = _pawn(water=0.2)

        engine.step_hour(state, governor.FallbackGovernor())

        self.assertEqual(state.stockpile.counts.get(Good.WATER, 0), 0)
        self.assertGreater(state.pawns["p"].needs[NEED_WATER], 0.9)

    def test_water_days_of_cover_uses_population_demand(self):
        state = FactionState()
        state.stockpile.add(Good.WATER, 6)
        state.pawns["a"] = _pawn("a")
        state.pawns["b"] = _pawn("b")
        state.pawns["c"] = _pawn("c")

        self.assertEqual(economy.water_days_of_cover(state), 2.0)


class WaterGovernorTests(unittest.TestCase):
    def test_low_water_cover_creates_governor_exception(self):
        state = FactionState()
        state.stockpile.add(Good.WATER, 1)
        state.pawns["a"] = _pawn("a")
        state.pawns["b"] = _pawn("b")

        exceptions = governor.build_exception_queue(state)

        self.assertIn("low_water", [exc.kind for exc in exceptions])


if __name__ == "__main__":
    unittest.main()
