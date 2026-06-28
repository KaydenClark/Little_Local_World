"""Tests for the non-blocking colony governor scheduler (integration I2).

The scheduler runs the LLM governor's model call off the render loop. These
tests mirror ``test_llm.py``'s scheduler suite: an injected ``http_post`` stands
in for a live model, so nothing here touches the network.
"""

import json
import os
import time
import unittest
from unittest.mock import patch

from agent_town import buildings, governor
from agent_town.core import ACTION_SET_SCHEDULE, FactionState, Pawn
from agent_town.governor import ColonyDecisionScheduler, FallbackGovernor
from agent_town.llm import LocalLLMClient
from agent_town import pawns


def _small_context():
    """A colony with one idle, skilled pawn and one open Farm slot."""
    state = FactionState()
    state.pawns["p1"] = Pawn(
        id="p1",
        name="Pat",
        skills={"farming": 12},
        needs={need: 1.0 for need in pawns.BUILD1_NEEDS},
        mood=0.8,
    )
    state.buildings["b1"] = buildings.make_building("Farm", 0, 0, building_id="b1")
    return state, governor.build_context(state)


def _chat_response(obj) -> dict:
    return {"choices": [{"message": {"content": json.dumps(obj)}}]}


def _rest_all_post(payload, timeout):
    return _chat_response(
        {"actions": [{"kind": "set_schedule", "group": "all", "template": "rest"}]}
    )


class SchedulerNonBlockingTests(unittest.TestCase):
    def test_decide_returns_immediately_and_uses_fallback_while_thinking(self):
        _state, context = _small_context()
        calls = []

        def slow_post(payload, timeout):
            calls.append(payload)
            time.sleep(0.2)
            return _rest_all_post(payload, timeout)

        sched = ColonyDecisionScheduler(
            LocalLLMClient(model="gemma-test", http_post=slow_post), interval=0.0
        )

        start = time.perf_counter()
        first = sched.decide(context)
        elapsed = time.perf_counter() - start

        try:
            self.assertLess(elapsed, 0.05)
            # The model is still thinking, so the colony runs on the fallback.
            self.assertEqual(first, FallbackGovernor().decide(context))
            self.assertEqual(sched.status.state, "thinking")
        finally:
            sched.shutdown(wait=True)
        self.assertEqual(len(calls), 1)

    def test_decision_upgrades_to_llm_actions_when_ready(self):
        _state, context = _small_context()
        # A real cooldown keeps the scheduler from instantly re-submitting after
        # it harvests, so the harvested "idle" state is observable.
        sched = ColonyDecisionScheduler(
            LocalLLMClient(model="gemma-test", http_post=_rest_all_post), interval=10.0
        )

        upgraded = None
        deadline = time.perf_counter() + 1.0
        while time.perf_counter() < deadline:
            actions = sched.decide(context)
            if [a.kind for a in actions] == [ACTION_SET_SCHEDULE]:
                upgraded = actions
                break
            time.sleep(0.01)
        sched.shutdown(wait=True)

        self.assertIsNotNone(upgraded, "scheduler never surfaced the model's actions")
        self.assertEqual(upgraded[0].group, "all")
        self.assertEqual(upgraded[0].template, "rest")
        self.assertEqual(sched.status.state, "idle")
        self.assertEqual(sched.status.last_action_kinds, (ACTION_SET_SCHEDULE,))

    def test_keeps_one_request_in_flight(self):
        _state, context = _small_context()
        calls = []

        def slow_post(payload, timeout):
            calls.append(payload)
            time.sleep(0.2)
            return _rest_all_post(payload, timeout)

        sched = ColonyDecisionScheduler(
            LocalLLMClient(model="gemma-test", http_post=slow_post), interval=0.0
        )

        sched.decide(context)
        deadline = time.perf_counter() + 0.1
        while not calls and time.perf_counter() < deadline:
            time.sleep(0.005)
        sched.decide(context)  # second call must not launch a parallel request

        sched.shutdown(wait=True)
        self.assertEqual(len(calls), 1)


class SchedulerFallbackTests(unittest.TestCase):
    def test_offline_model_reports_offline_and_keeps_running_on_fallback(self):
        _state, context = _small_context()

        def offline_post(payload, timeout):
            raise ConnectionError("server refused connection")

        sched = ColonyDecisionScheduler(
            LocalLLMClient(model="gemma-test", http_post=offline_post), interval=10.0
        )

        sched.decide(context)
        deadline = time.perf_counter() + 0.5
        while sched.status.state == "thinking" and time.perf_counter() < deadline:
            sched.decide(context)
            time.sleep(0.01)

        # The colony keeps getting valid fallback actions regardless of the model.
        fallback_actions = sched.decide(context)
        sched.shutdown(wait=True)
        self.assertEqual(sched.status.state, "offline")
        self.assertEqual(fallback_actions, FallbackGovernor().decide(context))

    def test_disabled_scheduler_always_uses_fallback(self):
        _state, context = _small_context()
        sched = ColonyDecisionScheduler(LocalLLMClient(model=None))

        self.assertFalse(sched.enabled)
        self.assertEqual(sched.status.state, "disabled")
        self.assertEqual(sched.decide(context), FallbackGovernor().decide(context))
        sched.shutdown(wait=True)


class SchedulerToggleTests(unittest.TestCase):
    def test_can_be_disabled_and_reconnected_at_runtime(self):
        sched = ColonyDecisionScheduler(LocalLLMClient(model=None))
        self.assertFalse(sched.enabled)

        with patch.dict(os.environ, {}, clear=True):
            connected = sched.connect_from_env(
                model_discovery=lambda base_url, timeout: "google/gemma-4-e4b"
            )

        self.assertTrue(connected)
        self.assertTrue(sched.enabled)
        self.assertEqual(sched.status.state, "idle")
        self.assertEqual(sched.status.model, "google/gemma-4-e4b")

        sched.disable("Turned off in game.")
        self.assertFalse(sched.enabled)
        self.assertEqual(sched.status.state, "disabled")
        self.assertEqual(sched.status.last_error, "Turned off in game.")
        sched.shutdown(wait=True)

    def test_toggle_flips_between_llm_and_fallback(self):
        sched = ColonyDecisionScheduler(LocalLLMClient(model=None))

        with patch.dict(os.environ, {}, clear=True):
            now_on = sched.toggle(model_discovery=lambda base_url, timeout: "model-1")
        self.assertTrue(now_on)
        self.assertTrue(sched.enabled)

        now_on = sched.toggle()
        self.assertFalse(now_on)
        self.assertFalse(sched.enabled)
        sched.shutdown(wait=True)

    def test_toggle_reports_failure_when_no_model_found(self):
        sched = ColonyDecisionScheduler(LocalLLMClient(model=None))

        with patch.dict(os.environ, {}, clear=True):
            now_on = sched.toggle(model_discovery=lambda base_url, timeout: "")

        self.assertFalse(now_on)
        self.assertFalse(sched.enabled)
        self.assertEqual(sched.status.state, "disabled")
        sched.shutdown(wait=True)


if __name__ == "__main__":
    unittest.main()
