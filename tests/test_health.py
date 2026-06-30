"""Tests for civilization invariants, debounced anomaly detection, and summary."""

from __future__ import annotations

import unittest

from agent_town import civilization, health
from agent_town.core import Good


def _snapshot(**over):
    base = {
        "type": "snapshot",
        "day": 0,
        "hour": 0,
        "population": 12,
        "avg_mood": 80.0,
        "idle": 0,
        "broken": 0,
        "broken_pawn_ids": [],
        "stockpile": {"bread": 50},
    }
    base.update(over)
    return base


def _decision(**over):
    base = {"type": "decision", "day": 0, "hour": 0, "applied": [], "dropped": False}
    base.update(over)
    return base


class CheckInvariantsTests(unittest.TestCase):
    def test_default_civilization_is_clean(self):
        state = civilization.create_default_civilization()
        self.assertEqual(health.check_invariants(state), [])

    def test_flags_negative_stock_and_bad_mood(self):
        state = civilization.create_default_civilization()
        state.stockpile.counts[Good.BREAD] = -3
        next(iter(state.pawns.values())).mood = 150.0
        violations = health.check_invariants(state)
        self.assertTrue(any("negative" in v for v in violations))
        self.assertTrue(any("mood out of range" in v for v in violations))


class DepletionDebounceTests(unittest.TestCase):
    """The week-proof lesson: intermediate goods cycling through zero must not spam."""

    def test_intermediate_good_cycling_through_zero_is_silent(self):
        monitor = health.EventMonitor()
        # grain bounces 5 -> 0 -> 5 -> 0 repeatedly; never alarms.
        for hour, grain in enumerate([5, 0, 5, 0, 5, 0]):
            events = monitor.observe(
                _snapshot(hour=hour, stockpile={"grain": grain, "bread": 50}),
                _decision(hour=hour),
                [],
            )
            self.assertEqual([e for e in events if e["kind"] == health.EV_GOOD_DEPLETED], [])
            self.assertEqual([e for e in events if e["kind"] == health.EV_GOOD_STALLED], [])

    def test_intermediate_good_stalled_after_sustained_zero(self):
        monitor = health.EventMonitor()
        stalls = []
        for hour in range(health.SUSTAINED_ZERO_HOURS + 2):
            events = monitor.observe(
                _snapshot(hour=hour, stockpile={"flour": 0, "bread": 0}),
                _decision(hour=hour),
                [],
            )
            stalls += [e for e in events if e["kind"] == health.EV_GOOD_STALLED]
        # Fires exactly once when the streak crosses the threshold (latched).
        self.assertEqual(len(stalls), 1)
        self.assertEqual(stalls[0]["severity"], health.WARN)

    def test_empty_intermediate_with_downstream_reserve_is_not_stalled(self):
        monitor = health.EventMonitor()
        stalls = []
        for hour in range(health.SUSTAINED_ZERO_HOURS + 2):
            events = monitor.observe(
                _snapshot(hour=hour, stockpile={"logs": 0, "planks": 20, "bread": 50}),
                _decision(hour=hour),
                [],
            )
            stalls += [e for e in events if e["kind"] == health.EV_GOOD_STALLED]

        self.assertEqual(stalls, [])

    def test_staple_depletion_is_critical_and_fires_once(self):
        monitor = health.EventMonitor()
        depletions = []
        for hour, bread in enumerate([10, 0, 0, 0]):
            events = monitor.observe(
                _snapshot(hour=hour, stockpile={"bread": bread}),
                _decision(hour=hour),
                [],
            )
            depletions += [e for e in events if e["kind"] == health.EV_GOOD_DEPLETED]
        self.assertEqual(len(depletions), 1)
        self.assertEqual(depletions[0]["severity"], health.CRITICAL)

    def test_staple_re_arms_after_refill(self):
        monitor = health.EventMonitor()
        seq = [10, 0, 5, 0]  # deplete, refill, deplete again -> two alarms
        depletions = []
        for hour, bread in enumerate(seq):
            events = monitor.observe(_snapshot(hour=hour, stockpile={"bread": bread}), _decision(hour=hour), [])
            depletions += [e for e in events if e["kind"] == health.EV_GOOD_DEPLETED]
        self.assertEqual(len(depletions), 2)


