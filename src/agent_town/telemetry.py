"""Structured run telemetry for the civilization simulation.

Telemetry is an observer at the caller boundary: it reads ``FactionState`` and
``StepResult`` after an engine hour has completed, then writes JSON-serializable
records. It deliberately does not mutate simulation state or change
``engine.step_hour``.
"""

from __future__ import annotations

import json
import time
import uuid
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol, TextIO

from . import economy, health
from .core import FactionState, GovernorAction, Good

WARN = "warn"
CRITICAL = "critical"
INFO = "info"


class Sink(Protocol):
    def record(self, obj: dict[str, Any]) -> None: ...


class NullSink:
    """No-op sink for tests and disabled telemetry."""

    def record(self, obj: dict[str, Any]) -> None:
        return


class JsonlStreamSink:
    """Write one JSON object per line to an already-open text stream."""

    def __init__(self, stream: TextIO) -> None:
        self.stream = stream

    def record(self, obj: dict[str, Any]) -> None:
        self.stream.write(json.dumps(obj, sort_keys=True) + "\n")
        self.stream.flush()


class JsonlFileSink:
    """Append JSONL records to a file and flush each record for live runs."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("w", encoding="utf-8")

    def record(self, obj: dict[str, Any]) -> None:
        self._handle.write(json.dumps(obj, sort_keys=True) + "\n")
        self._handle.flush()

    def close(self) -> None:
        self._handle.close()


class RingBufferSink:
    """In-memory record sink for the live viewer feed."""

    def __init__(self, maxlen: int = 200) -> None:
        self._records: deque[dict[str, Any]] = deque(maxlen=maxlen)

    def record(self, obj: dict[str, Any]) -> None:
        self._records.append(dict(obj))

    @property
    def records(self) -> list[dict[str, Any]]:
        return list(self._records)


class MultiSink:
    """Fan records out to multiple sinks."""

    def __init__(self, sinks: list[Sink] | tuple[Sink, ...]) -> None:
        self.sinks = tuple(sinks)

    def record(self, obj: dict[str, Any]) -> None:
        for sink in self.sinks:
            sink.record(obj)

    def close(self) -> None:
        for sink in self.sinks:
            close = getattr(sink, "close", None)
            if callable(close):
                close()


class TelemetryGovernor:
    """Pass-through governor wrapper that records proposed actions and latency."""

    def __init__(self, inner: Any, *, clock: Any = time.monotonic) -> None:
        self.inner = inner
        self.clock = clock
        self.last_actions: tuple[GovernorAction, ...] = ()
        self.last_latency = 0.0

    @property
    def status(self) -> Any:
        return getattr(self.inner, "status", None)

    def decide(self, context: dict[str, Any]) -> list[GovernorAction]:
        start = self.clock()
        actions = self.inner.decide(context)
        self.last_latency = max(0.0, self.clock() - start)
        self.last_actions = tuple(actions)
        return actions

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)


class RunLogger:
    """High-level structured logger for one simulation run."""

    def __init__(self, sink: Sink | None = None, *, run_id: str | None = None) -> None:
        self.sink = sink or NullSink()
        self.run_id = run_id or str(uuid.uuid4())
        self._previous_snapshot: dict[str, Any] | None = None
        self._last_governor_state = ""
        self.records: list[dict[str, Any]] = []
        self._ended = False

    def record(self, obj: dict[str, Any]) -> None:
        record = dict(obj)
        record.setdefault("run_id", self.run_id)
        self.records.append(record)
        self.sink.record(record)

    def log_run_start(
        self,
        state: FactionState,
        *,
        governor_kind: str,
        model: str = "",
        config: dict[str, Any] | None = None,
    ) -> None:
        self.record(
            {
                "type": "run_start",
                "run_id": self.run_id,
                "seed": state.seed,
                "governor_kind": governor_kind,
                "model": model,
                "config": config or {},
                "wall_clock_start": _wall_clock(),
            }
        )

    def log_hour(
        self,
        state: FactionState,
        step_result: Any,
        governor: Any,
        *,
        previous_snapshot: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        previous = previous_snapshot if previous_snapshot is not None else self._previous_snapshot
        snapshot = build_snapshot(state, step_result)
        decision = build_decision(state, step_result, governor)
        self.record(snapshot)
        self.record(decision)
        for event in diff_events(state, snapshot, decision, previous, self._last_governor_state):
            self.record(event)
        self._previous_snapshot = snapshot
        self._last_governor_state = str(decision.get("governor_state") or "")
        return snapshot

    def log_run_end(self, state: FactionState) -> None:
        if self._ended:
            return
        final_snapshot = build_snapshot(state, _empty_step_result())
        events = [record for record in self.records if record.get("type") == "event"]
        snapshots = [record for record in self.records if record.get("type") == "snapshot"]
        decisions = [record for record in self.records if record.get("type") == "decision"]
        self.record(
            {
                "type": "run_end",
                "wall_clock_end": _wall_clock(),
                "final_snapshot": final_snapshot,
                "totals": health.health_summary(snapshots, decisions, events),
            }
        )
        self._ended = True

    def close(self) -> None:
        close = getattr(self.sink, "close", None)
        if callable(close):
            close()


def build_snapshot(state: FactionState, step_result: Any) -> dict[str, Any]:
    """Build a per-hour state snapshot record."""
    return {
        "type": "snapshot",
        "day": state.day,
        "hour": state.time_of_day,
        "population": len(state.pawns),
        "avg_mood": round(economy.average_mood(state), 3),
        "avg_needs": _avg_needs(state),
        "coin": state.coin,
        "stockpile": {good.value: count for good, count in sorted(state.stockpile.counts.items(), key=lambda item: item[0].value)},
        "idle_count": _idle_count(state),
        "broken_count": len(health.broken_pawn_ids(state)),
        "broken_pawn_ids": health.broken_pawn_ids(state),
        "staffed_by_work_type": _staffed_by_work_type(state),
        "construction": _construction_records(state),
        "tax_collected": int(getattr(step_result, "tax_collected", 0)),
        "days_rolled": int(getattr(step_result, "days_rolled", 0)),
    }


def build_decision(state: FactionState, step_result: Any, governor: Any) -> dict[str, Any]:
    """Build a governor decision/apply record for the hour."""
    status = getattr(governor, "status", None) if governor is not None else None
    proposed_actions = tuple(getattr(governor, "last_actions", ()) or ())
    proposed_kinds = [action.kind for action in proposed_actions]
    applied_actions = tuple(getattr(step_result, "actions_applied", ()) or ())
    applied_kinds = [action.kind for action in applied_actions]
    governor_state = getattr(status, "state", "") if status is not None else ""
    dropped_reason = ""
    if governor_state in ("offline", "invalid"):
        dropped_reason = getattr(status, "last_error", "") or governor_state

    return {
        "type": "decision",
        "day": state.day,
        "hour": state.time_of_day,
        "governor_kind": type(getattr(governor, "inner", governor)).__name__ if governor is not None else "none",
        "governor_state": governor_state,
        "model": getattr(status, "model", "") if status is not None else "",
        "latency": round(float(getattr(status, "last_latency", 0.0) or getattr(governor, "last_latency", 0.0) or 0.0), 4),
        "last_error": getattr(status, "last_error", "") if status is not None else "",
        "proposed_action_kinds": proposed_kinds,
        "applied_action_kinds": applied_kinds,
        "rejected": _rejected_actions(proposed_kinds, applied_kinds),
        "dropped": bool(dropped_reason),
        "dropped_reason": dropped_reason,
        "buildings_completed": list(getattr(step_result, "buildings_completed", ()) or ()),
    }


def diff_events(
    state: FactionState,
    snapshot: dict[str, Any],
    decision: dict[str, Any],
    previous_snapshot: dict[str, Any] | None,
    previous_governor_state: str = "",
) -> list[dict[str, Any]]:
    """Build discrete anomaly/event records for this hour."""
    events: list[dict[str, Any]] = []
    day = int(snapshot["day"])
    hour = int(snapshot["hour"])

    for building_id in decision.get("buildings_completed", []):
        events.append(_event(day, hour, INFO, "building_completed", f"Completed {building_id}"))

    for violation in health.check_invariants(state):
        events.append(_event(day, hour, CRITICAL, "invariant_violation", "Invariant violation", violation))

    if decision.get("dropped"):
        reason = decision.get("dropped_reason", "decision dropped")
        events.append(_event(day, hour, WARN, "llm_decision_dropped", "LLM decision dropped", reason))

    governor_state = str(decision.get("governor_state") or "")
    if previous_governor_state in ("offline", "invalid") and governor_state == "idle":
        events.append(_event(day, hour, INFO, "llm_recovered", "Local model recovered"))

    if previous_snapshot is not None:
        events.extend(_stockpile_events(day, hour, previous_snapshot, snapshot))
        if int(snapshot.get("broken_count", 0)) > int(previous_snapshot.get("broken_count", 0)):
            events.append(_event(day, hour, CRITICAL, "pawn_break", "Pawn entered a break"))
        _append_idle_event(events, day, hour, previous_snapshot, snapshot)
        _append_mood_event(events, day, hour, previous_snapshot, snapshot)

    return events


def default_log_path(directory: str | Path = "logs") -> Path:
    """Default run-log path for scripts/viewer."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Path(directory) / f"run-{stamp}.jsonl"


