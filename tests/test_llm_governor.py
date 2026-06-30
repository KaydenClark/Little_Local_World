import json
import unittest

from agent_town import buildings, civilization, engine, governor
from agent_town.core import (
    ACTION_SET_SCHEDULE,
    ACTION_SET_WORK_PRIORITY,
    FactionState,
    Good,
    GovernorAction,
    Pawn,
)
from agent_town.llm import LocalLLMClient
from agent_town import pawns


def _small_context():
    """A civilization with one idle, skilled pawn and one open Farm slot."""
    state = FactionState()
    state.pawns["p1"] = Pawn(
        id="p1",
        name="Pat",
        skills={"farming": 12},
        needs={need: 1.0 for need in pawns.BUILD1_NEEDS},
        mood=80.0,
    )
    state.buildings["b1"] = buildings.make_building("Farm", 0, 0, building_id="b1")
    return state, governor.build_context(state)


def _chat_response(obj) -> dict:
    return {"choices": [{"message": {"content": json.dumps(obj)}}]}


class ActionParsingTests(unittest.TestCase):
    def test_action_from_dict_maps_good_to_enum(self):
        action = governor.action_from_dict(
            {"kind": "set_production_target", "building_id": "b1", "good": "bread", "amount": "5"}
        )
        self.assertEqual(action.kind, "set_production_target")
        self.assertEqual(action.good, Good.BREAD)
        self.assertEqual(action.amount, 5)

    def test_action_from_dict_rejects_unknown_kind(self):
        self.assertIsNone(governor.action_from_dict({"kind": "nuke_everything"}))

    def test_action_from_dict_maps_set_work_priority(self):
        action = governor.action_from_dict(
            {"kind": "set_work_priority", "group": "all", "work_type": "baking", "level": "1"}
        )
        self.assertEqual(action.kind, "set_work_priority")
        self.assertEqual(action.group, "all")
        self.assertEqual(action.work_type, "baking")
        self.assertEqual(action.level, 1)

    def test_parse_action_list_skips_junk_and_requires_list(self):
        payload = {"actions": [{"kind": "set_schedule", "group": "all", "template": "rest"}, "nope", 7]}
        actions = governor.parse_action_list(payload)
        self.assertEqual([a.kind for a in actions], [ACTION_SET_SCHEDULE])
        with self.assertRaises(ValueError):
            governor.parse_action_list({"oops": []})


class LLMGovernorDecideTests(unittest.TestCase):
    def test_uses_model_actions_when_valid(self):
        _state, context = _small_context()
        gov = governor.LLMGovernor(
            propose=lambda ctx: {"actions": [{"kind": "set_work_priority", "group": "all", "work_type": "farming", "level": 1}]}
        )

        actions = gov.decide(context)

        self.assertEqual([a.kind for a in actions], [ACTION_SET_WORK_PRIORITY])
        self.assertEqual(actions[0].group, "all")
        self.assertEqual(actions[0].work_type, "farming")
        self.assertEqual(actions[0].level, 1)

    def test_unsafe_all_rest_model_action_defers_to_fallback(self):
        _state, context = _small_context()
        gov = governor.LLMGovernor(
            propose=lambda ctx: {"actions": [{"kind": "set_schedule", "group": "all", "template": "rest"}]}
        )

        self.assertEqual(gov.decide(context), governor.FallbackGovernor().decide(context))

    def test_unsafe_disable_all_essential_work_defers_to_fallback(self):
        _state, context = _small_context()
        gov = governor.LLMGovernor(
            propose=lambda ctx: {"actions": [{"kind": "set_work_priority", "group": "all", "work_type": "farming", "level": 0}]}
        )

        self.assertEqual(gov.decide(context), governor.FallbackGovernor().decide(context))

    def test_unsafe_low_essential_priority_defers_to_fallback(self):
        _state, context = _small_context()
        gov = governor.LLMGovernor(
            propose=lambda ctx: {"actions": [{"kind": "set_work_priority", "group": "all", "work_type": "farming", "level": 4}]}
        )

        self.assertEqual(gov.decide(context), governor.FallbackGovernor().decide(context))

    def test_unsafe_named_essential_disable_defers_to_fallback(self):
        _state, context = _small_context()
        gov = governor.LLMGovernor(
            propose=lambda ctx: {"actions": [{"kind": "set_work_priority", "group": "p1", "work_type": "farming", "level": 0}]}
        )

        self.assertEqual(gov.decide(context), governor.FallbackGovernor().decide(context))

    def test_model_schedule_churn_defers_to_fallback(self):
        _state, context = _small_context()
        gov = governor.LLMGovernor(
            propose=lambda ctx: {"actions": [{"kind": "set_schedule", "group": "all", "template": "night"}]}
        )

        self.assertEqual(gov.decide(context), governor.FallbackGovernor().decide(context))

    def test_unsafe_nonessential_priority_boost_defers_to_fallback(self):
        _state, context = _small_context()
        gov = governor.LLMGovernor(
            propose=lambda ctx: {"actions": [{"kind": "set_work_priority", "group": "all", "work_type": "mining", "level": 1}]}
        )

        self.assertEqual(gov.decide(context), governor.FallbackGovernor().decide(context))

    def test_hard_fallback_on_model_error(self):
        _state, context = _small_context()
        def boom(_ctx):
            raise RuntimeError("model exploded")
        gov = governor.LLMGovernor(propose=boom)

        actions = gov.decide(context)

        # Falls back to the deterministic governor (which now sets policy only;
        # routine staffing is the work arbiter's job, not the governor's).
        self.assertEqual(actions, governor.FallbackGovernor().decide(context))

    def test_empty_model_actions_defer_to_fallback(self):
        _state, context = _small_context()
        gov = governor.LLMGovernor(propose=lambda ctx: {"actions": []})

        self.assertEqual(gov.decide(context), governor.FallbackGovernor().decide(context))

    def test_malformed_payload_falls_back(self):
        _state, context = _small_context()
        gov = governor.LLMGovernor(propose=lambda ctx: {"not_actions": 1})

        self.assertEqual(gov.decide(context), governor.FallbackGovernor().decide(context))


