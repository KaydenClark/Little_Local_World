"""Governor context, exception queue, and the rule-based fallback. [Track B]

The governor sets policy only - it never moves pawns tick by tick. It reads a
compact context (faction summary + roster summary + exception queue), and emits
``GovernorAction``s that are validated against state before they mutate it.

Two governors share one ``decide(context) -> list[GovernorAction]`` interface:
``FallbackGovernor`` (deterministic greedy matcher, also the test oracle) and
the later ``LLMGovernor`` (llm.py), which falls back to it on any error.

B4 implements the context builders, action validation/application, and the
fallback governor. ``place_building`` is validated and emitted here but realised
by the engine via Track A construction at integration.
"""

from __future__ import annotations

import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from . import pawns, schedule
from .core import (
    ACTION_ASSIGN_PAWN,
    ACTION_PLACE_BUILDING,
    ACTION_SET_PRODUCTION_TARGET,
    ACTION_SET_RESEARCH,
    ACTION_SET_SCHEDULE,
    ColonyException,
    FactionState,
    Good,
    GovernorAction,
    JobRef,
)
from .llm import LLMClientError, LocalLLMClient, ModelDiscovery

# A pawn this unhappy (but not yet breaking) is flagged for the governor.
UNHAPPY_THRESHOLD = 0.4
# An assigned pawn with role skill below this is a skill mismatch.
MISMATCH_SKILL = 2

BROKEN_STATES = (pawns.STATE_SLACKING, pawns.STATE_WANDERING)
RESCHEDULE_KINDS = ("unhappy_pawn", "pawn_breaking", "pawn_break")
RESTORATIVE_SCHEDULE = "rest"
BUILD_ORDER: tuple[tuple[str, int, int], ...] = (
    ("Forester", 1, 1),
    ("Sawmill", 2, 1),
    ("Farm", 1, 3),
    ("Mill", 2, 3),
    ("Bakery", 3, 3),
    ("Quarry", 4, 1),
)


class Governor(Protocol):
    """Anything that turns a context dict into a list of policy actions."""

    def decide(self, context: dict[str, Any]) -> list[GovernorAction]: ...


def _top_skill(skills: dict[str, int]) -> list | None:
    if not skills:
        return None
    name, level = sorted(skills.items(), key=lambda kv: (-kv[1], kv[0]))[0]
    return [name, level]


def build_faction_summary(state: FactionState) -> dict[str, Any]:
    """Population, avg mood, stockpile levels, coin, day/season, tax_rate (B4)."""
    roster = list(state.pawns.values())
    population = len(roster)
    avg_mood = sum(p.mood for p in roster) / population if population else 0.0
    return {
        "population": population,
        "avg_mood": round(avg_mood, 3),
        "coin": state.coin,
        "day": state.day,
        "season": state.season,
        "time_of_day": state.time_of_day,
        "tax_rate": state.tax_rate,
        "stockpile": {good.value: count for good, count in state.stockpile.counts.items()},
    }


def build_roster_summary(state: FactionState) -> list[dict[str, Any]]:
    """Pawns with assignment plus standout skill/traits, sorted by id (B4)."""
    roster = []
    for pawn in sorted(state.pawns.values(), key=lambda p: p.id):
        assignment = pawn.assignment.building_id if pawn.assignment else None
        role = pawn.assignment.role if pawn.assignment else None
        roster.append(
            {
                "pawn_id": pawn.id,
                "name": pawn.name,
                "assignment": assignment,
                "role": role,
                "skills": dict(pawn.skills),
                "top_skill": _top_skill(pawn.skills),
                "traits": list(pawn.traits),
                "schedule": pawn.schedule,
                "mood": round(pawn.mood, 3),
                "state": pawn.state,
            }
        )
    return roster


def build_buildings_summary(state: FactionState) -> list[dict[str, Any]]:
    """Buildings with their staffing and required skill, sorted by id (B4)."""
    summary = []
    for building in sorted(state.buildings.values(), key=lambda b: b.id):
        staffed = len(building.staffed_by)
        summary.append(
            {
                "building_id": building.id,
                "kind": building.kind,
                "skill": building.recipe.skill if building.recipe else None,
                "job_slots": building.job_slots,
                "staffed": staffed,
                "open_slots": max(0, building.job_slots - staffed),
                "built": building.built,
            }
        )
    return summary


