import unittest

from agent_town import governor, work
from agent_town.core import (
    ACTION_PLACE_BUILDING,
    ACTION_SET_SCHEDULE,
    Building,
    FactionState,
    Good,
    GovernorAction,
    JobRef,
    Pawn,
    Recipe,
)


def wood_recipe():
    return Recipe({Good.LOGS: 1}, {Good.PLANKS: 1}, 4.0, "woodcutting")


def town():
    state = FactionState()
    state.buildings["saw1"] = Building(
        id="saw1", kind="Sawmill", x=0, y=0, recipe=wood_recipe(), job_slots=1
    )
    state.pawns["ace"] = Pawn(id="ace", name="Ace", skills={"woodcutting": 8}, mood=0.7)
    state.pawns["ben"] = Pawn(id="ben", name="Ben", skills={"woodcutting": 2}, mood=0.7)
    return state


class FallbackGovernorTests(unittest.TestCase):
    def test_fallback_no_longer_hand_places_pawns(self):
        # Build 2 moved routine staffing to the work arbiter; the fallback only
        # sets policy now, so it emits no assign_pawn for an idle, staffable civ.
        actions = governor.FallbackGovernor().decide(governor.build_context(town()))
        self.assertFalse([a for a in actions if a.kind == "assign_pawn"])

    def test_arbiter_seats_best_skill_pawn_into_the_open_slot(self):
        # The behaviour that used to be the fallback's job now lives in work.py:
        # the higher-skill pawn (priority 2) beats the lower-skill one (priority 3)
        # for the single Sawmill slot, and the loser is left idle, not double-seated.
        state = town()
        work.assign_jobs(state)
        self.assertEqual(state.pawns["ace"].assignment, JobRef("saw1", "woodcutting"))
        self.assertIsNone(state.pawns["ben"].assignment)
        self.assertEqual(state.buildings["saw1"].staffed_by, ["ace"])

    def test_reschedules_unhappy_pawn(self):
        state = town()
        state.pawns["ben"].mood = 0.2  # breaking
        actions = governor.FallbackGovernor().decide(governor.build_context(state))
        scheds = [a for a in actions if a.kind == ACTION_SET_SCHEDULE]
        self.assertTrue(any(a.group == "ben" and a.template == "rest" for a in scheds))

    def test_requests_next_missing_chain_building(self):
        state = FactionState()

        actions = governor.FallbackGovernor().decide(governor.build_context(state))

        places = [a for a in actions if a.kind == ACTION_PLACE_BUILDING]
        self.assertEqual(len(places), 1)
        self.assertEqual(places[0].building_kind, "Forester")


class ApplyActionsTests(unittest.TestCase):
    def test_apply_assign_then_reject_full_building(self):
        state = town()
        ok = GovernorAction.assign_pawn("ace", "saw1", "woodcutting")
        self.assertEqual(governor.apply_actions(state, [ok]), [ok])
        self.assertIn("ace", state.buildings["saw1"].staffed_by)
        self.assertEqual(state.pawns["ace"].assignment, JobRef("saw1", "woodcutting"))
        self.assertFalse(
            governor.validate_action(state, GovernorAction.assign_pawn("ben", "saw1", "woodcutting"))
        )

    def test_apply_set_schedule_all(self):
        state = town()
        applied = governor.apply_actions(state, [GovernorAction.set_schedule("all", "night")])
        self.assertEqual(len(applied), 1)
        self.assertTrue(all(p.schedule == "night" for p in state.pawns.values()))

    def test_invalid_action_is_skipped(self):
        state = town()
        bad = GovernorAction.assign_pawn("ghost", "saw1", "woodcutting")
        self.assertEqual(governor.apply_actions(state, [bad]), [])

    def test_place_building_action_is_returned_for_engine_realization(self):
        state = FactionState()
        action = GovernorAction.place_building("Forester", 1, 1)

        self.assertEqual(governor.apply_actions(state, [action]), [action])

    def test_assign_pawn_sets_forced_override(self):
        state = town()
        governor.apply_actions(state, [GovernorAction.assign_pawn("ace", "saw1", "woodcutting")])
        # The override pins the pawn so the arbiter keeps it (the forced lane).
        self.assertEqual(state.pawns["ace"].forced_assignment, JobRef("saw1", "woodcutting"))

    def test_set_work_priority_applies_to_group(self):
        state = town()
        action = GovernorAction.set_work_priority("all", "woodcutting", 1)
        self.assertTrue(governor.validate_action(state, action))
        self.assertEqual(governor.apply_actions(state, [action]), [action])
        self.assertTrue(all(p.work_priorities["woodcutting"] == 1 for p in state.pawns.values()))

    def test_set_work_priority_rejects_out_of_range_level(self):
        state = town()
        self.assertFalse(
            governor.validate_action(state, GovernorAction.set_work_priority("ace", "woodcutting", 9))
        )
        self.assertEqual(
            governor.apply_actions(state, [GovernorAction.set_work_priority("ace", "woodcutting", 9)]), []
        )


class ContextTests(unittest.TestCase):
    def test_context_has_summary_roster_buildings_exceptions(self):
        ctx = governor.build_context(town())
        for key in ("faction", "roster", "buildings", "construction", "exceptions"):
            self.assertIn(key, ctx)
        self.assertEqual(ctx["faction"]["population"], 2)


if __name__ == "__main__":
    unittest.main()