def _avg_needs(state: FactionState) -> dict[str, float]:
    return {need: round(economy.average_need(state, need), 3) for need in economy.BUILD1_NEEDS}


def _idle_count(state: FactionState) -> int:
    return sum(
        1
        for pawn in state.pawns.values()
        if pawn.assignment is None and pawn.state not in ("slacking", "wandering")
    )


def _staffed_by_work_type(state: FactionState) -> dict[str, int]:
    counts: dict[str, int] = {}
    for building in state.buildings.values():
        if building.recipe is None:
            continue
        counts[building.recipe.skill] = counts.get(building.recipe.skill, 0) + len(building.staffed_by)
    return dict(sorted(counts.items()))


def _construction_records(state: FactionState) -> list[dict[str, Any]]:
    sites = []
    for site in sorted(state.construction_sites.values(), key=lambda item: item.id):
        total_required = sum(site.required.values())
        total_delivered = sum(site.delivered.values())
        progress = 1.0 if total_required == 0 else total_delivered / total_required
        sites.append(
            {
                "site_id": site.id,
                "building_kind": site.building_kind,
                "progress": round(progress, 3),
                "work_remaining": round(site.work_remaining, 3),
                "required": {good.value: amount for good, amount in site.required.items()},
                "delivered": {good.value: amount for good, amount in site.delivered.items()},
            }
        )
    return sites


