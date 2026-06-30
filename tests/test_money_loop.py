"""Build-2 money-loop coverage for wages and market revenue.

This is the narrow first slice: daily wages move treasury coin into pawn wallets,
and a staffed Market converts surplus bread into treasury coin without touching
reserve food.
"""

import unittest

from agent_town import buildings, economy, engine
from agent_town.core import FactionState, Good, JobRef, Pawn, Stockpile


def worker(pawn_id: str, skill: str = "commerce") -> Pawn:
    return Pawn(
        id=pawn_id,
        name=pawn_id.title(),
        skills={skill: 10},
        needs={},
        mood=80.0,
        schedule="default",
    )


class WageLoopTests(unittest.TestCase):
    def test_daily_wages_pay_assigned_pawns_from_treasury(self):
        pawn = worker("p1", "farming")
        pawn.assignment = JobRef("farm1", "farming")
        state = FactionState(coin=5, pawns={pawn.id: pawn})

        paid = economy.pay_daily_wages(state)

        self.assertEqual(paid, 1)
        self.assertEqual(state.coin, 4)
        self.assertEqual(pawn.coin, 1)

    def test_daily_wages_are_deterministic_when_treasury_is_short(self):
        first = worker("a", "farming")
        second = worker("b", "milling")
        first.assignment = JobRef("farm1", "farming")
        second.assignment = JobRef("mill1", "milling")
        state = FactionState(coin=1, pawns={second.id: second, first.id: first})

        paid = economy.pay_daily_wages(state)

        self.assertEqual(paid, 1)
        self.assertEqual(first.coin, 1)
        self.assertEqual(second.coin, 0)


class MarketLoopTests(unittest.TestCase):
    def test_staffed_market_sells_surplus_bread_above_population_reserve(self):
        market = buildings.make_building("Market", 0, 0, building_id="market1")
        merchant = worker("merchant")
        market.staffed_by.append(merchant.id)
        state = FactionState(
            buildings={market.id: market},
            pawns={merchant.id: merchant},
            stockpile=Stockpile({Good.BREAD: 10}),
        )

        revenue = economy.apply_market_sales(state)

        self.assertEqual(revenue, 4)
        self.assertEqual(state.coin, 4)
        self.assertEqual(state.stockpile.counts[Good.BREAD], 6)

    def test_unstaffed_market_does_not_sell_surplus(self):
        market = buildings.make_building("Market", 0, 0, building_id="market1")
        state = FactionState(
            buildings={market.id: market},
            stockpile=Stockpile({Good.BREAD: 10}),
        )

        revenue = economy.apply_market_sales(state)

        self.assertEqual(revenue, 0)
        self.assertEqual(state.coin, 0)
        self.assertEqual(state.stockpile.counts[Good.BREAD], 10)


class EngineMoneyLoopTests(unittest.TestCase):
    def test_day_rollover_reports_wages_and_market_revenue(self):
        farm = buildings.make_building("Farm", 0, 0, building_id="farm1")
        farmer = worker("farmer", "farming")
        farmer.assignment = JobRef(farm.id, "farming")
        farm.staffed_by.append(farmer.id)
        market = buildings.make_building("Market", 1, 0, building_id="market1")
        merchant = worker("merchant")
        market.staffed_by.append(merchant.id)
        state = FactionState(
            coin=5,
            time_of_day=23,
            tax_rate=0.0,
            buildings={farm.id: farm, market.id: market},
            pawns={farmer.id: farmer, merchant.id: merchant},
            stockpile=Stockpile({Good.BREAD: 16, Good.WATER: 4}),
        )

        result = engine.step_hour(state)

        self.assertEqual(result.days_rolled, 1)
        self.assertEqual(result.wages_paid, 2)
        self.assertEqual(result.market_revenue, 4)
        self.assertEqual(state.coin, 7)


if __name__ == "__main__":
    unittest.main()