class LLMGovernorClientTests(unittest.TestCase):
    def test_decide_through_injected_http_client(self):
        _state, context = _small_context()
        captured = {}

        def fake_http_post(payload, timeout):
            captured["payload"] = payload
            return _chat_response(
                {"actions": [{"kind": "assign_pawn", "pawn_id": "p1", "building_id": "b1", "role": "farming"}]}
            )

        client = LocalLLMClient(model="test-model", http_post=fake_http_post)
        gov = governor.LLMGovernor(client=client)

        actions = gov.decide(context)

        self.assertEqual(actions, [GovernorAction.assign_pawn("p1", "b1", "farming")])
        # The request used the JSON-schema response format.
        self.assertEqual(captured["payload"]["response_format"]["type"], "json_schema")

    def test_bad_model_content_falls_back(self):
        _state, context = _small_context()
        client = LocalLLMClient(
            model="test-model",
            http_post=lambda payload, timeout: {"choices": [{"message": {"content": "not json at all"}}]},
        )
        gov = governor.LLMGovernor(client=client)

        self.assertEqual(gov.decide(context), governor.FallbackGovernor().decide(context))

    def test_disabled_client_falls_back(self):
        _state, context = _small_context()
        gov = governor.LLMGovernor(client=LocalLLMClient(model=None))

        self.assertEqual(gov.decide(context), governor.FallbackGovernor().decide(context))


class LLMGovernorEngineTests(unittest.TestCase):
    def test_hard_fallback_governor_matches_fallback_over_three_days(self):
        # An always-failing LLM governor must drive the civilization identically to the
        # deterministic fallback - proving the safety net is faithful.
        llm_state = civilization.create_default_civilization()
        fb_state = civilization.create_default_civilization()

        engine.run_days(llm_state, governor.LLMGovernor(propose=_raise), days=3)
        engine.run_days(fb_state, governor.FallbackGovernor(), days=3)

        self.assertEqual(llm_state.coin, fb_state.coin)
        self.assertEqual(
            {pid: round(p.mood, 6) for pid, p in llm_state.pawns.items()},
            {pid: round(p.mood, 6) for pid, p in fb_state.pawns.items()},
        )
        self.assertEqual(llm_state.stockpile.counts, fb_state.stockpile.counts)

    def test_unsafe_model_policy_keeps_three_day_fallback_oracle(self):
        llm_state = civilization.create_default_civilization()
        fb_state = civilization.create_default_civilization()

        unsafe_actions = {
            "actions": [
                {"kind": "set_schedule", "group": "all", "template": "night"},
                {"kind": "set_work_priority", "group": "all", "work_type": "farming", "level": 4},
                {"kind": "set_work_priority", "group": "all", "work_type": "water", "level": 0},
                {"kind": "set_work_priority", "group": "all", "work_type": "mining", "level": 1},
            ]
        }
        engine.run_days(llm_state, governor.LLMGovernor(propose=lambda ctx: unsafe_actions), days=3)
        engine.run_days(fb_state, governor.FallbackGovernor(), days=3)

        self.assertEqual(llm_state.stockpile.counts, fb_state.stockpile.counts)
        self.assertEqual(
            {pid: pawn.schedule for pid, pawn in llm_state.pawns.items()},
            {pid: pawn.schedule for pid, pawn in fb_state.pawns.items()},
        )
        self.assertEqual(
            {pid: dict(pawn.work_priorities) for pid, pawn in llm_state.pawns.items()},
            {pid: dict(pawn.work_priorities) for pid, pawn in fb_state.pawns.items()},
        )


def _raise(_ctx):
    raise RuntimeError("offline")


if __name__ == "__main__":
    unittest.main()