class EdgeTriggerTests(unittest.TestCase):
    def test_mood_band_latch_fires_once_per_descent(self):
        monitor = health.EventMonitor()
        dips = []
        for hour, mood in enumerate([80, 40, 42, 38, 80, 40]):  # warn, stay, stay, recover, warn again
            events = monitor.observe(_snapshot(hour=hour, avg_mood=mood), _decision(hour=hour), [])
            dips += [e for e in events if e["kind"] == health.EV_MOOD_DIP]
        self.assertEqual(len(dips), 2)

    def test_mood_collapse_is_critical(self):
        monitor = health.EventMonitor()
        events = monitor.observe(_snapshot(avg_mood=80), _decision(), [])
        events += monitor.observe(_snapshot(hour=1, avg_mood=30), _decision(hour=1), [])
        collapse = [e for e in events if e["kind"] == health.EV_MOOD_COLLAPSE]
        self.assertEqual(len(collapse), 1)
        self.assertEqual(collapse[0]["severity"], health.CRITICAL)

    def test_llm_offline_then_recovered_edges(self):
        monitor = health.EventMonitor()
        kinds = []
        for hour, state in enumerate(["idle", "offline", "offline", "idle"]):
            events = monitor.observe(_snapshot(hour=hour), _decision(hour=hour, llm_state=state, dropped=state == "offline"), [])
            kinds += [e["kind"] for e in events]
        self.assertEqual(kinds.count(health.EV_LLM_OFFLINE), 1)
        self.assertEqual(kinds.count(health.EV_LLM_RECOVERED), 1)

    def test_pawn_break_fires_on_rising_count(self):
        monitor = health.EventMonitor()
        monitor.observe(_snapshot(broken=0), _decision(), [])
        events = monitor.observe(_snapshot(hour=1, broken=2, broken_pawn_ids=["p1", "p2"]), _decision(hour=1), [])
        breaks = [e for e in events if e["kind"] == health.EV_PAWN_BREAK]
        self.assertEqual(len(breaks), 1)
        self.assertEqual(breaks[0]["severity"], health.CRITICAL)


class HealthSummaryTests(unittest.TestCase):
    def test_disabled_run_does_not_count_as_llm_decisions(self):
        # No model loaded: outcome "disabled" must not inflate uptime or drops.
        decisions = [_decision(outcome="disabled") for _ in range(5)]
        snapshots = [_snapshot(hour=h) for h in range(5)]
        summary = health.health_summary(snapshots, decisions, [])
        self.assertEqual(summary["llm_decisions"], 0)
        self.assertEqual(summary["llm_dropped"], 0)

    def test_dropped_rate_over_attempted_decisions(self):
        decisions = [_decision(outcome="model")] * 3 + [_decision(outcome="error", dropped=True)] * 1
        summary = health.health_summary([_snapshot()], decisions, [])
        self.assertEqual(summary["llm_decisions"], 4)
        self.assertEqual(summary["llm_dropped"], 1)
        self.assertAlmostEqual(summary["llm_dropped_rate"], 0.25)

    def test_run_color_green_amber_red(self):
        green = health.health_summary([_snapshot()], [], [])
        self.assertEqual(health.run_color(green), "green")
        amber = health.health_summary([_snapshot()], [], [{"type": "event", "kind": "x", "severity": health.WARN}])
        self.assertEqual(health.run_color(amber), "amber")
        red = health.health_summary(
            [_snapshot(avg_mood=10)], [], [{"type": "event", "kind": "good_depleted", "severity": health.CRITICAL}]
        )
        self.assertEqual(health.run_color(red), "red")


if __name__ == "__main__":
    unittest.main()
