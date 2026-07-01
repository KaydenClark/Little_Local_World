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

from . import economy, pawns, schedule, work
from .core import (
    ACTION_ASSIGN_PAWN,
    ACTION_PLACE_BUILDING,
    ACTION_SET_PRODUCTION_TARGET,
    ACTION_SET_RESEARCH,
    ACTION_SET_SCHEDULE,
    ACTION_SET_WORK_PRIORITY,
    CivilizationException,
    FactionState,
    Good,
    GovernorAction,
    JobRef,
    NEED_FOOD,
    NEED_WATER,
)
from .llm import LLMClientError, LocalLLMClient, ModelDiscovery

# A pawn this unhappy (but not yet in a break band) is flagged for the governor.
# On the 0-100 mood scale, just above the minor break band (35).
UNHAPPY_THRESHOLD = 45.0
# An assigned pawn with role skill below this is a skill mismatch.
MISMATCH_SKILL = 2
LOW_WATER_COVER_DAYS = 1.0
LOW_WATER_NEED = 0.35
WATER_BUILDING_KIND = "Water Well"
WATER_BUILD_LOCATION = (5, 5)
# Food shortage signal. The default economy runs a thin *finished-bread* buffer
# (production is just-in-time), so a buffer-days trigger would cry wolf at every
# game start; average nutrition (saturation) is the honest "pawns are actually
# going hungry" signal. ``low_food`` fires when the civ is genuinely almost out of
# bread OR the average pawn is under half-fed - the floor+carry runway keeps that
# recoverable, so it is still early enough for the governor to grow more.
LOW_FOOD_COVER_DAYS = 0.5
LOW_FOOD_NEED = 0.5