def build_construction_summary(state: FactionState) -> list[dict[str, Any]]:
    """Pending construction sites, sorted by id."""
    return [
        {
            "site_id": site.id,
            "building_kind": site.building_kind,
            "x": site.x,
            "y": site.y,
            "goods_satisfied": all(
                site.delivered.get(good, 0) >= amount for good, amount in site.required.items()
            ),
            "work_remaining": site.work_remaining,
        }
        for site in sorted(state.construction_sites.values(), key=lambda s: s.id)
    ]


def build_exception_queue(state: FactionState) -> list[ColonyException]:
    """Per-problem detail: unstaffed/missing-inputs/idle/unhappy/break/mismatch."""
    exceptions: list[ColonyException] = []

    for building in sorted(state.buildings.values(), key=lambda b: b.id):
        if not building.built or building.recipe is None:
            continue
        if building.job_slots > 0 and not building.staffed_by:
            exceptions.append(
                ColonyException("unstaffed_building", building_id=building.id, detail=building.kind)
            )
            continue
        if building.staffed_by:
            missing = sorted(
                good.value
                for good, qty in building.recipe.inputs.items()
                if state.stockpile.counts.get(good, 0) < qty
            )
            if missing:
                exceptions.append(
                    ColonyException("missing_inputs", building_id=building.id, detail=",".join(missing))
                )

    for pawn in sorted(state.pawns.values(), key=lambda p: p.id):
        broken = pawn.state in BROKEN_STATES
        if broken:
            exceptions.append(ColonyException("pawn_break", pawn_id=pawn.id, detail=pawn.state))
        elif pawn.mood < pawns.BREAK_THRESHOLD:
            exceptions.append(
                ColonyException("pawn_breaking", pawn_id=pawn.id, detail=f"mood {round(pawn.mood, 2)}")
            )
        elif pawn.mood < UNHAPPY_THRESHOLD:
            exceptions.append(
                ColonyException("unhappy_pawn", pawn_id=pawn.id, detail=f"mood {round(pawn.mood, 2)}")
            )

        if pawn.assignment is None:
            if not broken:
                exceptions.append(ColonyException("idle_pawn", pawn_id=pawn.id, detail=pawn.state))
        else:
            level = pawn.skills.get(pawn.assignment.role, 0)
            if level < MISMATCH_SKILL:
                exceptions.append(
                    ColonyException(
                        "skill_mismatch",
                        pawn_id=pawn.id,
                        building_id=pawn.assignment.building_id,
                        detail=f"{pawn.assignment.role} {level}",
                    )
                )

    return exceptions


def build_context(state: FactionState) -> dict[str, Any]:
    """Assemble summary + roster + buildings + exception queue for a governor."""
    return {
        "faction": build_faction_summary(state),
        "roster": build_roster_summary(state),
        "buildings": build_buildings_summary(state),
        "construction": build_construction_summary(state),
        "exceptions": [
            {
                "kind": exc.kind,
                "pawn_id": exc.pawn_id,
                "building_id": exc.building_id,
                "detail": exc.detail,
            }
            for exc in build_exception_queue(state)
        ],
    }


def validate_action(state: FactionState, action: GovernorAction) -> bool:
    """Whether ``action`` is legal against the current state (B4)."""
    if action.kind == ACTION_ASSIGN_PAWN:
        if action.pawn_id not in state.pawns:
            return False
        building = state.buildings.get(action.building_id)
        if building is None or not building.built or building.recipe is None:
            return False
        if len(building.staffed_by) >= building.job_slots:
            return False
        return action.pawn_id not in building.staffed_by

    if action.kind == ACTION_SET_SCHEDULE:
        if action.template not in schedule.SCHEDULE_TEMPLATES:
            return False
        return action.group == "all" or action.group in state.pawns

    if action.kind == ACTION_SET_PRODUCTION_TARGET:
        building = state.buildings.get(action.building_id)
        if building is None or not isinstance(action.good, Good):
            return False
        return action.amount is not None and action.amount >= 0

    if action.kind == ACTION_PLACE_BUILDING:
        if not action.building_kind or action.x is None or action.y is None:
            return False
        if state.grid is not None:
            return state.grid.in_bounds(action.x, action.y)
        return True

    if action.kind == ACTION_SET_RESEARCH:
        return bool(action.tech)

    return False


