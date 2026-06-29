import unittest

from agent_town import mood
from agent_town.core import Pawn, Recipe

WOOD = Recipe(inputs={}, outputs={}, work_units=4.0, skill="woodcutting")


def make_pawn(**kw):
    base = dict(id="p", name="P", schedule="default")
    base.update(kw)
    return Pawn(**base)


class EffectiveWorkTests(unittest.TestCase):
    def test_skilled_happy_industrious_on_shift_works_hard(self):
        pawn = make_pawn(skills={"woodcutting": 16}, traits=("industrious",), mood=90)
        # hour 8 is a work block in the default schedule
        self.assertGreater(mood.effective_work(pawn, WOOD, 8), 1.3)

    def test_off_shift_pawn_contributes_nothing(self):
        pawn = make_pawn(skills={"woodcutting": 16}, mood=90)
        # hour 2 is a sleep block in the default schedule
        self.assertEqual(mood.effective_work(pawn, WOOD, 2), 0.0)

    def test_unskilled_low_mood_lazy_pawn_works_little(self):
        pawn = make_pawn(skills={}, traits=("lazy",), mood=10)
        value = mood.effective_work(pawn, WOOD, 8)
        self.assertGreater(value, 0.0)
        self.assertLess(value, 0.4)

    def test_matched_skill_beats_mismatched(self):
        skilled = make_pawn(skills={"woodcutting": 12}, mood=60)
        mismatched = make_pawn(skills={"cooking": 12}, mood=60)
        self.assertGreater(
            mood.effective_work(skilled, WOOD, 8),
            mood.effective_work(mismatched, WOOD, 8),
        )

    def test_factor_helpers(self):
        self.assertAlmostEqual(mood.mood_factor(50), 1.0)
        self.assertGreater(mood.skill_factor(20), mood.skill_factor(0))
        self.assertEqual(mood.schedule_factor("default", 2), 0.0)
        self.assertEqual(mood.schedule_factor("default", 8), 1.0)


if __name__ == "__main__":
    unittest.main()
