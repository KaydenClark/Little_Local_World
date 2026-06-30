"""Civilization invariants, anomaly detection, and run-health summary.

Pure functions over state and over telemetry records - **no file I/O, no
wall-clock** - so they are safe to call from the deterministic engine boundary,
the live viewer, and the offline ``analyze_run.py`` alike. This is the "is the
run going correctly?" brain; ``telemetry.py`` is the plumbing that feeds it.

Severity is the single dial the viewer (alert colour) and the analyzer (exit
code) both read: ``INFO`` is narration, ``WARN`` is "watch this", ``CRITICAL``
is "something is wrong" (conservation broken, the food staple gone, mood
collapsed, a pawn broke down).
"""

from __future__ import annotations

from typing import Any

from . import economy
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
DROPPED_RATE_WARN = 0.25  # >1/4 of LLM decisions dropped to fallback
# The survival staple: bread under this many units (≈ <1 per pawn) is low.
BREAD_LOW_PER_PAWN = 1.0


def check_invariants(state: FactionState) -> list[str]:
    """Conservation / consistency violations. Empty list means healthy.

    Guards the "nothing from nothing" law (`BLUEPRINT.md`) and the arbiter's
    one-job-per-pawn / capacity rules: no double-staffing, no phantom staff, no
    negative stock, mood in range.
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
    for pid, pawn in state.pawns.items():
        if not (0.0 <= pawn.mood <= 100.0):
            violations.append(f"pawn {pid} mood out of range ({pawn.mood})")
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


def detect_events(
    prev: dict[str, Any] | None,
    snapshot: dict[str, Any],
    decision: dict[str, Any],
    violations: list[str],
) -> list[dict[str, Any]]:
    """Discrete anomalies for this hour, from the snapshot diff + the decision.

    ``prev`` is last hour's snapshot (None on the first hour). Pure: same inputs
    always yield the same events, so events are reproducible per run.
    """
    day = snapshot["day"]
    hour = snapshot["hour"]
    events: list[dict[str, Any]] = []

    if violations:
        events.append(
            _event(EV_INVARIANT, CRITICAL, day, hour, f"{len(violations)} invariant violation(s)", violations=violations)
        )

    # Completed buildings (info) come straight off the decision record.
    for building_id in decision.get("buildings_completed", []):
        events.append(_event(EV_BUILDING_COMPLETED, INFO, day, hour, f"Built {building_id}", building_id=building_id))

    # Mental breaks: a rising broken count.
    broken = snapshot.get("broken", 0)
    if prev is not None and broken > prev.get("broken", 0):
        events.append(_event(EV_PAWN_BREAK, CRITICAL, day, hour, f"{broken} pawn(s) on a mental break", broken=broken))

    # Events are edge-triggered (fire on the transition, not every hour the
    # condition holds) so the feed shows changes, not a per-hour drumbeat.

    # Mass idle: fire when the idle fraction crosses the threshold.
    population = max(1, snapshot.get("population", 1))
    idle = snapshot.get("idle", 0)
    prev_idle_frac = (prev or {}).get("idle", 0) / max(1, (prev or {}).get("population", population))
    if idle / population > IDLE_FRACTION_WARN >= prev_idle_frac:
        events.append(_event(EV_MASS_IDLE, WARN, day, hour, f"{idle}/{population} pawns idle with no legal job", idle=idle))

    # Food staple pressure (bread). A missing stockpile key reads as 0, so an
    # already-empty larder does not re-alarm every hour.
    bread = snapshot.get("stockpile", {}).get(Good.BREAD.value, 0)
    prev_bread = (prev or {}).get("stockpile", {}).get(Good.BREAD.value, 0)
    low = BREAD_LOW_PER_PAWN * population
    if bread <= 0 < prev_bread:
        events.append(_event(EV_GOOD_DEPLETED, CRITICAL, day, hour, "Bread depleted - pawns will go hungry", good="bread"))
    elif 0 < bread < low and not (0 < prev_bread < low):
        events.append(_event(EV_GOOD_LOW, WARN, day, hour, f"Bread low ({bread} for {population})", good="bread", amount=bread))

    # Civ mood bands (edge-triggered on crossing).
    mood = snapshot.get("avg_mood", 100.0)
    prev_mood = (prev or {}).get("avg_mood", mood)
    if mood < MOOD_COLLAPSE <= prev_mood:
        events.append(_event(EV_MOOD_COLLAPSE, CRITICAL, day, hour, f"Average mood collapsed to {mood:.0f}", mood=mood))
    elif mood < MOOD_WARN <= prev_mood:
        events.append(_event(EV_MOOD_DIP, WARN, day, hour, f"Average mood dipped to {mood:.0f}", mood=mood))

    # Governor / LLM health.
    if decision.get("dropped"):
        events.append(
            _event(EV_LLM_DROPPED, WARN, day, hour, "LLM decision dropped to fallback", reason=decision.get("llm_error") or decision.get("outcome"))
        )
    prev_offline = bool((prev or {}).get("_llm_offline"))
    offline = decision.get("llm_state") in ("offline", "invalid")
    snapshot["_llm_offline"] = offline  # carried for next-hour edge detection
    if offline and not prev_offline:
        events.append(_event(EV_LLM_OFFLINE, WARN, day, hour, "LLM governor offline - fallback covering", state=decision.get("llm_state")))
    elif prev_offline and not offline and decision.get("llm_state") == "idle":
        events.append(_event(EV_LLM_RECOVERED, INFO, day, hour, "LLM governor recovered"))

    return events


def max_severity(events: list[dict[str, Any]]) -> str | None:
    """The worst severity among ``events`` (for the viewer alert dot), or None."""
    if not events:
        return None
    return max((e.get("severity", INFO) for e in events), key=lambda s: _SEVERITY_RANK.get(s, 0))


def health_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate a whole run's records into a health report for the analyzer."""
    snapshots = [r for r in records if r.get("type") == "snapshot"]
    decisions = [r for r in records if r.get("type") == "decision"]
    events = [r for r in records if r.get("type") == "event"]

    moods = [s["avg_mood"] for s in snapshots if "avg_mood" in s]
    idles = [s.get("idle", 0) for s in snapshots]
    # An LLM "decision" only counts when a model was actually in play - a run with
    # no model loaded (state/outcome "disabled") is fallback-by-design, not dropped.
    llm_decisions = [d for d in decisions if _llm_attempted(d)]
    dropped = sum(1 for d in llm_decisions if d.get("dropped"))
    llm_ok = sum(1 for d in llm_decisions if d.get("llm_state") == "idle" or d.get("outcome") == "model")
    llm_total = max(1, len(llm_decisions))

    action_hist: dict[str, int] = {}
    for d in decisions:
        for kind in d.get("applied", []):
            action_hist[kind] = action_hist.get(kind, 0) + 1

    event_counts: dict[str, int] = {}
    for e in events:
        event_counts[e.get("kind", "?")] = event_counts.get(e.get("kind", "?"), 0) + 1

    critical = [e for e in events if e.get("severity") == CRITICAL]
    return {
        "hours": len(snapshots),
        "mood_start": moods[0] if moods else None,
        "mood_min": min(moods) if moods else None,
        "mood_end": moods[-1] if moods else None,
        "idle_peak": max(idles) if idles else 0,
        "breaks": event_counts.get(EV_PAWN_BREAK, 0),
        "depletions": event_counts.get(EV_GOOD_DEPLETED, 0),
        "llm_decisions": len(llm_decisions),
        "llm_dropped": dropped,
        "llm_dropped_rate": round(dropped / llm_total, 3),
        "llm_uptime": round(llm_ok / llm_total, 3),
        "actions": action_hist,
        "event_counts": event_counts,
        "critical_events": len(critical),
    }


def _llm_attempted(decision: dict[str, Any]) -> bool:
    """Whether a model was actually in play this hour (not disabled / not bare fallback)."""
    state = decision.get("llm_state")
    if state is not None:
        return state != "disabled"
    return decision.get("outcome") in ("model", "error", "fallback")


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
