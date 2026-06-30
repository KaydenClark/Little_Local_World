import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from agent_town import health
from agent_town.core import Building, FactionState, Good, Pawn, WorkDecision


class InvariantTests(unittest.TestCase):
    def test_clean_state_has_no_invariant_violations(self):
        state = FactionState()
        state.pawns["p1"] = Pawn(id="p1", name="Pat", mood=50.0, needs={"food": 0.5})
        state.buildings["farm1"] = Building(id="farm1", kind="Farm", x=0, y=0, job_slots=1, staffed_by=["p1"])

        self.assertEqual(health.check_invariants(state), [])

    def test_flags_bad_staffing_stockpile_and_work_decisions(self):
        state = FactionState()
        state.pawns["p1"] = Pawn(id="p1", name="Pat", mood=101.0, needs={"food": -0.1})
        state.stockpile.counts[Good.BREAD] = -1
        state.buildings["farm1"] = Building(id="farm1", kind="Farm", x=0, y=0, staffed_by=["p1", "ghost"])
        state.buildings["mill1"] = Building(id="mill1", kind="Mill", x=1, y=0, staffed_by=["p1"])
        state.work_decisions["ghost"] = WorkDecision(lane="idle")

        violations = health.check_invariants(state)

        self.assertTrue(any("negative stockpile" in item for item in violations))
        self.assertTrue(any("unknown pawn" in item for item in violations))
        self.assertTrue(any("staffed in multiple" in item for item in violations))
        self.assertTrue(any("mood out of range" in item for item in violations))
        self.assertTrue(any("need out of range" in item for item in violations))
        self.assertTrue(any("work decision for unknown pawn" in item for item in violations))


class HealthSummaryTests(unittest.TestCase):
    def test_summary_aggregates_snapshots_decisions_and_events(self):
        snapshots = [
            {"type": "snapshot", "avg_mood": 75.0, "idle_count": 1, "broken_count": 0, "population": 4},
            {"type": "snapshot", "avg_mood": 18.0, "idle_count": 3, "broken_count": 1, "population": 4},
        ]
        decisions = [
            {"type": "decision", "dropped": False, "applied_action_kinds": ["set_schedule"]},
            {"type": "decision", "dropped": True, "applied_action_kinds": []},
        ]
        events = [
            {"type": "event", "kind": "good_depleted", "severity": "critical"},
            {"type": "event", "kind": "invariant_violation", "severity": "critical"},
        ]

        summary = health.health_summary(snapshots, decisions, events)

        self.assertEqual(summary["mood_start"], 75.0)
        self.assertEqual(summary["mood_min"], 18.0)
        self.assertEqual(summary["mood_end"], 18.0)
        self.assertEqual(summary["mood_trend"], "down")
        self.assertEqual(summary["idle_peak"], 3)
        self.assertEqual(summary["break_count"], 1)
        self.assertEqual(summary["dropped_decision_count"], 1)
        self.assertEqual(summary["action_kind_histogram"]["set_schedule"], 1)
        self.assertEqual(summary["invariant_violation_count"], 1)

    def test_red_conditions_are_detected(self):
        summary = {
            "mood_min": health.MOOD_COLLAPSE_THRESHOLD - 1,
            "dropped_decision_rate": health.DROPPED_RATE_RED_THRESHOLD + 0.1,
            "invariant_violation_count": 1,
            "critical_good_depletion_events": 1,
        }

        red = health.red_conditions(summary)

        self.assertTrue(any("invariant" in item for item in red))
        self.assertTrue(any("depleted" in item for item in red))
        self.assertTrue(any("mood collapse" in item for item in red))
        self.assertTrue(any("dropped decision rate" in item for item in red))


class AnalyzeRunScriptTests(unittest.TestCase):
    def test_analyzer_exits_nonzero_for_red_log(self):
        records = [
            {"type": "run_start", "run_id": "red"},
            {"type": "snapshot", "avg_mood": 10.0, "idle_count": 0, "broken_count": 0, "population": 1},
            {"type": "decision", "dropped": True, "applied_action_kinds": []},
            {"type": "event", "kind": "invariant_violation", "severity": "critical", "text": "bad state"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "run.jsonl"
            path.write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")

            completed = subprocess.run(
                [sys.executable, "scripts/analyze_run.py", str(path)],
                check=False,
                text=True,
                capture_output=True,
            )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("RED", completed.stdout)


if __name__ == "__main__":
    unittest.main()