def apply_actions(state: FactionState, actions: list[GovernorAction]) -> list[GovernorAction]:
    """Validate then apply each action; return the ones that took effect (B4)."""
    applied: list[GovernorAction] = []
    for action in actions:
        if not validate_action(state, action):
            continue
        if action.kind == ACTION_ASSIGN_PAWN:
            building = state.buildings[action.building_id]
            building.staffed_by.append(action.pawn_id)
            state.pawns[action.pawn_id].assignment = JobRef(action.building_id, action.role)
            applied.append(action)
        elif action.kind == ACTION_SET_SCHEDULE:
            targets = (
                list(state.pawns.values())
                if action.group == "all"
                else [state.pawns[action.group]]
            )
            for pawn in targets:
                pawn.schedule = action.template
            applied.append(action)
        elif action.kind == ACTION_SET_PRODUCTION_TARGET:
            state.buildings[action.building_id].production_target[action.good] = action.amount
            applied.append(action)
        elif action.kind == ACTION_SET_RESEARCH:
            if action.tech not in state.research:
                state.research = state.research + (action.tech,)
            applied.append(action)
        elif action.kind == ACTION_PLACE_BUILDING:
            # Realized by Track A construction; returning it lets the engine do
            # that without the governor mutating construction state directly.
            applied.append(action)
    return applied


class FallbackGovernor:
    """Deterministic greedy governor: best-skill slot, restorative reschedule.

    Also the integration oracle - if a town survives N days under it, the
    economy is winnable. ``decide`` is pure: it reads context and returns
    actions without mutating state.
    """

    def decide(self, context: dict[str, Any]) -> list[GovernorAction]:
        actions: list[GovernorAction] = []
        roster = context.get("roster", [])
        buildings = context.get("buildings", [])
        construction = context.get("construction", [])
        exceptions = context.get("exceptions", [])

        # 1) Assign available pawns to their best-skill open slots.
        assignable = [
            entry
            for entry in roster
            if entry["assignment"] is None and entry["state"] not in BROKEN_STATES
        ]
        open_slots: list[tuple[str, str]] = []
        for building in buildings:
            if building["built"] and building["skill"] and building["open_slots"] > 0:
                open_slots.extend([(building["building_id"], building["skill"])] * building["open_slots"])

        used: set[str] = set()
        for building_id, skill in sorted(open_slots, key=lambda slot: slot[0]):
            candidates = [entry for entry in assignable if entry["pawn_id"] not in used]
            if not candidates:
                break
            best = sorted(candidates, key=lambda e: (-e["skills"].get(skill, 0), e["pawn_id"]))[0]
            actions.append(GovernorAction.assign_pawn(best["pawn_id"], building_id, skill))
            used.add(best["pawn_id"])

        # 2) Move unhappy / breaking pawns onto a restorative schedule.
        rescheduled: set[str] = set()
        for exc in exceptions:
            pawn_id = exc.get("pawn_id")
            if exc["kind"] in RESCHEDULE_KINDS and pawn_id and pawn_id not in rescheduled:
                actions.append(GovernorAction.set_schedule(pawn_id, RESTORATIVE_SCHEDULE))
                rescheduled.add(pawn_id)

        # 3) Ask the engine to place the next missing build-1 chain link. The
        # engine/Track A owns cost checks and construction-site realization.
        existing = {building["kind"] for building in buildings}
        pending = {site["building_kind"] for site in construction}
        for kind, x, y in BUILD_ORDER:
            if kind not in existing and kind not in pending:
                actions.append(GovernorAction.place_building(kind, x, y))
                break

        return actions


