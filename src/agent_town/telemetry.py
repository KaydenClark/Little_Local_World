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
(viewer feed) and verified after the fact (``analyze_run.py``). Every record
carries a ``run_id`` so logs from many runs can be told apart and the analyzer
can correlate them. The "is it correct?" judgement lives in ``health.py``; this
file is pure plumbing.
"""

from __future__ import annotations

import datetime
import json
import uuid
from collections import Counter, deque
from pathlib import Path
from typing import Any

from . import economy, health
from .core import BUILD1_NEEDS, FactionState

# Bump when the record schema changes in a way the analyzer must branch on.
SCHEMA_VERSION = 1


def _now_iso() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


# --- Record builders --------------------------------------------------------


def build_snapshot(state: FactionState, step_result: Any) -> dict[str, Any]:
    """The civilization's state this hour as a flat, JSON-safe record."""
    staffed: dict[str, int] = {}
    for building in state.buildings.values():
        work_type = building.recipe.skill if building.recipe else None
        if work_type:
            staffed[work_type] = staffed.get(work_type, 0) + len(building.staffed_by)
    broken_ids = health.broken_pawn_ids(state)
    broken = set(broken_ids)
    idle = sum(1 for p in state.pawns.values() if p.assignment is None and p.id not in broken)
    return {
        "type": "snapshot",
        "day": state.day,
        "hour": state.time_of_day,
        "population": len(state.pawns),
        "avg_mood": round(economy.average_mood(state), 2),
        "needs": {need: round(economy.average_need(state, need), 3) for need in BUILD1_NEEDS},
        "coin": state.coin,
        "stockpile": {good.value: count for good, count in sorted(state.stockpile.counts.items(), key=lambda kv: kv[0].value)},
        "storage": _storage_record(state),
        "idle": idle,
        "broken": len(broken_ids),
        "broken_pawn_ids": broken_ids,
        "staffed": dict(sorted(staffed.items())),
        "construction": _construction_records(state),
        "tax_collected": int(getattr(step_result, "tax_collected", 0)),
        "wages_paid": int(getattr(step_result, "wages_paid", 0)),
        "market_revenue": int(getattr(step_result, "market_revenue", 0)),
        "household_spending": int(getattr(step_result, "household_spending", 0)),
        "sales_tax_collected": int(getattr(step_result, "sales_tax_collected", 0)),
        "unmet_market_demand": int(getattr(step_result, "unmet_market_demand", 0)),
        "days_rolled": int(getattr(step_result, "days_rolled", 0)),
    }


def _construction_records(state: FactionState) -> list[dict[str, Any]]:
    sites = []
    for site in sorted(state.construction_sites.values(), key=lambda s: s.id):
        required = sum(site.required.values())
        delivered = sum(site.delivered.values())
        sites.append(
            {
                "site_id": site.id,
                "building_kind": site.building_kind,
                "progress": 1.0 if required == 0 else round(delivered / required, 3),
                "work_remaining": round(site.work_remaining, 3),
                "required": {good.value: amount for good, amount in site.required.items()},
                "delivered": {good.value: amount for good, amount in site.delivered.items()},
            }
        )
    return sites


def _storage_record(state: FactionState) -> dict[str, Any]:
    economy.refresh_storage_capacity(state)
    fullness = state.stockpile.fullness()
    return {
        "used": state.stockpile.used_capacity(),
        "capacity": state.stockpile.capacity,
        "fullness": None if fullness is None else round(fullness, 3),
    }


def _multiset_diff(proposed: list[str], applied: list[str]) -> list[str]:
    """Action kinds proposed but not applied (a rough 'rejected' view)."""
    return list((Counter(proposed) - Counter(applied)).elements())


