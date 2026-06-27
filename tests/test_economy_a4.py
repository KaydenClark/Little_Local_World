import unittest

from agent_town.buildings import create_building
from agent_town.construction import building_cost, place_building
from agent_town.core import FactionState, Good, Pawn, Stockpile
from agent_town.economy import advance_day, advance_economy, collect_daily_tax


def _pawn(pawn_id, mood):
    return Pawn(
        id=pawn_id,
        name=pawn_id.title(),
        skills={},
        traits=(),
        wants=(),
        needs={},
        mood=mood,
        schedule="day",
        assignment=None,
        x=0,
        y=0,
        state="idle",
    )


def _state(*buildings, pawns=(), stockpile=None, coin=0, tax_rate=0.1):
    return FactionState(
        stockpile=stockpile or Stockpile(),
        coin=coin,
        pawns=list(pawns),
        buildings=list(buildings),
        construction_sites=[],
        research="",
        season="spring",
        tax_rate=tax_rate,
        day=1,
        time_of_day=9,
    )


class MultiChainProductionTests(unittest.TestCase):
    def test_create_food_and_stone_buildings_with_recipes(self):
        farm = create_building("Farm", 1, 1)
        mill = create_building("Mill", 2, 1)
        bakery = create_building("Bakery", 3, 1)
        quarry = create_building("Quarry", 4, 1)

        self.assertEqual(farm.recipe.outputs, {Good.GRAIN: 1})
        self.assertEqual(mill.recipe.inputs, {Good.GRAIN: 2})
        self.assertEqual(mill.recipe.outputs, {Good.FLOUR: 1})
        self.assertEqual(bakery.recipe.inputs, {Good.FLOUR: 2})
        self.assertEqual(bakery.recipe.outputs, {Good.BREAD: 1})
        self.assertEqual(quarry.recipe.outputs, {Good.STONE: 1})

    def test_seeded_food_chain_produces_bread(self):
        farm = create_building("Farm", 1, 1)
        mill = create_building("Mill", 2, 1)
        bakery = create_building("Bakery", 3, 1)
        for building in (farm, mill, bakery):
            building.staffed_by.append(f"temp-{building.kind.lower()}")
        state = _state(farm, mill, bakery)

        for _ in range(8):
            advance_economy(state, 1.0)

        self.assertEqual(state.stockpile.counts[Good.BREAD], 2)
        self.assertNotIn(Good.GRAIN, state.stockpile.counts)
        self.assertNotIn(Good.FLOUR, state.stockpile.counts)

    def test_quarry_produces_stone(self):
        quarry = create_building("Quarry", 1, 1)
        quarry.staffed_by.append("temp-quarrier")
        state = _state(quarry)

        advance_economy(state, 3.0)

        self.assertEqual(state.stockpile.counts[Good.STONE], 3)


class TaxAndPlacementTests(unittest.TestCase):
    def test_daily_tax_scales_with_population_mood_and_tax_rate(self):
        low = _state(pawns=(_pawn("low-1", 0.2), _pawn("low-2", 0.2)), tax_rate=0.1)
        high = _state(
            pawns=(_pawn("high-1", 0.9), _pawn("high-2", 0.9), _pawn("high-3", 0.9)),
            tax_rate=0.2,
        )

        low_income = collect_daily_tax(low)
        high_income = collect_daily_tax(high)

        self.assertGreater(high_income, low_income)
        self.assertEqual(low.coin, low_income)
        self.assertEqual(high.coin, high_income)

    def test_advance_day_collects_tax_and_moves_day_clock(self):
        state = _state(pawns=(_pawn("one", 0.75),), tax_rate=0.2)
        state.time_of_day = 23

        income = advance_day(state)

        self.assertGreater(income, 0)
        self.assertEqual(state.coin, income)
        self.assertEqual(state.day, 2)
        self.assertEqual(state.time_of_day, 0)

    def test_place_building_spends_coin_and_adds_construction_site(self):
        cost = building_cost("Bakery")
        state = _state(coin=cost)

        site = place_building(state, "Bakery", 6, 7)

        self.assertEqual(state.coin, 0)
        self.assertEqual(state.construction_sites, [site])
        self.assertEqual(site.building_kind, "Bakery")

    def test_place_building_blocks_when_coin_is_low_without_mutating(self):
        cost = building_cost("Bakery")
        state = _state(coin=cost - 1)

        with self.assertRaisesRegex(ValueError, "Insufficient coin"):
            place_building(state, "Bakery", 6, 7)

        self.assertEqual(state.coin, cost - 1)
        self.assertEqual(state.construction_sites, [])


if __name__ == "__main__":
    unittest.main()
