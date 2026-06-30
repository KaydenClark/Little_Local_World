"""Invariant checks, anomaly detection, and run-health summary (pure logic)."""

import unittest

from agent_town import buildings, health, pawns
from agent_town.core import FactionState, Good, JobRef, Pawn


def _pawn(pid, **kw):
    base = dict(id=pid, name=pid.upper(), skills={"farming": 18}, mood=80.0)
    base.update(kw)
    return Pawn(**base)


class InvariantTests(unittest.TestCase):
    def test_clean_state_has_no_violations(self):
        state = FactionState()
        state.buildings["farm1"] = buildings.make_building("Farm", 0, 0, building_id="farm1")
        state.pawns["p"] = _pawn("p", assignment=JobRef("farm1", "farming"))
        state.buildings["farm1"].staffed_by.append("p")
        self.assertEqual(health.check_invariants(state), [])

    def test_double_staffed_pawn_is_flagged(self):
        state = FactionState()
        for bid in ("farm1", "farm2"):
            state.buildings[bid] = buildings.make_building("Farm", 0, 0, building_id=bid)
            state.buildings[bid].staffed_by.append("p")
        state.pawns["p"] = _pawn("p")
        violations = health.check_invariants(state)
        self.assertTrue(any("staffed in 2 buildings" in v for v in violations))

    def test_overstaffed_and_phantom_and_negative_and_mood(self):
        state = FactionState()
        farm = buildings.make_building("Farm", 0, 0, building_id="farm1")  # job_slots == 1
        farm.staffed_by.extend(["real", "ghost"])  # overstaffed + phantom
        state.buildings["farm1"] = farm
        state.pawns["real"] = _pawn("real", mood=150.0)  # mood out of range
        state.stockpile.counts[Good.BREAD] = -3  # negative stock
        violations = health.check_invariants(state)
        joined = " | ".join(violations)
        self.assertIn("overstaffed", joined)
        self.assertIn("unknown pawn", joined)
        self.assertIn("negative", joined)
        self.assertIn("out of range", joined)


def _snap(**kw):
    base = dict(day=0, hour=6, population=12, avg_mood=80.0, broken=0, idle=1, stockpile={"bread": 10})
    base.update(kw)
    return base


class EventDetectionTests(unittest.TestCase):
    def test_bread_depletion_is_critical(self):
        events = health.detect_events(_snap(stockpile={"bread": 4}), _snap(stockpile={"bread": 0}), {"dropped": False}, [])
        kinds = {(e["kind"], e["severity"]) for e in events}
        self.assertIn((health.EV_GOOD_DEPLETED, health.CRITICAL), kinds)

    def test_new_break_is_critical(self):
        events = health.detect_events(_snap(broken=0), _snap(broken=2), {"dropped": False}, [])
        self.assertTrue(any(e["kind"] == health.EV_PAWN_BREAK and e["severity"] == health.CRITICAL for e in events))

    def test_mass_idle_warns(self):
        events = health.detect_events(_snap(idle=1), _snap(idle=5), {"dropped": False}, [])  # 5/12 > 0.34
        self.assertTrue(any(e["kind"] == health.EV_MASS_IDLE and e["severity"] == health.WARN for e in events))

    def test_mood_collapse_vs_dip(self):
        collapse = health.detect_events(_snap(avg_mood=40), _snap(avg_mood=30), {"dropped": False}, [])
        dip = health.detect_events(_snap(avg_mood=50), _snap(avg_mood=40), {"dropped": False}, [])
        self.assertTrue(any(e["kind"] == health.EV_MOOD_COLLAPSE for e in collapse))
        self.assertTrue(any(e["kind"] == health.EV_MOOD_DIP for e in dip))

    def test_dropped_llm_decision_warns(self):
        events = health.detect_events(_snap(), _snap(), {"dropped": True, "llm_error": "truncated"}, [])
        self.assertTrue(any(e["kind"] == health.EV_LLM_DROPPED for e in events))

    def test_invariant_violation_becomes_a_critical_event(self):
        events = health.detect_events(None, _snap(), {"dropped": False}, ["farm1: overstaffed 2/1"])
        self.assertTrue(any(e["kind"] == health.EV_INVARIANT and e["severity"] == health.CRITICAL for e in events))

    def test_max_severity_picks_the_worst(self):
        events = [
            {"severity": health.INFO},
            {"severity": health.CRITICAL},
            {"severity": health.WARN},
        ]
        self.assertEqual(health.max_severity(events), health.CRITICAL)
        self.assertIsNone(health.max_severity([]))


class SummaryTests(unittest.TestCase):
    def _records(self):
        return [
            {"type": "snapshot", "avg_mood": 80, "idle": 1},
            {"type": "snapshot", "avg_mood": 30, "idle": 6},
            {"type": "decision", "applied": ["set_work_priority"], "llm_state": "idle", "dropped": False},
            {"type": "decision", "applied": [], "llm_state": "offline", "dropped": True},
            {"type": "event", "kind": health.EV_GOOD_DEPLETED, "severity": health.CRITICAL},
        ]

    def test_summary_aggregates_and_flags_problems(self):
        summary = health.health_summary(self._records())
        self.assertEqual(summary["hours"], 2)
        self.assertEqual(summary["mood_min"], 30)
        self.assertEqual(summary["idle_peak"], 6)
        self.assertEqual(summary["llm_dropped"], 1)
        self.assertEqual(summary["llm_dropped_rate"], 0.5)
        self.assertEqual(summary["actions"], {"set_work_priority": 1})

        problems = health.run_problems(summary)
        self.assertTrue(problems)  # critical event + mood collapse + high dropped rate
        self.assertTrue(any("critical" in p for p in problems))

    def test_clean_run_has_no_problems(self):
        summary = health.health_summary(
            [
                {"type": "snapshot", "avg_mood": 80, "idle": 1},
                {"type": "decision", "applied": [], "llm_state": "idle", "dropped": False},
            ]
        )
        self.assertEqual(health.run_problems(summary), [])


if __name__ == "__main__":
    unittest.main()
