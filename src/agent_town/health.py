"""Run-health checks and summaries for civilization telemetry.

This module is pure over state/log records. It is safe for tests, the analyzer,
and the viewer to call because it never mutates the simulation.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from .core import FactionState
from . import pawns

MOOD_WARN_THRESHOLD = 35.0
MOOD_COLLAPSE_THRESHOLD = 20.0
DROPPED_RATE_RED_THRESHOLD = 0.25


def check_invariants(state: FactionState) -> list[str]:
    """Return operator-readable invariant violations for the current state."""
    violations: list[str] = []

    staffed_locations: dict[str, list[str]] = {}
    for building in state.buildings.values():
        for pawn_id in building.staffed_by:
            if pawn_id not in state.pawns:
                violations.append(f"building {building.id} staffed by unknown pawn {pawn_id}")
                continue
            staffed_locations.setdefault(pawn_id, []).append(building.id)

    for pawn_id, building_ids in sorted(staffed_locations.items()):
        if len(building_ids) > 1:
            joined = ",".join(sorted(building_ids))
            violations.append(f"pawn {pawn_id} staffed in multiple buildings: {joined}")

    for good, count in sorted(state.stockpile.counts.items(), key=lambda item: item[0].value):
        if count < 0:
            violations.append(f"negative stockpile {good.value}: {count}")

    for pawn in sorted(state.pawns.values(), key=lambda p: p.id):
        if pawn.mood < 0.0 or pawn.mood > 100.0:
            violations.append(f"pawn {pawn.id} mood out of range: {pawn.mood}")
        for need, value in sorted(pawn.needs.items()):
            if value < 0.0 or value > 1.0:
                violations.append(f"pawn {pawn.id} need out of range {need}: {value}")

    for pawn_id in sorted(state.work_decisions):
        if pawn_id not in state.pawns:
            violations.append(f"work decision for unknown pawn {pawn_id}")

    return violations


def health_summary(
    snapshots: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Aggregate the health of a run from telemetry records."""
    events = events or []
    moods = [float(snapshot.get("avg_mood", 0.0)) for snapshot in snapshots]
    idle_counts = [int(snapshot.get("idle_count", 0)) for snapshot in snapshots]
    broken_counts = [int(snapshot.get("broken_count", 0)) for snapshot in snapshots]

    action_histogram: Counter[str] = Counter()
    dropped = 0
    llm_up = 0
    for decision in decisions:
        if decision.get("dropped"):
            dropped += 1
        if decision.get("governor_state") not in ("offline", "invalid"):
            llm_up += 1
        for kind in decision.get("applied_action_kinds", []):
            action_histogram[str(kind)] += 1

    decision_count = len(decisions)
    mood_start = moods[0] if moods else 0.0
    mood_end = moods[-1] if moods else 0.0
    mood_trend = "flat"
    if mood_end < mood_start:
        mood_trend = "down"
    elif mood_end > mood_start:
        mood_trend = "up"

    return {
        "mood_start": mood_start,
        "mood_min": min(moods) if moods else 0.0,
        "mood_end": mood_end,
        "mood_trend": mood_trend,
        "idle_peak": max(idle_counts) if idle_counts else 0,
        "break_count": max(broken_counts) if broken_counts else 0,
        "good_depletion_events": sum(1 for event in events if event.get("kind") == "good_depleted"),
        "critical_good_depletion_events": sum(
            1
            for event in events
            if event.get("kind") == "good_depleted" and event.get("severity") == "critical"
        ),
        "llm_uptime_pct": round((llm_up / decision_count) * 100, 2) if decision_count else 100.0,
        "dropped_decision_count": dropped,
        "dropped_decision_rate": dropped / decision_count if decision_count else 0.0,
        "action_kind_histogram": dict(sorted(action_histogram.items())),
        "invariant_violation_count": sum(1 for event in events if event.get("kind") == "invariant_violation"),
    }


def red_conditions(summary: dict[str, Any]) -> list[str]:
    """Return analyzer-blocking health conditions."""
    problems: list[str] = []
    if int(summary.get("invariant_violation_count", 0)) > 0:
        problems.append("invariant violation")
    if int(summary.get("critical_good_depletion_events", 0)) > 0:
        problems.append("critical good depleted")
    if float(summary.get("mood_min", 100.0)) < MOOD_COLLAPSE_THRESHOLD:
        problems.append("mood collapse")
    if float(summary.get("dropped_decision_rate", 0.0)) > DROPPED_RATE_RED_THRESHOLD:
        problems.append("dropped decision rate too high")
    return problems


def broken_pawn_ids(state: FactionState) -> list[str]:
    """Stable ids of pawns currently in mental-break states."""
    return sorted(
        pawn.id
        for pawn in state.pawns.values()
        if pawn.state in (pawns.STATE_SLACKING, pawns.STATE_WANDERING)
    )