BROKEN_STATES = (pawns.STATE_SLACKING, pawns.STATE_WANDERING)
RESCHEDULE_KINDS = ("unhappy_pawn", "pawn_breaking", "pawn_break")
RESTORATIVE_SCHEDULE = "rest"
ESSENTIAL_WORK_TYPES = frozenset(("water", "farming", "milling", "baking"))
LOWEST_SAFE_MODEL_ESSENTIAL_PRIORITY = 2
BUILD_ORDER: tuple[tuple[str, int, int], ...] = (
    ("Forester", 1, 1),
    ("Sawmill", 2, 1),
    ("Farm", 1, 3),
    ("Mill", 2, 3),
    ("Bakery", 3, 3),
    (WATER_BUILDING_KIND, WATER_BUILD_LOCATION[0], WATER_BUILD_LOCATION[1]),
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
        "water_days_of_cover": round(economy.water_days_of_cover(state), 3),
        "food_days_of_cover": round(economy.food_days_of_cover(state), 3),
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


def build_exception_queue(state: FactionState) -> list[CivilizationException]:
    """Per-problem detail: unstaffed/missing-inputs/idle/unhappy/break/mismatch."""
    exceptions: list[CivilizationException] = []

    for building in sorted(state.buildings.values(), key=lambda b: b.id):
        if not building.built or building.recipe is None:
            continue
        if building.job_slots > 0 and not building.staffed_by:
            exceptions.append(
                CivilizationException("unstaffed_building", building_id=building.id, detail=building.kind)
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
                    CivilizationException("missing_inputs", building_id=building.id, detail=",".join(missing))
                )

    if state.pawns:
        food_cover = economy.food_days_of_cover(state)
        food_need = economy.average_need(state, NEED_FOOD)
        if food_cover < LOW_FOOD_COVER_DAYS or food_need < LOW_FOOD_NEED:
            exceptions.append(
                CivilizationException(
                    "low_food",
                    detail=f"{round(food_cover, 2)} days cover, {round(food_need * 100)}% need",
                )
            )

        water_cover = economy.water_days_of_cover(state)
        water_need = economy.average_need(state, NEED_WATER)
        if water_cover < LOW_WATER_COVER_DAYS or water_need < LOW_WATER_NEED:
            exceptions.append(
                CivilizationException(
                    "low_water",
                    detail=f"{round(water_cover, 2)} days cover, {round(water_need * 100)}% need",
                )
            )

    for pawn in sorted(state.pawns.values(), key=lambda p: p.id):
        broken = pawn.state in BROKEN_STATES
        if broken:
            exceptions.append(CivilizationException("pawn_break", pawn_id=pawn.id, detail=pawn.state))
        elif pawn.mood < pawns.BREAK_MINOR:
            exceptions.append(
                CivilizationException("pawn_breaking", pawn_id=pawn.id, detail=f"mood {round(pawn.mood, 2)}")
            )
        elif pawn.mood < UNHAPPY_THRESHOLD:
            exceptions.append(
                CivilizationException("unhappy_pawn", pawn_id=pawn.id, detail=f"mood {round(pawn.mood, 2)}")
            )

        if pawn.assignment is None:
            if not broken:
                exceptions.append(CivilizationException("idle_pawn", pawn_id=pawn.id, detail=pawn.state))
        else:
            level = pawn.skills.get(pawn.assignment.role, 0)
            if level < MISMATCH_SKILL:
                exceptions.append(
                    CivilizationException(
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

    if action.kind == ACTION_SET_WORK_PRIORITY:
        if not action.work_type or action.level is None:
            return False
        if action.level < 0 or action.level > 4:
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
            # assign_pawn is now the forced override (the arbiter's top lane): pin
            # the pawn here so the work arbiter keeps it instead of reassigning.
            pawn = state.pawns[action.pawn_id]
            pawn.assignment = JobRef(action.building_id, action.role)
            pawn.forced_assignment = JobRef(action.building_id, action.role)
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
        elif action.kind == ACTION_SET_WORK_PRIORITY:
            targets = (
                list(state.pawns.values())
                if action.group == "all"
                else [state.pawns[action.group]]
            )
            for pawn in targets:
                work.set_priority(pawn, action.work_type, action.level)
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
    """Deterministic policy governor: restorative reschedule, next-building.

    Build 2 moved routine staffing to the lane-based work arbiter
    (``work.assign_jobs``): pawns self-select their best legal job from
    skill-derived priorities, so the governor no longer hand-places pawns. Its
    levers are now policy only - rest unhappy/breaking pawns and queue the next
    missing chain building. It stays the integration oracle: if a town survives N
    days under it (with the arbiter doing the staffing), the economy is winnable.
    ``decide`` is pure: it reads context and returns actions without mutating state.
    """

    def decide(self, context: dict[str, Any]) -> list[GovernorAction]:
        actions: list[GovernorAction] = []
        buildings = context.get("buildings", [])
        construction = context.get("construction", [])
        exceptions = context.get("exceptions", [])
        low_food = any(exc["kind"] == "low_food" for exc in exceptions)

        # 1) Move unhappy / breaking pawns onto a restorative schedule - unless the
        # civ is short on food. The rest schedule has zero work hours and does not
        # restore the food reserve, so resting a hungry pawn cannot lift the mood
        # (the drag is hunger) and only pulls a producer off the food chain,
        # deepening the shortage. During a food crisis, keep everyone working so
        # the chain can recover; the food response owns that lane.
        rescheduled: set[str] = set()
        if not low_food:
            for exc in exceptions:
                pawn_id = exc.get("pawn_id")
                if exc["kind"] in RESCHEDULE_KINDS and pawn_id and pawn_id not in rescheduled:
                    actions.append(GovernorAction.set_schedule(pawn_id, RESTORATIVE_SCHEDULE))
                    rescheduled.add(pawn_id)

        # 2) Ask the engine to place the next missing build-1 chain link. The
        # engine/Track A owns cost checks and construction-site realization.
        existing = {building["kind"] for building in buildings}
        pending = {site["building_kind"] for site in construction}
        if any(exc["kind"] == "low_water" for exc in exceptions):
            if WATER_BUILDING_KIND not in existing and WATER_BUILDING_KIND not in pending:
                actions.append(GovernorAction.place_building(WATER_BUILDING_KIND, *WATER_BUILD_LOCATION))
                return actions

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
# back to FallbackGovernor on ANY error (this is why the civilization exception entity
# is ``CivilizationException`` and not ``Exception`` - the bare ``except Exception``
# below must stay a safety net, not catch a domain object).
# ---------------------------------------------------------------------------

CIVILIZATION_ACTION_KINDS = (
    ACTION_ASSIGN_PAWN,
    ACTION_SET_SCHEDULE,
    ACTION_SET_WORK_PRIORITY,
    ACTION_PLACE_BUILDING,
    ACTION_SET_PRODUCTION_TARGET,
    ACTION_SET_RESEARCH,
)

CIVILIZATION_ACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "enum": list(CIVILIZATION_ACTION_KINDS)},
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
                    "work_type": {"type": "string"},
                    "level": {"type": "integer"},
                },
                "required": ["kind"],
            },
        }
    },
    "required": ["actions"],
}