# ---------------------------------------------------------------------------
# LLM governor (integration milestone I2)
#
# Same ``decide(context) -> list[GovernorAction]`` interface as FallbackGovernor,
# backed by a local model via ``LocalLLMClient``. It asks for a JSON object of
# policy actions against a fixed schema, parses+validates them, and hard-falls
# back to FallbackGovernor on ANY error (this is why the colony exception entity
# is ``ColonyException`` and not ``Exception`` - the bare ``except Exception``
# below must stay a safety net, not catch a domain object).
# ---------------------------------------------------------------------------

COLONY_ACTION_KINDS = (
    ACTION_ASSIGN_PAWN,
    ACTION_SET_SCHEDULE,
    ACTION_PLACE_BUILDING,
    ACTION_SET_PRODUCTION_TARGET,
    ACTION_SET_RESEARCH,
)

COLONY_ACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "enum": list(COLONY_ACTION_KINDS)},
                    "pawn_id": {"type": "string"},
                    "building_id": {"type": "string"},
                    "role": {"type": "string"},
                    "group": {"type": "string"},
                    "template": {"type": "string"},
                    "building_kind": {"type": "string"},
                    "good": {"type": "string"},
                    "amount": {"type": "integer"},
                    "x": {"type": "integer"},
                    "y": {"type": "integer"},
                    "tech": {"type": "string"},
                },
                "required": ["kind"],
            },
        }
    },
    "required": ["actions"],
}

GOVERNOR_SYSTEM_PROMPT = (
    "You are the Governor of a small colony. You set POLICY only - you never move "
    "pawns yourself. Each turn you read a JSON summary of the colony and reply with "
    "a JSON object {\"actions\": [...]} of zero or more policy actions. Valid action "
    "kinds and their fields:\n"
    "- assign_pawn {pawn_id, building_id, role}: staff an idle pawn into an open "
    "building slot whose skill matches the pawn.\n"
    "- set_schedule {group, template}: group is a pawn_id or \"all\"; template is "
    "one of default, night, rest. Put unhappy or breaking pawns on rest.\n"
    "- place_building {building_kind, x, y}: queue the next missing production "
    "building.\n"
    "- set_production_target {building_id, good, amount}.\n"
    "- set_research {tech}.\n"
    "Prefer to staff idle pawns into matching open slots and to rest unhappy pawns. "
    "Reply with valid JSON only - no prose, no markdown, no chain of thought."
)


def _coerce_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def action_from_dict(data: dict[str, Any]) -> GovernorAction | None:
    """Build a GovernorAction from a raw LLM action dict, or None if unusable."""
    kind = data.get("kind")
    if kind not in COLONY_ACTION_KINDS:
        return None

    good_value = data.get("good")
    good_enum: Good | None = None
    if good_value is not None:
        try:
            good_enum = Good(str(good_value))
        except ValueError:
            good_enum = None

    return GovernorAction(
        kind=kind,
        pawn_id=_clean_str(data.get("pawn_id")),
        group=_clean_str(data.get("group")),
        building_id=_clean_str(data.get("building_id")),
        building_kind=_clean_str(data.get("building_kind")),
        role=_clean_str(data.get("role")),
        template=_clean_str(data.get("template")),
        good=good_enum,
        amount=_coerce_int(data.get("amount")),
        x=_coerce_int(data.get("x")),
        y=_coerce_int(data.get("y")),
        tech=_clean_str(data.get("tech")),
    )


def parse_action_list(payload: dict[str, Any]) -> list[GovernorAction]:
    """Parse the LLM's ``{"actions": [...]}`` object into GovernorActions."""
    raw = payload.get("actions")
    if not isinstance(raw, list):
        raise ValueError("LLM governor response must contain an 'actions' list")
    actions: list[GovernorAction] = []
    for item in raw:
        if isinstance(item, dict):
            action = action_from_dict(item)
            if action is not None:
                actions.append(action)
    return actions


def _clean_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


