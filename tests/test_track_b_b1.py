import unittest

from agent_town import mood, pawns, schedule
from agent_town.core import (
    BUILD1_NEEDS,
    FactionState,
    NEED_FOOD,
    NEED_RECREATION,
    NEED_REST,
    Pawn,
    SCHEDULE_ANY,
    SCHEDULE_REC,
    SCHEDULE_SLEEP,
    SCHEDULE_WORK,
)


class ScheduleTemplateTests(unittest.TestCase):
    def test_templates_cover_default_night_and_rest(self):
        self.assertIn("default", schedule.SCHEDULE_TEMPLATES)
        self.assertIn("night", schedule.SCHEDULE_TEMPLATES)
        self.assertIn("rest", schedule.SCHEDULE_TEMPLATES)

        default = schedule.template("default")
        self.assertEqual(len(default.blocks), 24)
        self.assertIn(SCHEDULE_SLEEP, default.blocks)
        self.assertIn(SCHEDULE_WORK, default.blocks)
        self.assertIn(SCHEDULE_REC, default.blocks)

    def test_template_lookup_falls_back_to_default(self):
        self.assertIs(schedule.template("unknown"), schedule.template("default"))

    def test_block_for_wraps_hours(self):
        self.assertEqual(schedule.block_for("default", 8), SCHEDULE_WORK)
        self.assertEqual(schedule.block_for("default", 32), SCHEDULE_WORK)

    def test_advance_clock_rolls_days(self):
        state = FactionState(day=3, time_of_day=22)

        rolled = schedule.advance_clock(state, 5)

        self.assertEqual(rolled, 1)
        self.assertEqual(state.day, 4)
        self.assertEqual(state.time_of_day, 3)

    def test_advance_clock_rejects_negative_hours(self):
        with self.assertRaises(ValueError):
            schedule.advance_clock(FactionState(), -1)


class PawnNeedsTests(unittest.TestCase):
    def test_decay_needs_initializes_build1_needs_and_clamps_to_zero(self):
        pawn = Pawn(id="p1", name="Ada")

        pawns.decay_needs(pawn, 24)

        self.assertEqual(set(BUILD1_NEEDS), set(pawn.needs))
        self.assertEqual(pawn.needs[NEED_FOOD], 0.0)
        self.assertGreater(pawn.needs[NEED_RECREATION], 0.0)
        for value in pawn.needs.values():
            self.assertGreaterEqual(value, 0.0)
            self.assertLessEqual(value, 1.0)

    def test_restore_need_clamps_and_validates(self):
        pawn = Pawn(id="p1", name="Ada", needs={NEED_FOOD: 0.2})

        pawns.restore_need(pawn, NEED_FOOD, 2.0)

        self.assertEqual(pawn.needs[NEED_FOOD], 1.0)
        with self.assertRaises(ValueError):
            pawns.restore_need(pawn, "comfort", 0.1)
        with self.assertRaises(ValueError):
            pawns.restore_need(pawn, NEED_FOOD, -0.1)

    def test_schedule_blocks_restore_rest_and_recreation_but_not_food(self):
        pawn = Pawn(
            id="p1",
            name="Ada",
            needs={NEED_REST: 0.2, NEED_FOOD: 0.2, NEED_RECREATION: 0.2},
        )

        pawns.apply_schedule_block(pawn, SCHEDULE_SLEEP, 1)
        pawns.apply_schedule_block(pawn, SCHEDULE_REC, 1)
        pawns.apply_schedule_block(pawn, SCHEDULE_ANY, 1)
        before_work = dict(pawn.needs)
        pawns.apply_schedule_block(pawn, SCHEDULE_WORK, 1)

        self.assertGreater(pawn.needs[NEED_REST], 0.2)
        self.assertGreater(pawn.needs[NEED_RECREATION], 0.2)
        # Food is a nutrition reserve now: no schedule block restores it for free.
        self.assertEqual(pawn.needs[NEED_FOOD], 0.2)
        self.assertEqual(pawn.needs, before_work)

    def test_needs_satisfaction_is_mean_of_tracked_needs(self):
        pawn = Pawn(
            id="p1",
            name="Ada",
            needs={NEED_REST: 1.0, NEED_FOOD: 0.5, NEED_RECREATION: -1.0},
        )

        self.assertEqual(pawns.needs_satisfaction(pawn), 0.5)

    def test_negative_decay_is_rejected(self):
        with self.assertRaises(ValueError):
            pawns.decay_needs(Pawn(id="p1", name="Ada"), -0.1)


class MoodTests(unittest.TestCase):
    def test_mood_target_tracks_needs_satisfaction(self):
        rested = Pawn(
            id="rested",
            name="Rested",
            needs={NEED_REST: 1.0, NEED_FOOD: 1.0, NEED_RECREATION: 1.0},
        )
        strained = Pawn(
            id="strained",
            name="Strained",
            needs={NEED_REST: 0.0, NEED_FOOD: 0.0, NEED_RECREATION: 0.0},
        )

        # Mood is now on a 0-100 scale (mood_target replaces compute_mood).
        self.assertGreater(mood.mood_target(rested), mood.mood_target(strained))
        self.assertGreaterEqual(mood.mood_target(strained), 0.0)
        self.assertLessEqual(mood.mood_target(rested), 100.0)


if __name__ == "__main__":
    unittest.main()
