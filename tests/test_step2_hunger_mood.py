"""Step 2 coverage: nutrition reserve, hunger bands, mood drift, the thought
ledger, seeded breaks, and tax stability after the 0-100 recalibration."""

import unittest

from agent_town import economy, engine, mood, pawns
from agent_town.core import (
    FactionState,
    Good,
    NEED_FOOD,
    NEED_RECREATION,
    NEED_REST,
    Pawn,
    Stockpile,
    Thought,
)


def _pawn(**kw):
    base = dict(id="p", name="P")
    base.update(kw)
    return Pawn(**base)


class NutritionReserveTests(unittest.TestCase):
    def test_eat_adds_nutrition_capped_with_overeating_waste(self):
        pawn = _pawn(needs={NEED_FOOD: 0.5})
        stock = Stockpile({Good.BREAD: 2})

        self.assertTrue(pawns.eat(pawn, stock))

        # 0.5 + 0.9 = 1.4, capped at 1.0 -> 0.4 nutrition wasted, one loaf gone.
        self.assertEqual(pawn.needs[NEED_FOOD], 1.0)
        self.assertEqual(stock.counts.get(Good.BREAD, 0), 1)

    def test_eat_without_bread_is_a_noop(self):
        pawn = _pawn(needs={NEED_FOOD: 0.2})
        stock = Stockpile()

        self.assertFalse(pawns.eat(pawn, stock))
        self.assertEqual(pawn.needs[NEED_FOOD], 0.2)

    def test_no_schedule_block_restores_food_for_free(self):
        for block, restored in pawns.SCHEDULE_RESTORATION_PER_HOUR.items():
            self.assertNotIn(NEED_FOOD, restored, f"{block} must not restore food")


class HungerBandTests(unittest.TestCase):
    def test_hunger_thought_follows_saturation_bands(self):
        def value(food):
            thought = mood.hunger_thought(_pawn(needs={NEED_FOOD: food}))
            return None if thought is None else thought.value

        self.assertIsNone(value(0.50))  # Fed
        self.assertIsNone(value(0.25))  # Fed (boundary)
        self.assertEqual(value(0.20), mood.HUNGER_HUNGRY_VALUE)  # -6
        self.assertEqual(value(0.10), mood.HUNGER_RAVENOUS_VALUE)  # -12
        self.assertEqual(value(0.0), mood.HUNGER_MALNOURISHED_VALUE)  # -20


class MoodDriftTests(unittest.TestCase):
    def test_drift_rises_faster_than_it_falls(self):
        self.assertEqual(mood.drift_mood(50.0, 80.0), 62.0)  # +12 toward target
        self.assertEqual(mood.drift_mood(80.0, 50.0), 72.0)  # -8 toward target

    def test_drift_does_not_overshoot_the_target(self):
        self.assertEqual(mood.drift_mood(60.0, 62.0), 62.0)

    def test_mood_is_frozen_while_asleep(self):
        self.assertEqual(mood.drift_mood(50.0, 80.0, asleep=True), 50.0)


class ThoughtLedgerTests(unittest.TestCase):
    def test_identical_thoughts_stack_and_refresh_age(self):
        pawn = _pawn()
        pawns.add_thought(pawn, "catharsis", "Catharsis", 12.0, 8)
        pawn.thoughts[0].age = 5
        pawns.add_thought(pawn, "catharsis", "Catharsis", 12.0, 8)

        self.assertEqual(len(pawn.thoughts), 1)
        self.assertEqual(pawn.thoughts[0].stack, 2)
        self.assertEqual(pawn.thoughts[0].age, 0)

    def test_stacked_thought_value_scales_mood_target(self):
        pawn = _pawn(needs={NEED_REST: 0.5, NEED_FOOD: 0.5, NEED_RECREATION: 0.5})
        base = mood.mood_target(pawn)
        pawn.thoughts.append(Thought("catharsis", "Catharsis", 12.0, stack=2, duration=8))
        self.assertEqual(mood.mood_target(pawn), base + 24.0)

    def test_event_thoughts_expire_after_their_duration(self):
        pawn = _pawn()
        pawns.add_thought(pawn, "catharsis", "Catharsis", 12.0, 8)
        for _ in range(7):
            pawns.age_thoughts(pawn)
        self.assertEqual(len(pawn.thoughts), 1)  # still alive at age 7
        pawns.age_thoughts(pawn)
        self.assertEqual(pawn.thoughts, [])  # expired at age 8


class SeededBreakTests(unittest.TestCase):
    def test_break_roll_is_reproducible_and_seed_sensitive(self):
        a = FactionState(seed=7, day=1, time_of_day=9)
        b = FactionState(seed=7, day=1, time_of_day=9)
        c = FactionState(seed=8, day=1, time_of_day=9)
        pawn = _pawn(id="pawn03")

        self.assertEqual(engine._break_roll(a, pawn), engine._break_roll(b, pawn))
        self.assertNotEqual(engine._break_roll(a, pawn), engine._break_roll(c, pawn))

    def test_break_chance_is_higher_in_worse_bands(self):
        self.assertGreater(pawns.break_chance(pawns.MTB_EXTREME), pawns.break_chance(pawns.MTB_MINOR))
        self.assertEqual(pawns.break_chance(0.0), 1.0)


class TaxRecalibrationTests(unittest.TestCase):
    def test_tax_income_unchanged_by_the_0_100_switch(self):
        state = FactionState(tax_rate=0.2)
        for index in range(4):
            state.pawns[f"p{index}"] = _pawn(id=f"p{index}", mood=80.0)

        # average_mood is now 0-100; tax keeps its pre-switch calibration.
        self.assertEqual(economy.average_mood(state), 80.0)
        self.assertEqual(economy.daily_tax_income(state), int(4 * 0.8 * 0.2 * 10))


if __name__ == "__main__":
    unittest.main()
