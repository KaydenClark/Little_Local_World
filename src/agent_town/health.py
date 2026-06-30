"""Civilization invariants, anomaly detection, and run-health summary.

Pure logic over state and over telemetry records - **no file I/O, no wall-clock**
- so it is safe to call from the deterministic engine boundary, the live viewer,
and the offline ``analyze_run.py`` alike. This is the "is the run going
correctly?" brain; ``telemetry.py`` is the plumbing that feeds it.

Severity is the single dial the viewer (alert colour) and the analyzer (exit
code) both read: ``INFO`` is narration, ``WARN`` is "watch this", ``CRITICAL``
is "something is wrong" (conservation broken, the food staple gone, mood
collapsed, a pawn broke down).

Event detection is **stateful and debounced**, owned by :class:`EventMonitor`.
The lesson from the first live week-proof run was that edge-triggering on every
"good hit zero" turns the *intermediate* goods (grain, flour) - which naturally
cycle through zero each production tick - into a wall of false alarms that buries
the one alert that matters (bread). So depletion is classified: the survival
*staple* alarms immediately and once; *intermediate* goods only alarm when they
stay empty for a sustained stretch (a stalled supply chain), and every recurring
condition re-arms only after it recovers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .core import FactionState, Good
from .pawns import BREAK_MINOR, STATE_SLACKING, STATE_WANDERING

# --- Severities -------------------------------------------------------------
INFO = "info"
WARN = "warn"
CRITICAL = "critical"
_SEVERITY_RANK = {INFO: 0, WARN: 1, CRITICAL: 2}

# --- Event kinds ------------------------------------------------------------
EV_BUILDING_COMPLETED = "building_completed"
EV_PAWN_BREAK = "pawn_break"
EV_MASS_IDLE = "mass_idle"
EV_GOOD_DEPLETED = "good_depleted"
EV_GOOD_LOW = "good_low"
EV_GOOD_STALLED = "good_stalled"
EV_MOOD_DIP = "mood_dip"
EV_MOOD_COLLAPSE = "mood_collapse"
EV_LLM_DROPPED = "llm_decision_dropped"
EV_LLM_OFFLINE = "llm_offline"
EV_LLM_RECOVERED = "llm_recovered"
EV_INVARIANT = "invariant_violation"

# --- Thresholds (shared by the live panel and the analyzer) -----------------
MOOD_WARN = 45.0  # civ-average mood below this is a dip
MOOD_COLLAPSE = BREAK_MINOR  # 35.0: at/below the minor break band, breaks spread
IDLE_FRACTION_WARN = 0.34  # >1/3 of pawns idle with no legal job
DROPPED_RATE_WARN = 0.25  # >1/4 of *attempted* LLM decisions dropped to fallback
# The survival staple: bread under this many units (~ <1 per pawn) is low.
BREAD_LOW_PER_PAWN = 1.0
# An intermediate good empty this many consecutive hours is a stalled supply
# chain (mill/farm stuck), not the normal produce-then-consume churn.
SUSTAINED_ZERO_HOURS = 12

# Goods whose depletion is a survival emergency (alarmed immediately + once).
# Everything else is an intermediate that cycles through zero by design.
STAPLE_GOODS: frozenset[str] = frozenset({Good.BREAD.value})

# Intermediates can sit at zero because the downstream building consumes them
# immediately. Treat the chain as healthy while the downstream buffer exists.
DOWNSTREAM_BUFFERS: dict[str, tuple[str, ...]] = {
    Good.LOGS.value: (Good.PLANKS.value,),
    Good.GRAIN.value: (Good.FLOUR.value, Good.BREAD.value),
    Good.FLOUR.value: (Good.BREAD.value,),
}

# Governor states that mean the local model is not answering (kept as literals so
# this module stays decoupled from governor.py; they mirror GOV_OFFLINE/INVALID).
_GOV_OFFLINE_STATES = ("offline", "invalid")
_GOV_IDLE = "idle"

_BAND_RANK = {"ok": 0, "warn": 1, "collapse": 2}


def check_invariants(state: FactionState) -> list[str]:
    """Conservation / consistency violations. Empty list means healthy.

    Guards the "nothing from nothing" law (``BLUEPRINT.md``) and the arbiter's
    one-job-per-pawn / capacity rules: no double-staffing, no phantom staff, no
    over-staffing, no negative stock, mood/needs in range, no stale work trace.
    """
    violations: list[str] = []
    staffed_in: dict[str, int] = {}
    for building in state.buildings.values():
        ids = building.staffed_by
        if len(ids) != len(set(ids)):
            violations.append(f"{building.id}: duplicate staff entries {ids}")
        if len(ids) > building.job_slots:
            violations.append(f"{building.id}: overstaffed {len(ids)}/{building.job_slots}")
        for pid in ids:
            if pid not in state.pawns:
                violations.append(f"{building.id}: staffs unknown pawn {pid!r}")
            staffed_in[pid] = staffed_in.get(pid, 0) + 1
    for pid, count in sorted(staffed_in.items()):
        if count > 1:
            violations.append(f"pawn {pid} staffed in {count} buildings at once")
    for good, count in state.stockpile.counts.items():
        if count < 0:
            violations.append(f"stockpile {good.value} is negative ({count})")
    for pid, pawn in sorted(state.pawns.items()):
        if not (0.0 <= pawn.mood <= 100.0):
            violations.append(f"pawn {pid} mood out of range ({pawn.mood})")
        for need, value in sorted(pawn.needs.items()):
            if not (0.0 <= value <= 1.0):
                violations.append(f"pawn {pid} need {need} out of range ({value})")
    for pid in sorted(state.work_decisions):
        if pid not in state.pawns:
            violations.append(f"work decision for unknown pawn {pid}")
    return violations


def _event(kind: str, severity: str, day: int, hour: int, text: str, **detail: Any) -> dict[str, Any]:
    return {
        "type": "event",
        "kind": kind,
        "severity": severity,
        "day": day,
        "hour": hour,
        "text": text,
        "detail": detail,
    }


@dataclass
class EventMonitor:
    """Stateful, debounced anomaly detector fed one snapshot+decision per hour.

    Holding state (zero-streaks, edge latches, the current mood band) here keeps
    the persisted records clean - the previous design stashed flags onto the
    snapshot dict, which leaked internal fields into the log. Each recurring
    condition fires once on the worsening transition and only re-arms after it
    recovers, so the feed shows *changes*, not a per-hour drumbeat.
    """

    prev: dict[str, Any] | None = None
    zero_streaks: dict[str, int] = field(default_factory=dict)
    depleted_alarmed: set[str] = field(default_factory=set)  # staples currently flagged empty
    stalled_alarmed: set[str] = field(default_factory=set)  # intermediates flagged sustained-zero
    bread_low_armed: bool = True
    llm_offline: bool = False
    idle_high: bool = False
    mood_band: str = "ok"

    def observe(
        self,
        snapshot: dict[str, Any],
        decision: dict[str, Any],
        violations: list[str],
    ) -> list[dict[str, Any]]:
        """Discrete anomaly events for this hour; advances internal latches."""
        day = snapshot["day"]
        hour = snapshot["hour"]
        events: list[dict[str, Any]] = []

        if violations:
            events.append(
                _event(EV_INVARIANT, CRITICAL, day, hour, f"{len(violations)} invariant violation(s)", violations=violations)
            )

        for building_id in decision.get("buildings_completed", []):
            events.append(_event(EV_BUILDING_COMPLETED, INFO, day, hour, f"Built {building_id}", building_id=building_id))

        broken = snapshot.get("broken", 0)
        if self.prev is not None and broken > self.prev.get("broken", 0):
            events.append(
                _event(
                    EV_PAWN_BREAK, CRITICAL, day, hour,
                    f"{broken} pawn(s) on a mental break",
                    broken=broken, pawn_ids=snapshot.get("broken_pawn_ids", []),
                )
            )

        self._mass_idle(events, day, hour, snapshot)
        self._stockpile(events, day, hour, snapshot)
        self._mood(events, day, hour, snapshot)
        self._llm(events, day, hour, decision)

        self.prev = snapshot
        return events

    def _mass_idle(self, events: list[dict], day: int, hour: int, snapshot: dict) -> None:
        population = max(1, snapshot.get("population", 1))
        idle = snapshot.get("idle", 0)
        idle_frac = idle / population
        if idle_frac > IDLE_FRACTION_WARN and not self.idle_high:
            self.idle_high = True
            events.append(_event(EV_MASS_IDLE, WARN, day, hour, f"{idle}/{population} pawns idle with no legal job", idle=idle, population=population))
        elif idle_frac <= IDLE_FRACTION_WARN:
            self.idle_high = False

    def _stockpile(self, events: list[dict], day: int, hour: int, snapshot: dict) -> None:
        stock = snapshot.get("stockpile", {})
        population = max(1, snapshot.get("population", 1))
        for good in sorted(set(self.zero_streaks) | set(stock)):
            count = int(stock.get(good, 0))
            self.zero_streaks[good] = self.zero_streaks.get(good, 0) + 1 if count <= 0 else 0
            if good in STAPLE_GOODS:
                # Staple: immediate CRITICAL on depletion, latched, re-arm on refill.
                if count <= 0 and good not in self.depleted_alarmed:
                    self.depleted_alarmed.add(good)
                    events.append(_event(EV_GOOD_DEPLETED, CRITICAL, day, hour, f"{good.capitalize()} depleted - pawns will go hungry", good=good))
                elif count > 0:
                    self.depleted_alarmed.discard(good)
            else:
                # Intermediate: only a *sustained* empty stretch is worth a WARN.
                if count <= 0 and _has_downstream_buffer(stock, good):
                    self.zero_streaks[good] = 0
                    self.stalled_alarmed.discard(good)
                elif self.zero_streaks[good] >= SUSTAINED_ZERO_HOURS and good not in self.stalled_alarmed:
                    self.stalled_alarmed.add(good)
                    events.append(_event(EV_GOOD_STALLED, WARN, day, hour, f"{good.capitalize()} empty {self.zero_streaks[good]}h - supply chain stalled", good=good, hours=self.zero_streaks[good]))
                elif count > 0:
                    self.stalled_alarmed.discard(good)
        # Bread running low (staple, above zero), latched and re-armed above the line.
        bread = int(stock.get(Good.BREAD.value, 0))
        low = BREAD_LOW_PER_PAWN * population
        if 0 < bread < low and self.bread_low_armed:
            self.bread_low_armed = False
            events.append(_event(EV_GOOD_LOW, WARN, day, hour, f"Bread low ({bread} for {population})", good="bread", amount=bread))
        elif bread >= low:
            self.bread_low_armed = True

    def _mood(self, events: list[dict], day: int, hour: int, snapshot: dict) -> None:
        mood = snapshot.get("avg_mood", 100.0)
        band = "collapse" if mood < MOOD_COLLAPSE else "warn" if mood < MOOD_WARN else "ok"
        if _BAND_RANK[band] > _BAND_RANK[self.mood_band]:
            if band == "collapse":
                events.append(_event(EV_MOOD_COLLAPSE, CRITICAL, day, hour, f"Average mood collapsed to {mood:.0f}", mood=round(mood, 1)))
            else:
                events.append(_event(EV_MOOD_DIP, WARN, day, hour, f"Average mood dipped to {mood:.0f}", mood=round(mood, 1)))
        self.mood_band = band

    def _llm(self, events: list[dict], day: int, hour: int, decision: dict) -> None:
        if decision.get("dropped"):
            reason = decision.get("dropped_reason") or decision.get("llm_error") or decision.get("outcome") or "decision dropped"
            events.append(_event(EV_LLM_DROPPED, WARN, day, hour, "LLM decision dropped to fallback", reason=reason))
        offline = decision.get("llm_state") in _GOV_OFFLINE_STATES or decision.get("outcome") == "error"
        recovered = decision.get("llm_state") == _GOV_IDLE or decision.get("outcome") == "model"
        if offline and not self.llm_offline:
            self.llm_offline = True
            events.append(_event(EV_LLM_OFFLINE, WARN, day, hour, "LLM governor offline - fallback covering", state=decision.get("llm_state") or decision.get("outcome")))
        elif self.llm_offline and not offline and recovered:
            self.llm_offline = False
            events.append(_event(EV_LLM_RECOVERED, INFO, day, hour, "LLM governor recovered"))


def _has_downstream_buffer(stock: dict[str, Any], good: str) -> bool:
    return any(int(stock.get(buffer, 0)) > 0 for buffer in DOWNSTREAM_BUFFERS.get(good, ()))


def max_severity(events: list[dict[str, Any]]) -> str | None:
    """The worst severity among ``events`` (for the viewer alert dot), or None."""
    if not events:
        return None
    return max((e.get("severity", INFO) for e in events), key=lambda s: _SEVERITY_RANK.get(s, 0))


def _trend(start: float | None, end: float | None) -> str:
    if start is None or end is None:
        return "flat"
    if end < start:
        return "down"
    if end > start:
        return "up"
    return "flat"


def health_summary(
    snapshots: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Aggregate a whole run's records into a health report for the analyzer."""
    events = events or []
    moods = [s["avg_mood"] for s in snapshots if "avg_mood" in s]
    idles = [s.get("idle", 0) for s in snapshots]
    brokens = [s.get("broken", 0) for s in snapshots]

    # An LLM "decision" only counts when a model was actually in play - a run with
    # no model loaded (disabled) is fallback-by-design, not dropped, and must not
    # inflate uptime or pad the dropped-rate denominator.
    llm_decisions = [d for d in decisions if _llm_attempted(d)]
    dropped = sum(1 for d in llm_decisions if d.get("dropped"))
    llm_ok = sum(1 for d in llm_decisions if d.get("llm_state") == _GOV_IDLE or d.get("outcome") == "model")
    llm_total = max(1, len(llm_decisions))

    action_hist: dict[str, int] = {}
    for d in decisions:
        for kind in d.get("applied", []):
            action_hist[kind] = action_hist.get(kind, 0) + 1

    event_counts: dict[str, int] = {}
    for e in events:
        event_counts[e.get("kind", "?")] = event_counts.get(e.get("kind", "?"), 0) + 1

    critical = sum(1 for e in events if e.get("severity") == CRITICAL)
    warn = sum(1 for e in events if e.get("severity") == WARN)
    mood_start = moods[0] if moods else None
    mood_end = moods[-1] if moods else None
    return {
        "hours": len(snapshots),
        "mood_start": mood_start,
        "mood_min": min(moods) if moods else None,
        "mood_end": mood_end,
        "mood_trend": _trend(mood_start, mood_end),
        "idle_peak": max(idles) if idles else 0,
        "break_peak": max(brokens) if brokens else 0,
        "breaks": event_counts.get(EV_PAWN_BREAK, 0),
        "depletions": event_counts.get(EV_GOOD_DEPLETED, 0),
        "stalls": event_counts.get(EV_GOOD_STALLED, 0),
        "llm_decisions": len(llm_decisions),
        "llm_dropped": dropped,
        "llm_dropped_rate": round(dropped / llm_total, 3),
        "llm_uptime": round(llm_ok / llm_total, 3),
        "actions": dict(sorted(action_hist.items())),
        "event_counts": dict(sorted(event_counts.items())),
        "critical_events": critical,
        "warn_events": warn,
    }