class LLMGovernor:
    """LLM-backed governor with a hard fallback to FallbackGovernor.

    ``decide`` asks the model for an action list; on any error - disabled client,
    timeout, bad JSON, schema miss - it returns the deterministic fallback's
    decision instead, so the colony never stalls on a flaky model. A successful
    call that yields no usable actions also defers to the fallback.
    """

    def __init__(
        self,
        client: LocalLLMClient | None = None,
        *,
        fallback: "FallbackGovernor | None" = None,
        propose: Any = None,
    ) -> None:
        self.client = client
        self.fallback = fallback or FallbackGovernor()
        # ``propose`` lets tests inject a context->payload function in place of a
        # live model call.
        self._propose = propose

    def decide(self, context: dict[str, Any]) -> list[GovernorAction]:
        try:
            payload = self._propose(context) if self._propose is not None else self._ask_model(context)
            actions = parse_action_list(payload)
        except Exception:
            return self.fallback.decide(context)
        return actions if actions else self.fallback.decide(context)

    def _ask_model(self, context: dict[str, Any]) -> dict[str, Any]:
        if self.client is None:
            raise LLMClientError("LLM governor has no client configured")
        return self.client.complete_json(
            GOVERNOR_SYSTEM_PROMPT,
            {"colony": context},
            schema=COLONY_ACTION_SCHEMA,
            name="colony_actions",
        )


# ---------------------------------------------------------------------------
# Non-blocking governor scheduler (integration milestone I2)
#
# The live colony viewer renders at 60 fps and steps the engine on a short real-
# time interval. A 4B local model takes seconds to answer, so calling it inline
# from ``step_hour`` would freeze the window. ``ColonyDecisionScheduler`` runs the
# model call on a single worker thread and implements the ``Governor`` protocol:
# each hour it harvests any finished call, may launch a new one, and returns
# either the model's freshly decided actions or - while the model is mid-thought,
# offline, or disabled - the deterministic ``FallbackGovernor``'s actions. The
# colony keeps advancing every hour and only *upgrades* to LLM policy when a
# decision is ready, so the fallback always covers the gap.
# ---------------------------------------------------------------------------

# Governor status states surfaced to the viewer HUD.
GOV_DISABLED = "disabled"
GOV_IDLE = "idle"
GOV_THINKING = "thinking"
GOV_OFFLINE = "offline"
GOV_INVALID = "invalid"

# Default real-time cooldown (seconds) between completing one model call and
# starting the next, so the viewer does not hammer the model continuously.
DEFAULT_DECISION_INTERVAL = 6.0


@dataclass
class GovernorStatus:
    """Live governor state for the viewer HUD and run logs."""

    enabled: bool
    state: str
    model: str = ""
    base_url: str = ""
    last_error: str = ""
    last_latency: float = 0.0
    last_action_kinds: tuple[str, ...] = ()


def _connection_error(message: str) -> bool:
    lowered = message.lower()
    return any(word in lowered for word in ("connection", "timed out", "refused", "unreachable", "failed"))


