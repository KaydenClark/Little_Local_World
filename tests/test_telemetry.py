"""Run-log telemetry: snapshots, decisions, sinks, and determinism-safety."""

import json
import tempfile
import unittest
from pathlib import Path

from agent_town import civilization, engine, governor, telemetry
from agent_town.core import FactionState, GovernorAction, JobRef, Pawn
from agent_town import buildings, pawns


def _farm_state():
    state = FactionState(day=1, time_of_day=8)
    state.buildings["farm1"] = buildings.make_building("Farm", 0, 0, building_id="farm1")
    state.pawns["p0"] = Pawn(
        id="p0", name="P0", skills={"farming": 18},
        needs={n: 1.0 for n in pawns.BUILD1_NEEDS}, mood=80.0,
        assignment=JobRef("farm1", "farming"),
    )
    state.buildings["farm1"].staffed_by.append("p0")
    state.pawns["p1"] = Pawn(id="p1", name="P1", skills={"baking": 18},
                             needs={n: 1.0 for n in pawns.BUILD1_NEEDS}, mood=80.0)
    return state


class _Result:
    def __init__(self, applied=(), completed=(), tax=0, days=0):
        self.actions_applied = tuple(applied)
        self.buildings_completed = tuple(completed)
        self.tax_collected = tax
        self.days_rolled = days


class SnapshotTests(unittest.TestCase):
    def test_snapshot_captures_civ_state(self):
        snap = telemetry.build_snapshot(_farm_state(), _Result(tax=3, days=1))
        self.assertEqual(snap["type"], "snapshot")
        self.assertEqual((snap["day"], snap["hour"]), (1, 8))
        self.assertEqual(snap["population"], 2)
        self.assertEqual(snap["idle"], 1)  # p1 has no assignment
        self.assertEqual(snap["staffed"], {"farming": 1})
        self.assertEqual(snap["tax_collected"], 3)
        self.assertEqual(snap["days_rolled"], 1)


class DecisionTests(unittest.TestCase):
    def test_proposed_vs_applied_and_rejected(self):
        gov = telemetry.TelemetryGovernor(governor.FallbackGovernor())
        gov.last_actions = [GovernorAction.set_work_priority("all", "farming", 1),
                            GovernorAction.assign_pawn("p0", "farm1", "farming")]
        result = _Result(applied=[GovernorAction.set_work_priority("all", "farming", 1)])
        decision = telemetry.build_decision(gov, result)
        self.assertEqual(decision["proposed"], ["set_work_priority", "assign_pawn"])
        self.assertEqual(decision["applied"], ["set_work_priority"])
        self.assertEqual(decision["rejected"], ["assign_pawn"])
        self.assertEqual(decision["governor_kind"], "fallback")

    def test_llm_outcome_marks_dropped(self):
        llm = governor.LLMGovernor(propose=lambda ctx: (_ for _ in ()).throw(RuntimeError("boom")))
        gov = telemetry.TelemetryGovernor(llm)
        gov.decide({"roster": [], "buildings": [], "construction": [], "exceptions": []})
        decision = telemetry.build_decision(gov, _Result())
        self.assertEqual(decision["governor_kind"], "llm")
        self.assertEqual(decision["outcome"], "error")
        self.assertTrue(decision["dropped"])


class TelemetryGovernorTests(unittest.TestCase):
    def test_pass_through_returns_inner_decision_and_captures_it(self):
        inner = governor.FallbackGovernor()
        gov = telemetry.TelemetryGovernor(inner)
        context = governor.build_context(_farm_state())

        self.assertEqual(gov.decide(context), inner.decide(context))
        self.assertEqual([a.kind for a in gov.last_actions], [a.kind for a in inner.decide(context)])
        self.assertGreaterEqual(gov.last_decide_ms, 0.0)

    def test_delegates_unknown_attributes_to_inner(self):
        from agent_town.llm import LocalLLMClient

        # A scheduler with no client is disabled; status + enabled delegate through.
        sched = governor.CivilizationDecisionScheduler(LocalLLMClient(model=None))
        gov = telemetry.TelemetryGovernor(sched)
        self.assertIsNotNone(gov.status)  # delegated property
        self.assertFalse(gov.enabled)  # delegated attribute
        sched.shutdown(wait=True)


class SinkTests(unittest.TestCase):
    def test_ring_buffer_filters_by_type(self):
        ring = telemetry.RingBufferSink(maxlen=10, types={"event"})
        ring.write({"type": "snapshot"})
        ring.write({"type": "event", "kind": "x"})
        self.assertEqual([r["type"] for r in ring.records], ["event"])

    def test_jsonl_file_sink_round_trips(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "sub" / "run.jsonl"
            sink = telemetry.JsonlFileSink(path)
            sink.write({"type": "snapshot", "day": 0})
            sink.write({"type": "event", "kind": "x"})
            sink.close()
            lines = path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual([json.loads(line)["type"] for line in lines], ["snapshot", "event"])


class LoggerTests(unittest.TestCase):
    def test_log_hour_emits_snapshot_and_decision(self):
        ring = telemetry.RingBufferSink(maxlen=50)
        log = telemetry.RunLogger(ring)
        state = _farm_state()
        gov = telemetry.TelemetryGovernor(governor.FallbackGovernor())
        result = engine.step_hour(state, gov)
        log.log_hour(state, result, gov)
        types = [r["type"] for r in ring.records]
        self.assertIn("snapshot", types)
        self.assertIn("decision", types)

    def test_logging_does_not_change_the_simulation(self):
        # Logging is a pure observer: a logged run and an unlogged run must reach
        # identical sim state.
        logged = civilization.create_default_civilization()
        plain = civilization.create_default_civilization()
        log = telemetry.RunLogger(telemetry.RingBufferSink(maxlen=10_000))
        gov_logged = telemetry.TelemetryGovernor(governor.FallbackGovernor())

        for _ in range(48):
            result = engine.step_hour(logged, gov_logged)
            log.log_hour(logged, result, gov_logged)
        engine.run(plain, governor.FallbackGovernor(), hours=48)

        self.assertEqual(logged.coin, plain.coin)
        self.assertEqual(logged.stockpile.counts, plain.stockpile.counts)
        self.assertEqual(
            {pid: round(p.mood, 6) for pid, p in logged.pawns.items()},
            {pid: round(p.mood, 6) for pid, p in plain.pawns.items()},
        )
        self.assertEqual(
            {pid: (p.assignment.building_id if p.assignment else None) for pid, p in logged.pawns.items()},
            {pid: (p.assignment.building_id if p.assignment else None) for pid, p in plain.pawns.items()},
        )


if __name__ == "__main__":
    unittest.main()