def build_decision(state: FactionState, governor: Any, step_result: Any) -> dict[str, Any]:
    """What the governor proposed vs. what took effect, plus LLM health.

    Handles both governor paths honestly: the non-blocking scheduler exposes a
    ``status`` (``GovernorStatus``); the blocking ``LLMGovernor`` exposes a
    ``last_outcome`` (model/fallback/error/disabled). ``dropped`` marks an hour
    where a *configured* model failed and the deterministic fallback covered - a
    disabled run (no model loaded) is fallback-by-design and never "dropped".
    """
    proposed = [a.kind for a in getattr(governor, "last_actions", []) or []]
    applied = [a.kind for a in getattr(step_result, "actions_applied", ()) or ()]
    record: dict[str, Any] = {
        "type": "decision",
        "day": state.day,
        "hour": state.time_of_day,
        "governor_kind": type(getattr(governor, "inner", governor)).__name__,
        "proposed": proposed,
        "applied": applied,
        "rejected": _multiset_diff(proposed, applied),
        "buildings_completed": list(getattr(step_result, "buildings_completed", ()) or ()),
        "decide_ms": round(getattr(governor, "last_decide_ms", 0.0), 1),
        "dropped": False,
        "dropped_reason": "",
        "llm_source": "fallback",
        "llm_state": "",
        "llm_model": "",
        "llm_latency": 0.0,
        "llm_error": "",
        "outcome": "",
    }
    status = getattr(governor, "status", None)
    if status is not None:
        record["llm_source"] = "scheduler"
        record["llm_state"] = status.state
        record["llm_model"] = getattr(status, "model", "")
        record["llm_latency"] = round(getattr(status, "last_latency", 0.0), 3)
        record["llm_error"] = getattr(status, "last_error", "")
        if status.state in ("offline", "invalid"):
            record["dropped"] = True
            record["dropped_reason"] = status.last_error or status.state
        return record
    outcome = getattr(governor, "last_outcome", None)
    if outcome is not None:
        record["llm_source"] = "llm"
        record["outcome"] = outcome
        record["llm_error"] = getattr(governor, "last_error", "")
        if outcome == "error":
            record["dropped"] = True
            record["dropped_reason"] = record["llm_error"] or "model error"
        return record
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
    """Appends one JSON object per line; flushes so a live tail sees each hour.

    ``sort_keys`` keeps the JSONL stable across runs (clean diffs); append mode
    means re-using a path never silently truncates an existing log.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(self.path, "a", encoding="utf-8")

    def write(self, record: dict[str, Any]) -> None:
        self._fh.write(json.dumps(record, default=str, sort_keys=True) + "\n")
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


class _EmptyStep:
    """Stand-in StepResult for the final snapshot at run end (no hour stepped)."""

    actions_applied: tuple = ()
    buildings_completed: tuple = ()
    days_rolled = 0
    tax_collected = 0
    wages_paid = 0
    market_revenue = 0
    household_spending = 0
    sales_tax_collected = 0
    unmet_market_demand = 0


class RunLogger:
    """Orchestrates per-hour telemetry; deterministic-safe (reads state only)."""

    def __init__(self, sink: Any | None = None, *, run_id: str | None = None) -> None:
        self.sink = sink or NullSink()
        self.run_id = run_id or uuid.uuid4().hex[:12]
        self.monitor = health.EventMonitor()
        # Accumulated records, so log_run_end can embed a self-contained summary
        # without re-reading the file. ~3 records/hour - trivial for a week run.
        self.snapshots: list[dict[str, Any]] = []
        self.decisions: list[dict[str, Any]] = []
        self.events: list[dict[str, Any]] = []
        self.last_events: list[dict[str, Any]] = []
        self.last_severity: str | None = None
        self._ended = False

    def record(self, obj: dict[str, Any]) -> None:
        obj.setdefault("run_id", self.run_id)
        self.sink.write(obj)

    def log_run_start(self, state: FactionState, governor: Any, **config: Any) -> dict[str, Any]:
        inner = getattr(governor, "inner", governor)
        status = getattr(governor, "status", None)
        record = {
            "type": "run_start",
            "run_id": self.run_id,
            "schema": SCHEMA_VERSION,
            "seed": state.seed,
            "population": len(state.pawns),
            "governor": type(inner).__name__,
            "model": getattr(status, "model", "") if status is not None else "",
            "wall": _now_iso(),
            **config,
        }
        self.record(record)
        return record

    def log_hour(self, state: FactionState, step_result: Any, governor: Any) -> tuple[dict, dict, list]:
        """Emit this hour's snapshot, decision, and any anomaly events."""
        snapshot = build_snapshot(state, step_result)
        decision = build_decision(state, governor, step_result)
        violations = health.check_invariants(state)
        events = self.monitor.observe(snapshot, decision, violations)
        self.record(snapshot)
        self.record(decision)
        for event in events:
            self.record(event)
        self.snapshots.append(snapshot)
        self.decisions.append(decision)
        self.events.extend(events)
        self.last_events = events
        self.last_severity = health.max_severity(events)
        return snapshot, decision, events

    def log_run_end(self, state: FactionState, summary: dict[str, Any] | None = None) -> dict[str, Any] | None:
        if self._ended:
            return None
        if summary is None:
            summary = health.health_summary(self.snapshots, self.decisions, self.events)
        record = {
            "type": "run_end",
            "day": state.day,
            "hour": state.time_of_day,
            "coin": state.coin,
            "wall": _now_iso(),
            "final_snapshot": build_snapshot(state, _EmptyStep()),
            "summary": summary,
            "color": health.run_color(summary),
        }
        self.record(record)
        self._ended = True
        return record

    def close(self) -> None:
        self.sink.close()


# --- Governor wrapper -------------------------------------------------------


class TelemetryGovernor:
    """Pass-through wrapper that captures what a governor proposed each hour.

    Returns ``inner.decide(...)`` unchanged, so it cannot alter behavior; it only
    records the proposed actions and the decide() wall time, and transparently
    delegates everything else (``status``, ``last_outcome``, ``toggle``,
    ``shutdown``, ...) to the wrapped governor so the viewer's controls keep
    working.
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