GOVERNOR_SYSTEM_PROMPT = (
    "You are the Governor of a small civilization. You set POLICY only - you never move "
    "pawns yourself. Each turn you read a JSON summary of the civilization and reply with "
    "a JSON object {\"actions\": [...]} of zero or more policy actions. Valid action "
    "kinds and their fields:\n"
    "Mood is on a 0-100 scale (about 50 is neutral; below 35 a pawn starts to "
    "break).\n"
    "Pawns now choose their own jobs from their work priorities - you tune named "
    "pawns when needed, you do not place pawns by hand.\n"
    "- set_work_priority {group, work_type, level}: group is a pawn_id or \"all\"; "
    "work_type is a skill (water, farming, milling, baking, forestry, "
    "woodworking, mining); level 1 is highest, 4 lowest, 0 disables it. This is your main "
    "lever for steering labour. For now, only tune essential food/water work "
    "(water, farming, milling, baking), target named pawns, keep it at level 1 or "
    "2, and never disable or demote it. Do not use group \"all\" for work "
    "priorities because it erases specialization.\n"
    "- assign_pawn {pawn_id, building_id, role}: a rare FORCED override that pins "
    "one pawn to one building slot. Prefer set_work_priority instead.\n"
    "- set_schedule {group, template}: rest only a named unhappy or breaking pawn; "
    "do not mass-change schedules.\n"
    "- place_building {building_kind, x, y}: queue the next missing production "
    "building.\n"
    "- set_production_target {building_id, good, amount}.\n"
    "- set_research {tech}.\n"
    "Prefer tuning work priorities and resting unhappy pawns over forcing "
    "assignments. Return at most 6 highest-impact actions per turn. Reply with "
    "valid JSON only - no prose, no markdown, no chain of thought."
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
    if kind not in CIVILIZATION_ACTION_KINDS:
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
        work_type=_clean_str(data.get("work_type")),
        level=_coerce_int(data.get("level")),
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


def filter_model_actions(context: dict[str, Any], actions: list[GovernorAction]) -> list[GovernorAction]:
    """Drop LLM-only policy actions that can shut down survival essentials.

    Validation still answers "is this action structurally legal?". This answers
    the narrower safety question for model-originated policy: the model may rest
    named unhappy pawns and raise essential priorities for named pawns, but it
    may not churn schedules, flatten the whole town's specializations, boost
    nonessential work above survival work, or demote the food/water chain below
    its survival floor.
    """
    return [action for action in actions if _model_action_safe(context, action)]


def _model_action_safe(context: dict[str, Any], action: GovernorAction) -> bool:
    if action.kind == ACTION_SET_SCHEDULE:
        return action.template == RESTORATIVE_SCHEDULE and action.group != "all" and _rest_target_has_exception(
            context, action.group
        )
    if action.kind == ACTION_SET_WORK_PRIORITY:
        if action.group == "all":
            return False
        if action.work_type not in ESSENTIAL_WORK_TYPES:
            return False
        if action.level is None:
            return True
        return 0 < action.level <= LOWEST_SAFE_MODEL_ESSENTIAL_PRIORITY
    return True


def _rest_target_has_exception(context: dict[str, Any], group: str | None) -> bool:
    if not group:
        return False
    for exc in context.get("exceptions", []):
        if exc.get("pawn_id") == group and exc.get("kind") in RESCHEDULE_KINDS:
            return True
    return False


def _clean_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


class LLMGovernor:
    """LLM-backed governor with a hard fallback to FallbackGovernor.

    ``decide`` asks the model for an action list; on any error - disabled client,
    timeout, bad JSON, schema miss - it returns the deterministic fallback's
    decision instead, so the civilization never stalls on a flaky model. A successful
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
        # Telemetry-only (does not affect decisions): how the last decide() went -
        # "model" (used the LLM), "fallback" (model returned nothing usable),
        # "error" (model/parse failed and the hard fallback covered), or
        # "disabled" (no model loaded - fallback by design, not a failure).
        self.last_outcome = "idle"
        self.last_error = ""

    def decide(self, context: dict[str, Any]) -> list[GovernorAction]:
        try:
            payload = self._propose(context) if self._propose is not None else self._ask_model(context)
            actions = filter_model_actions(context, parse_action_list(payload))
        except Exception as exc:
            disabled = self._propose is None and (self.client is None or not self.client.enabled)
            self.last_outcome = "disabled" if disabled else "error"
            self.last_error = str(exc)
            return self.fallback.decide(context)
        if actions:
            self.last_outcome = "model"
            self.last_error = ""
            return actions
        self.last_outcome = "fallback"
        self.last_error = "empty"
        return self.fallback.decide(context)

    def _ask_model(self, context: dict[str, Any]) -> dict[str, Any]:
        if self.client is None:
            raise LLMClientError("LLM governor has no client configured")
        return self.client.complete_json(
            GOVERNOR_SYSTEM_PROMPT,
            {"civilization": context},
            schema=CIVILIZATION_ACTION_SCHEMA,
            name="civilization_actions",
        )


# ---------------------------------------------------------------------------
# Non-blocking governor scheduler (integration milestone I2)
#
# The live civilization viewer renders at 60 fps and steps the engine on a short real-
# time interval. A 4B local model takes seconds to answer, so calling it inline
# from ``step_hour`` would freeze the window. ``CivilizationDecisionScheduler`` runs the
# model call on a single worker thread and implements the ``Governor`` protocol:
# each hour it harvests any finished call, may launch a new one, and returns
# either the model's freshly decided actions or - while the model is mid-thought,
# offline, or disabled - the deterministic ``FallbackGovernor``'s actions. The
# civilization keeps advancing every hour and only *upgrades* to LLM policy when a
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


class CivilizationDecisionScheduler:
    """Non-blocking ``Governor`` adapter that runs an LLM call off the render loop.

    Wraps a :class:`LocalLLMClient`; its :meth:`decide` never blocks on the
    network. A single worker thread holds at most one in-flight model call. When
    a call finishes, its actions are applied on the next :meth:`decide`; every
    hour in between (and whenever the model is offline or disabled) falls back to
    the deterministic :class:`FallbackGovernor`, so the civilization never stalls.
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
    ) -> "CivilizationDecisionScheduler":
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
        return ThreadPoolExecutor(max_workers=1, thread_name_prefix="civilization-llm")

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
        # LLMGovernor: "the model chose nothing, keep the civilization moving".
        self._pending = actions or None

    def _decide_actions(self, context: dict[str, Any]) -> tuple[list[GovernorAction], float]:
        """Worker-thread body: ask the model and parse its action list."""
        start = self.clock()
        payload = self.client.complete_json(
            GOVERNOR_SYSTEM_PROMPT,
            {"civilization": context},
            schema=CIVILIZATION_ACTION_SCHEMA,
            name="civilization_actions",
        )
        actions = parse_action_list(payload)
        actions = filter_model_actions(context, actions)
        return actions, self.clock() - start