def _rejected_actions(proposed_kinds: list[str], applied_kinds: list[str]) -> list[dict[str, str]]:
    remaining = list(applied_kinds)
    rejected = []
    for kind in proposed_kinds:
        if kind in remaining:
            remaining.remove(kind)
        else:
            rejected.append({"kind": kind, "reason": "not applied"})
    return rejected


def _stockpile_events(
    day: int,
    hour: int,
    previous_snapshot: dict[str, Any],
    snapshot: dict[str, Any],
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    previous = previous_snapshot.get("stockpile", {})
    current = snapshot.get("stockpile", {})
    for good in sorted(set(previous) | set(current)):
        before = int(previous.get(good, 0))
        after = int(current.get(good, 0))
        if before > 0 and after == 0:
            severity = CRITICAL if good == Good.BREAD.value else WARN
            events.append(_event(day, hour, severity, "good_depleted", f"{good} depleted", {"good": good}))
        elif 0 < after <= 2 and good == Good.BREAD.value:
            events.append(_event(day, hour, WARN, "good_low", "bread low", {"good": good, "count": after}))
    return events


def _append_idle_event(
    events: list[dict[str, Any]],
    day: int,
    hour: int,
    previous_snapshot: dict[str, Any],
    snapshot: dict[str, Any],
) -> None:
    idle = int(snapshot.get("idle_count", 0))
    previous_idle = int(previous_snapshot.get("idle_count", 0))
    population = max(1, int(snapshot.get("population", 0)))
    if idle > previous_idle and idle >= max(3, population // 3):
        events.append(_event(day, hour, WARN, "mass_idle", f"{idle} pawns idle", {"idle": idle, "population": population}))


def _append_mood_event(
    events: list[dict[str, Any]],
    day: int,
    hour: int,
    previous_snapshot: dict[str, Any],
    snapshot: dict[str, Any],
) -> None:
    previous_mood = float(previous_snapshot.get("avg_mood", 0.0))
    mood = float(snapshot.get("avg_mood", 0.0))
    if previous_mood >= health.MOOD_COLLAPSE_THRESHOLD > mood:
        events.append(_event(day, hour, CRITICAL, "mood_collapse", "Average mood collapsed", {"avg_mood": mood}))
    elif previous_mood >= health.MOOD_WARN_THRESHOLD > mood:
        events.append(_event(day, hour, WARN, "mood_dip", "Average mood dipped", {"avg_mood": mood}))


def _event(
    day: int,
    hour: int,
    severity: str,
    kind: str,
    text: str,
    detail: Any = "",
) -> dict[str, Any]:
    return {
        "type": "event",
        "day": day,
        "hour": hour,
        "severity": severity,
        "kind": kind,
        "text": text,
        "detail": detail,
    }


def _wall_clock() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _empty_step_result() -> Any:
    class Empty:
        actions_applied: tuple[GovernorAction, ...] = ()
        buildings_completed: tuple[str, ...] = ()
        days_rolled = 0
        tax_collected = 0

    return Empty()