def _llm_attempted(decision: dict[str, Any]) -> bool:
    """Whether a model was actually in play this hour (not disabled / bare fallback)."""
    state = decision.get("llm_state")
    if state:
        return state != "disabled"
    outcome = decision.get("outcome")
    return outcome in ("model", "error", "fallback")


def run_problems(summary: dict[str, Any]) -> list[str]:
    """Red conditions that should fail a run (analyzer exit code)."""
    problems: list[str] = []
    if summary.get("critical_events"):
        problems.append(f"{summary['critical_events']} critical event(s)")
    if summary.get("depletions"):
        problems.append(f"food staple depleted {summary['depletions']}x")
    mood_min = summary.get("mood_min")
    if mood_min is not None and mood_min < MOOD_COLLAPSE:
        problems.append(f"mood collapsed to {mood_min:.0f} (< {MOOD_COLLAPSE:.0f})")
    if summary.get("llm_decisions") and summary.get("llm_dropped_rate", 0) > DROPPED_RATE_WARN:
        problems.append(f"LLM dropped-decision rate {summary['llm_dropped_rate']:.0%} (> {DROPPED_RATE_WARN:.0%})")
    return problems


def run_color(summary: dict[str, Any]) -> str:
    """Run-level health light: ``red`` (any red condition), ``amber`` (warn-level
    activity), or ``green`` (clean). A first-class field an autopilot or notifier
    can poll without re-deriving the rules."""
    if run_problems(summary):
        return "red"
    if summary.get("warn_events"):
        return "amber"
    return "green"


def broken_pawn_ids(state: FactionState) -> list[str]:
    """Stable ids of pawns currently in mental-break states."""
    return sorted(
        pawn.id
        for pawn in state.pawns.values()
        if pawn.state in (STATE_SLACKING, STATE_WANDERING)
    )
