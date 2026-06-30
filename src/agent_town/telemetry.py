"""Run-log telemetry: structured records of what the civilization actually did.

This is an **observer at the hour boundary**, called by the viewer and the
headless runner *after* each ``engine.step_hour``. It reads ``state`` +
``StepResult`` + governor status and emits JSON records (snapshot, decision,
event) to one or more sinks. It never feeds back into sim logic, so logging
on/off cannot change the simulation. Wall-clock time appears only in the
``run_start``/``run_end`` records emitted here at the I/O boundary; every other
record is keyed by sim-time ``(day, hour)``.

Why this exists: the LM Studio server log shows what the *model* sent but nothing
about the *civilization* (mood, coin, staffing, idle, dropped decisions,
conservation). This module is our own record so a run can be monitored live
(viewer feed) and verified after the fact (``analyze_run.py``). The "is it
correct?" judgement lives in ``health.py``.
"""

from __future__ import annotations

import datetime
import json
from collections import Counter, deque
from pathlib import Path
from typing import Any

from . import economy, governor as governor_mod, health
from .core import BUILD1_NEEDS, FactionState
from .pawns import STATE_SLACKING, STATE_WANDERING


def _now_iso() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


# --- Record builders --------------------------------------------------------


def build_snapshot(state: FactionState, step_result) -> dict[str, Any]:
    """The civilization's state this hour as a flat, JSON-safe record."""
    staffed: dict[str, int] = {}
    for building in state.buildings.values():
        work_type = building.recipe.skill if building.recipe else None
        if work_type:
            staffed[work_type] = staffed.get(work_type, 0) + len(building.staffed_by)
    pawns = state.pawns.values()
    idle = sum(1 for p in pawns if p.assignment is None and p.state not in (STATE_SLACKING, STATE_WANDERING))
    broken = sum(1 for p in pawns if p.state in (STATE_SLACKING, STATE_WANDERING))
    return {
        "type": "snapshot",
        "day": state.day,
        "hour": state.time_of_day,
        "population": len(state.pawns),
        "avg_mood": round(economy.average_mood(state), 2),
        "needs": {need: round(economy.average_need(state, need), 3) for need in BUILD1_NEEDS},
        "coin": state.coin,
        "stockpile": {good.value: count for good, count in state.stockpile.counts.items()},
        "idle": idle,
        "broken": broken,
        "staffed": staffed,
        "construction": len(state.construction_sites),
        "tax_collected": step_result.tax_collected,
        "days_rolled": step_result.days_rolled,
    }


def _multiset_diff(proposed: list[str], applied: list[str]) -> list[str]:
    """Action kinds proposed but not applied (a rough 'rejected' view)."""
    return list((Counter(proposed) - Counter(applied)).elements())


def build_decision(governor: Any, step_result) -> dict[str, Any]:
    """What the governor proposed vs. what took effect, plus LLM health.

    Reads ``governor.last_actions`` (set by :class:`TelemetryGovernor`) and, when
    present, ``governor.status`` (the scheduler's :class:`GovernorStatus`) or
    ``governor.last_outcome`` (the blocking ``LLMGovernor``). ``dropped`` marks an
    hour where the LLM failed and the deterministic fallback covered.
    """
    proposed = [a.kind for a in getattr(governor, "last_actions", []) or []]
    applied = [a.kind for a in step_result.actions_applied]
    record: dict[str, Any] = {
        "type": "decision",
        "proposed": proposed,
        "applied": applied,
        "rejected": _multiset_diff(proposed, applied),
        "buildings_completed": list(step_result.buildings_completed),
        "decide_ms": round(getattr(governor, "last_decide_ms", 0.0), 1),
        "dropped": False,
    }
    status = getattr(governor, "status", None)
    if status is not None:
        record["governor_kind"] = "scheduler"
        record["llm_state"] = status.state
        record["llm_model"] = status.model
        record["llm_latency"] = round(status.last_latency, 2)
        record["llm_error"] = status.last_error
        record["dropped"] = status.state in (governor_mod.GOV_OFFLINE, governor_mod.GOV_INVALID)
        return record
    outcome = getattr(governor, "last_outcome", None)
    if outcome is not None:
        record["governor_kind"] = "llm"
        record["outcome"] = outcome
        record["llm_error"] = getattr(governor, "last_error", "")
        record["dropped"] = outcome == "error"
        return record
    record["governor_kind"] = "fallback"
    return record


# --- Sinks ------------------------------------------------------------------


class NullSink:
    """Drops every record (the default, zero-cost path)."""

    def write(self, record: dict[str, Any]) -> None:  # noqa: D401
        pass

    def close(self) -> None:
        pass