class ColonyDecisionScheduler:
    """Non-blocking ``Governor`` adapter that runs an LLM call off the render loop.

    Wraps a :class:`LocalLLMClient`; its :meth:`decide` never blocks on the
    network. A single worker thread holds at most one in-flight model call. When
    a call finishes, its actions are applied on the next :meth:`decide`; every
    hour in between (and whenever the model is offline or disabled) falls back to
    the deterministic :class:`FallbackGovernor`, so the colony never stalls.
    """

    def __init__(
        self,
        client: LocalLLMClient | None = None,
        *,
        fallback: "FallbackGovernor | None" = None,
        interval: float = DEFAULT_DECISION_INTERVAL,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.client = client or LocalLLMClient(model=None)
        self.fallback = fallback or FallbackGovernor()
        self.interval = max(0.0, interval)
        self.clock = clock
        self._executor = self._create_executor()
        self._future: Future[tuple[list[GovernorAction], float]] | None = None
        self._pending: list[GovernorAction] | None = None
        self._next_time = 0.0
        self.status = self._idle_status()

    @classmethod
    def from_env(
        cls,
        *,
        model_discovery: ModelDiscovery | None = None,
        interval: float = DEFAULT_DECISION_INTERVAL,
        clock: Callable[[], float] = time.monotonic,
    ) -> "ColonyDecisionScheduler":
        """Build a scheduler whose client is discovered from the environment."""
        return cls(
            LocalLLMClient.from_env(model_discovery=model_discovery),
            interval=interval,
            clock=clock,
        )

    @property
    def enabled(self) -> bool:
        return self.client.enabled

    def decide(self, context: dict[str, Any]) -> list[GovernorAction]:
        """Return this hour's actions without blocking on the model."""
        self._harvest()
        self._maybe_submit(context)
        if self._pending is not None:
            actions, self._pending = self._pending, None
            return actions
        return self.fallback.decide(context)

    def connect_from_env(self, *, model_discovery: ModelDiscovery | None = None) -> bool:
        """(Re)connect to a local model discovered from the environment."""
        client = LocalLLMClient.from_env(model_discovery=model_discovery)
        if client.enabled:
            self._replace_client(client)
            return True
        self._replace_client(
            client,
            last_error="No local chat model found. Start LM Studio, load a model, then retry.",
        )
        return False

    def disable(self, reason: str = "LLM governor off (autopilot on fallback).") -> None:
        """Drop to the deterministic fallback and cancel any in-flight call."""
        self._replace_client(LocalLLMClient(model=None), last_error=reason)

    def toggle(self, *, model_discovery: ModelDiscovery | None = None) -> bool:
        """Flip between the LLM governor and the fallback; return the new state."""
        if self.enabled:
            self.disable()
            return False
        return self.connect_from_env(model_discovery=model_discovery)

    def shutdown(self, *, wait: bool = False) -> None:
        self._executor.shutdown(wait=wait, cancel_futures=not wait)

    # -- internals ---------------------------------------------------------

    @staticmethod
    def _create_executor() -> ThreadPoolExecutor:
        return ThreadPoolExecutor(max_workers=1, thread_name_prefix="colony-llm")

    def _idle_status(self, *, last_error: str = "") -> GovernorStatus:
        return GovernorStatus(
            enabled=self.client.enabled,
            state=GOV_IDLE if self.client.enabled else GOV_DISABLED,
            model=self.client.model,
            base_url=self.client.base_url,
            last_error=last_error,
        )

    def _replace_client(self, client: LocalLLMClient, *, last_error: str = "") -> None:
        if self._future is not None:
            self._future.cancel()
            self._future = None
        self._executor.shutdown(wait=False, cancel_futures=True)
        self.client = client
        self._executor = self._create_executor()
        self._pending = None
        self._next_time = 0.0
        self.status = self._idle_status(last_error=last_error)

    def _maybe_submit(self, context: dict[str, Any]) -> None:
        if not self.client.enabled:
            self.status.enabled = False
            self.status.state = GOV_DISABLED
            return
        if self._future is not None:
            self.status.state = GOV_THINKING
            return
        if self.clock() < self._next_time:
            return
        self.status.state = GOV_THINKING
        self._future = self._executor.submit(self._decide_actions, context)

    def _harvest(self) -> None:
        if self._future is None or not self._future.done():
            return
        future, self._future = self._future, None
        self._next_time = self.clock() + self.interval
        try:
            actions, latency = future.result()
        except LLMClientError as exc:
            self.status.state = GOV_OFFLINE if _connection_error(str(exc)) else GOV_INVALID
            self.status.last_error = str(exc)
            return
        except (ValueError, TypeError, KeyError) as exc:
            self.status.state = GOV_INVALID
            self.status.last_error = str(exc)
            return
        self.status.state = GOV_IDLE
        self.status.last_error = ""
        self.status.last_latency = latency
        self.status.last_action_kinds = tuple(action.kind for action in actions)
        # An empty (or all-junk) decision defers to the fallback, matching
        # LLMGovernor: "the model chose nothing, keep the colony moving".
        self._pending = actions or None

    def _decide_actions(self, context: dict[str, Any]) -> tuple[list[GovernorAction], float]:
        """Worker-thread body: ask the model and parse its action list."""
        start = self.clock()
        payload = self.client.complete_json(
            GOVERNOR_SYSTEM_PROMPT,
            {"colony": context},
            schema=COLONY_ACTION_SCHEMA,
            name="colony_actions",
        )
        actions = parse_action_list(payload)
        return actions, self.clock() - start
