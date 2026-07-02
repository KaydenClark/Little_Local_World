import unittest

from agent_town import mood, pawns
from agent_town.core import NEED_FOOD, Pawn, Recipe

WOOD = Recipe(inputs={}, outputs={}, work_units=4.0, skill="woodcutting")


def make_pawn(**kw):
    base = dict(id="p", name="P", schedule="default")
    base.update(kw)
    return Pawn(**base)


class EffectiveWorkTests(unittest.TestCase):
    def test_skilled_industrious_on_shift_works_hard(self):
        pawn = make_pawn(skills={"woodcutting": 16}, traits=("industrious",), mood=90)
        # hour 8 is a work block in the default schedule
        self.assertGreater(mood.effective_work(pawn, WOOD, 8), 1.3)

    def test_off_shift_pawn_contributes_nothing(self):
        pawn = make_pawn(skills={"woodcutting": 16}, mood=90)
        # hour 2 is a sleep block in the default schedule
        self.assertEqual(mood.effective_work(pawn, WOOD, 2), 0.0)

    def test_unskilled_lazy_pawn_works_less_than_specialist(self):
        pawn = make_pawn(skills={}, traits=("lazy",), mood=10)
        value = mood.effective_work(pawn, WOOD, 8)
        self.assertGreater(value, 0.0)
        self.assertLess(value, 0.5)

    def test_high_mood_alone_does_not_boost_effective_work(self):
        steady = make_pawn(skills={"woodcutting": 10}, mood=50)
        elated = make_pawn(skills={"woodcutting": 10}, mood=90)

        self.assertEqual(
            mood.effective_work(steady, WOOD, 8),
            mood.effective_work(elated, WOOD, 8),
        )

    def test_hunger_directly_reduces_effective_work(self):
        fed = make_pawn(skills={"woodcutting": 10}, needs={NEED_FOOD: 0.50})
        hungry = make_pawn(skills={"woodcutting": 10}, needs={NEED_FOOD: 0.20})
        ravenous = make_pawn(skills={"woodcutting": 10}, needs={NEED_FOOD: 0.10})
        malnourished = make_pawn(skills={"woodcutting": 10}, needs={NEED_FOOD: 0.0})

        self.assertEqual(mood.effective_work(fed, WOOD, 8), 1.0)
        self.assertEqual(mood.effective_work(hungry, WOOD, 8), 0.5)
        self.assertEqual(mood.effective_work(ravenous, WOOD, 8), 0.25)
        # A fully-starved pawn keeps a small floor of work rather than zero, so a
        # food shortage stays escapable (no food -> zero work -> no food spiral).
        self.assertEqual(
            mood.effective_work(malnourished, WOOD, 8), mood.HUNGER_STARVING_FLOOR
        )
        self.assertGreater(mood.effective_work(malnourished, WOOD, 8), 0.0)
        self.assertLess(
            mood.effective_work(malnourished, WOOD, 8),
            mood.effective_work(ravenous, WOOD, 8),
        )

    def test_break_state_stops_effective_work(self):
        pawn = make_pawn(skills={"woodcutting": 10}, state=pawns.STATE_SLACKING)

        self.assertEqual(mood.effective_work(pawn, WOOD, 8), 0.0)

    def test_matched_skill_beats_mismatched(self):
        skilled = make_pawn(skills={"woodcutting": 12}, mood=60)
        mismatched = make_pawn(skills={"cooking": 12}, mood=60)
        self.assertGreater(
            mood.effective_work(skilled, WOOD, 8),
            mood.effective_work(mismatched, WOOD, 8),
        )

    def test_factor_helpers(self):
        self.assertAlmostEqual(mood.mood_factor(50), 1.0)
        self.assertAlmostEqual(mood.mood_factor(90), 1.0)
        self.assertGreater(mood.skill_factor(20), mood.skill_factor(0))
        self.assertEqual(mood.schedule_factor("default", 2), 0.0)
        self.assertEqual(mood.schedule_factor("default", 8), 1.0)


if __name__ == "__main__":
    unittest.main()