class RingBufferSink:
    """Keeps the last ``maxlen`` records in memory for the live viewer feed.

    Optionally filters to certain record ``types`` (e.g. just ``event``s) so the
    in-game feed spans more history without snapshot/decision noise.
    """

    def __init__(self, maxlen: int = 200, types: set[str] | None = None) -> None:
        self.records: deque[dict[str, Any]] = deque(maxlen=maxlen)
        self.types = set(types) if types else None

    def write(self, record: dict[str, Any]) -> None:
        if self.types is None or record.get("type") in self.types:
            self.records.append(record)

    def close(self) -> None:
        pass


class JsonlFileSink:
    """Appends one JSON object per line; flushes so a live tail sees each hour."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(self.path, "a", encoding="utf-8")

    def write(self, record: dict[str, Any]) -> None:
        self._fh.write(json.dumps(record, default=str) + "\n")
        self._fh.flush()

    def close(self) -> None:
        try:
            self._fh.close()
        except Exception:
            pass


class MultiSink:
    """Fans one record out to several sinks (e.g. file + ring buffer)."""

    def __init__(self, sinks: list[Any]) -> None:
        self.sinks = list(sinks)

    def write(self, record: dict[str, Any]) -> None:
        for sink in self.sinks:
            sink.write(record)

    def close(self) -> None:
        for sink in self.sinks:
            sink.close()


# --- The logger -------------------------------------------------------------


class RunLogger:
    """Orchestrates per-hour telemetry; deterministic-safe (reads state only)."""

    def __init__(self, sink: Any | None = None) -> None:
        self.sink = sink or NullSink()
        self._prev_snapshot: dict[str, Any] | None = None
        self.last_events: list[dict[str, Any]] = []
        self.last_severity: str | None = None

    def record(self, obj: dict[str, Any]) -> None:
        self.sink.write(obj)

    def log_run_start(self, state: FactionState, governor: Any, **config: Any) -> dict[str, Any]:
        inner = getattr(governor, "inner", governor)
        record = {
            "type": "run_start",
            "seed": state.seed,
            "population": len(state.pawns),
            "governor": type(inner).__name__,
            "wall": _now_iso(),
            **config,
        }
        self.record(record)
        return record

    def log_hour(self, state: FactionState, step_result, governor: Any) -> tuple[dict, dict, list]:
        """Emit this hour's snapshot, decision, and any anomaly events."""
        snapshot = build_snapshot(state, step_result)
        decision = build_decision(governor, step_result)
        violations = health.check_invariants(state)
        events = health.detect_events(self._prev_snapshot, snapshot, decision, violations)
        self.record(snapshot)
        self.record(decision)
        for event in events:
            self.record(event)
        self._prev_snapshot = snapshot
        self.last_events = events
        self.last_severity = health.max_severity(events)
        return snapshot, decision, events

    def log_run_end(self, state: FactionState, summary: dict[str, Any] | None = None) -> dict[str, Any]:
        record = {
            "type": "run_end",
            "day": state.day,
            "hour": state.time_of_day,
            "coin": state.coin,
            "wall": _now_iso(),
        }
        if summary is not None:
            record["summary"] = summary
        self.record(record)
        return record

    def close(self) -> None:
        self.sink.close()


# --- Governor wrapper -------------------------------------------------------


class TelemetryGovernor:
    """Pass-through wrapper that captures what a governor proposed each hour.

    Returns ``inner.decide(...)`` unchanged, so it cannot alter behavior; it only
    records the proposed actions and the decide() wall time, and transparently
    delegates everything else (``status``, ``toggle``, ``shutdown``, ...) to the
    wrapped governor so the viewer's controls keep working.
    """

    def __init__(self, inner: Any) -> None:
        self.inner = inner
        self.last_actions: list[Any] = []
        self.last_decide_ms: float = 0.0

    def decide(self, context: dict[str, Any]) -> list[Any]:
        import time

        start = time.perf_counter()
        actions = self.inner.decide(context)
        self.last_decide_ms = (time.perf_counter() - start) * 1000.0
        self.last_actions = list(actions)
        return actions

    @property
    def status(self) -> Any:
        return getattr(self.inner, "status", None)

    @property
    def last_outcome(self) -> Any:
        return getattr(self.inner, "last_outcome", None)

    def __getattr__(self, name: str) -> Any:
        if name == "inner":
            raise AttributeError(name)
        return getattr(self.inner, name)


def default_run_log_path(directory: str | Path = "logs", *, prefix: str = "run") -> Path:
    """A timestamped JSONL path under ``directory`` (created on demand)."""
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    return Path(directory) / f"{prefix}-{stamp}.jsonl"
