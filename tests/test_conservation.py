"""The conservation law, executable (Fable review E-3 / Slice C).

BLUEPRINT's "nothing from nothing" law used to exist only as prose plus a
negative-stock check. These tests pin its executable form: the stockpile
journals every inflow/outflow, ``check_invariants`` asserts
``stock == flow_in - flow_out`` per good, and a multi-day engine run must keep
the invariant list empty at every single hour - the mid-run oracle the review
found missing. The tamper tests are the negative controls proving the oracle
can actually fail: goods minted or vanished behind the journal's back are
reported, not absorbed.
"""

from __future__ import annotations

import unittest

from agent_town import civilization, engine, health
from agent_town.core import Good, Stockpile


class LedgerIdentityTests(unittest.TestCase):
    def test_seeded_civilization_journals_initial_stock(self):
        state = civilization.create_default_civilization()
        self.assertEqual(state.stockpile.flow_in.get(Good.BREAD, 0), 48)
        self.assertEqual(state.stockpile.flow_in.get(Good.WATER, 0), 24)
        self.assertEqual(health.check_invariants(state), [])

    def test_hand_built_stockpile_seeds_its_journal(self):
        stockpile = Stockpile(counts={Good.GRAIN: 10})
        self.assertEqual(stockpile.flow_in, {Good.GRAIN: 10})
        stockpile.remove(Good.GRAIN, 4)
        stockpile.add(Good.FLOUR, 2)
        self.assertEqual(stockpile.counts.get(Good.GRAIN, 0), stockpile.flow_in[Good.GRAIN] - stockpile.flow_out[Good.GRAIN])
        self.assertEqual(stockpile.counts.get(Good.FLOUR, 0), stockpile.flow_in[Good.FLOUR])

    def test_conservation_ledger_holds_10_days(self):
        """240 hours of the default civ under the fallback governor: the law
        holds at *every* hour, not just at the end - a mid-run break that later
        self-corrects must still fail this test."""
        state = civilization.create_default_civilization()
        for hour in range(240):
            engine.step_hour(state)
            violations = health.check_invariants(state)
            self.assertEqual(
                violations, [], f"invariants broken at hour {hour} (day {state.day} {state.time_of_day}:00)"
            )
        # The run must also have *produced* something, or the law held vacuously.
        self.assertGreater(sum(state.stockpile.flow_in.values()), 72)  # more than the seed stock


class LedgerTamperTests(unittest.TestCase):
    """Negative controls: the oracle must catch goods conjured or destroyed
    behind the journal's back (any path that bypasses Stockpile.add/remove)."""

    def _stepped_state(self):
        state = civilization.create_default_civilization()
        for _ in range(24):
            engine.step_hour(state)
        self.assertEqual(health.check_invariants(state), [])
        return state

    def test_ledger_catches_minted_goods(self):
        state = self._stepped_state()
        state.stockpile.counts[Good.BREAD] = state.stockpile.counts.get(Good.BREAD, 0) + 50
        violations = health.check_invariants(state)
        self.assertTrue(any("conservation" in v and "bread" in v and "minted" in v for v in violations), violations)

    def test_ledger_catches_vanished_goods(self):
        state = self._stepped_state()
        state.stockpile.counts[Good.WATER] = 0
        violations = health.check_invariants(state)
        self.assertTrue(any("conservation" in v and "water" in v and "vanished" in v for v in violations), violations)

    def test_tamper_surfaces_as_critical_event(self):
        """The break is watchable: EventMonitor turns the violation into a
        CRITICAL invariant event for the viewer feed and the analyzer."""
        state = self._stepped_state()
        state.stockpile.counts[Good.BREAD] = state.stockpile.counts.get(Good.BREAD, 0) + 50
        violations = health.check_invariants(state)
        monitor = health.EventMonitor()
        events = monitor.observe(
            {"type": "snapshot", "day": state.day, "hour": state.time_of_day, "stockpile": {}},
            {"type": "decision"},
            violations,
        )
        invariant_events = [e for e in events if e["kind"] == health.EV_INVARIANT]
        self.assertEqual(len(invariant_events), 1)
        self.assertEqual(invariant_events[0]["severity"], health.CRITICAL)


if __name__ == "__main__":
    unittest.main()
