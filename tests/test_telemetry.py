"""Tests for run-log telemetry plumbing (sinks, builders, logger, governor wrap)."""

from __future__ import annotations

import json
import unittest

from agent_town import civilization, engine, governor, telemetry
from agent_town.core import GovernorAction


class _StubStatus:
    def __init__(self, state="idle", model="m", last_latency=1.2, last_error=""):
        self.state = state
        self.model = model
        self.last_latency = last_latency
        self.last_error = last_error


class _SchedulerLike:
    """Mimics the non-blocking scheduler: has .status, decides nothing."""

    def __init__(self, status):
        self.status = status

    def decide(self, context):
        return []


class SinkTests(unittest.TestCase):
    def test_ring_buffer_type_filter(self):
        ring = telemetry.RingBufferSink(maxlen=10, types={"event"})
        ring.write({"type": "snapshot"})
        ring.write({"type": "event", "kind": "x"})
        self.assertEqual([r["type"] for r in ring.records], ["event"])

    def test_ring_buffer_evicts_oldest(self):
        ring = telemetry.RingBufferSink(maxlen=2)
        for i in range(3):
            ring.write({"type": "event", "i": i})
        self.assertEqual([r["i"] for r in ring.records], [1, 2])

    def test_jsonl_file_roundtrip_and_sorted_keys(self, ):
        import tempfile, os
        path = os.path.join(tempfile.mkdtemp(), "log.jsonl")
        sink = telemetry.JsonlFileSink(path)
        sink.write({"b": 2, "a": 1, "type": "event"})
        sink.close()
        with open(path, encoding="utf-8") as fh:
            line = fh.read().strip()
        self.assertTrue(line.index('"a"') < line.index('"b"'))  # sort_keys
        self.assertEqual(json.loads(line)["a"], 1)

    def test_multisink_fans_out(self):
        a = telemetry.RingBufferSink(maxlen=5)
        b = telemetry.RingBufferSink(maxlen=5)
        telemetry.MultiSink([a, b]).write({"type": "event"})
        self.assertEqual(len(a.records), 1)
        self.assertEqual(len(b.records), 1)


class BuildSnapshotTests(unittest.TestCase):
    def test_snapshot_shape(self):
        state = civilization.create_default_civilization()
        result = engine.step_hour(state, governor.FallbackGovernor())
        snap = telemetry.build_snapshot(state, result)
        for key in ("day", "hour", "population", "avg_mood", "needs", "coin",
                    "stockpile", "idle", "broken", "broken_pawn_ids", "staffed",
                    "construction", "wages_paid", "market_revenue",
                    "household_spending", "sales_tax_collected"):
            self.assertIn(key, snap)
        self.assertNotIn("_llm_offline", snap)  # no internal-field leakage


class BuildDecisionTests(unittest.TestCase):
    def test_scheduler_offline_marks_dropped(self):
        gov = _SchedulerLike(_StubStatus(state="offline", last_error="conn refused"))
        state = civilization.create_default_civilization()
        result = engine.step_hour(state, gov)
        decision = telemetry.build_decision(state, gov, result)
        self.assertEqual(decision["llm_source"], "scheduler")
        self.assertTrue(decision["dropped"])
        self.assertEqual(decision["dropped_reason"], "conn refused")

    def test_blocking_llm_error_marks_dropped(self):
        gov = telemetry.TelemetryGovernor(governor.LLMGovernor(propose=lambda ctx: (_ for _ in ()).throw(ValueError("boom"))))
        state = civilization.create_default_civilization()
        result = engine.step_hour(state, gov)
        decision = telemetry.build_decision(state, gov, result)
        self.assertEqual(decision["llm_source"], "llm")
        self.assertEqual(decision["outcome"], "error")
        self.assertTrue(decision["dropped"])

    def test_plain_fallback_is_not_dropped(self):
        gov = governor.FallbackGovernor()
        state = civilization.create_default_civilization()
        result = engine.step_hour(state, gov)
        decision = telemetry.build_decision(state, gov, result)
        self.assertEqual(decision["llm_source"], "fallback")
        self.assertFalse(decision["dropped"])


class TelemetryGovernorTests(unittest.TestCase):
    def test_passthrough_records_actions_without_changing_them(self):
        inner = governor.FallbackGovernor()
        wrapped = telemetry.TelemetryGovernor(inner)
        state = civilization.create_default_civilization()
        ctx = {"faction": {"time_of_day": 8}}
        direct = governor.FallbackGovernor().decide(ctx)
        out = wrapped.decide(ctx)
        self.assertEqual([a.kind for a in out], [a.kind for a in direct])
        self.assertEqual(list(wrapped.last_actions), out)

    def test_delegates_unknown_attributes(self):
        status = _StubStatus()
        wrapped = telemetry.TelemetryGovernor(_SchedulerLike(status))
        self.assertIs(wrapped.status, status)


class RunLoggerTests(unittest.TestCase):
    def test_run_id_on_every_record_and_self_contained_end(self):
        ring = telemetry.RingBufferSink(maxlen=1000)
        logger = telemetry.RunLogger(ring)
        state = civilization.create_default_civilization()
        gov = telemetry.TelemetryGovernor(governor.FallbackGovernor())
        logger.log_run_start(state, gov)
        for _ in range(3):
            result = engine.step_hour(state, gov)
            logger.log_hour(state, result, gov)
        end = logger.log_run_end(state)
        self.assertTrue(all(r.get("run_id") == logger.run_id for r in ring.records))
        self.assertIn("summary", end)
        self.assertIn("color", end)
        self.assertIn("final_snapshot", end)

    def test_log_run_end_is_idempotent(self):
        logger = telemetry.RunLogger()
        state = civilization.create_default_civilization()
        self.assertIsNotNone(logger.log_run_end(state))
        self.assertIsNone(logger.log_run_end(state))


if __name__ == "__main__":
    unittest.main()
