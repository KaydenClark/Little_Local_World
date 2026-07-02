"""Analyzer honesty: pipeline health must not impersonate model efficacy
(Fable review E-4 / Slice D).

The review demonstrated a GREEN verdict on a run where the model applied zero
actions, because "LLM decisions" counted scheduler-attached hours, not model
output. These tests pin the split: per-hour decision ``origin`` says which
policy actually drove the hour, ``health.model_efficacy`` counts model
emissions and model-applied actions separately from pipeline uptime, and a
model-in-play run with zero applied model actions can be AMBER at best.
"""

from __future__ import annotations

import unittest

from agent_town import civilization, engine, governor, health, telemetry
from agent_town.core import GovernorAction


def _decision(**over):
    base = {"type": "decision", "day": 0, "hour": 0, "applied": [], "dropped": False}
    base.update(over)
    return base


def _snapshot(hour=0):
    return {"type": "snapshot", "day": 0, "hour": hour, "avg_mood": 80.0, "idle": 0, "broken": 0, "stockpile": {"bread": 50}}


class ModelEfficacyTests(unittest.TestCase):
    def test_pipeline_only_model_run_is_not_green(self):
        """The review's exact hazard: a healthy scheduler pipeline (llm_state
        idle for every hour) with zero model-origin actions must not stamp GREEN."""
        decisions = [_decision(hour=h, llm_state="idle", llm_source="scheduler") for h in range(96)]
        summary = health.health_summary([_snapshot(h) for h in range(96)], decisions, [])
        self.assertEqual(summary["llm_decisions"], 96)  # pipeline was up...
        self.assertEqual(summary["model_decisions"], 0)  # ...but the model drove nothing
        self.assertTrue(summary["model_pipeline_only"])
        self.assertEqual(health.run_color(summary), "amber")
        self.assertTrue(any("pipeline-only" in c for c in health.run_cautions(summary)))

    def test_model_run_with_applied_actions_can_be_green(self):
        decisions = [_decision(hour=h, llm_state="idle", llm_source="scheduler") for h in range(5)]
        decisions[2] = _decision(
            hour=2, llm_state="idle", llm_source="scheduler",
            origin="model", applied=["set_work_priority", "place_building"],
        )
        summary = health.health_summary([_snapshot(h) for h in range(5)], decisions, [])
        self.assertEqual(summary["model_decisions"], 1)
        self.assertEqual(summary["model_actions"], {"place_building": 1, "set_work_priority": 1})
        self.assertFalse(summary["model_pipeline_only"])
        self.assertEqual(health.run_color(summary), "green")

    def test_fallback_only_run_stays_green(self):
        """No model loaded is fallback-by-design: no efficacy claim, no penalty."""
        decisions = [_decision(hour=h, outcome="disabled") for h in range(5)]
        summary = health.health_summary([_snapshot(h) for h in range(5)], decisions, [])
        self.assertEqual(summary["llm_decisions"], 0)
        self.assertFalse(summary["model_pipeline_only"])
        self.assertEqual(health.run_color(summary), "green")

    def test_old_blocking_log_recovers_origin_from_outcome(self):
        """Pre-v3 blocking-path records carry outcome == "model" - still counted."""
        decisions = [_decision(hour=0, outcome="model", applied=["place_building"])]
        efficacy = health.model_efficacy(decisions)
        self.assertEqual(efficacy["model_decisions"], 1)
        self.assertEqual(efficacy["model_actions_applied"], 1)
        self.assertFalse(efficacy["model_pipeline_only"])

    def test_model_emission_with_nothing_applied_is_still_pipeline_only(self):
        """The model spoke but nothing it said took effect: no efficacy earned."""
        decisions = [_decision(hour=0, llm_state="idle", origin="model", applied=[])]
        efficacy = health.model_efficacy(decisions)
        self.assertEqual(efficacy["model_decisions"], 1)
        self.assertTrue(efficacy["model_pipeline_only"])


class DecisionOriginTests(unittest.TestCase):
    def test_scheduler_marks_only_model_driven_hours(self):
        state = civilization.create_default_civilization()
        context = governor.build_context(state)
        scheduler = governor.CivilizationDecisionScheduler()  # disabled client
        scheduler.decide(context)
        self.assertEqual(scheduler.last_source, governor.SOURCE_FALLBACK)
        # A finished model decision waiting in the mailbox: the next hour is
        # model-driven, the hour after falls back again.
        scheduler._pending = [GovernorAction.place_building("Farm", 1, 1)]
        scheduler.decide(context)
        self.assertEqual(scheduler.last_source, governor.SOURCE_MODEL)
        scheduler.decide(context)
        self.assertEqual(scheduler.last_source, governor.SOURCE_FALLBACK)
        scheduler.shutdown()

    def test_build_decision_records_model_origin(self):
        state = civilization.create_default_civilization()
        gov = governor.LLMGovernor(
            propose=lambda context: {"actions": [{"kind": "place_building", "building_kind": "Farm", "x": 1, "y": 1}]}
        )
        gov.decide(governor.build_context(state))
        record = telemetry.build_decision(state, gov, engine.StepResult())
        self.assertEqual(record["origin"], "model")

    def test_build_decision_records_fallback_origin(self):
        state = civilization.create_default_civilization()
        record = telemetry.build_decision(state, governor.FallbackGovernor(), engine.StepResult())
        self.assertEqual(record["origin"], "fallback")


if __name__ == "__main__":
    unittest.main()
