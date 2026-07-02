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

from . import buildings, economy, pawns, schedule, work
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
# Food-chain expansion (the dig-out): during a shortage the governor grows more
# food capacity, front of chain first, so a low-food civ visibly "plants more
# wheat". Balanced ratio that feeds the bakeries, from the recipes (Farm -> 1
# grain; Mill: 2 grain -> 1 flour; Bakery: 2 flour -> 4 bread): ~4 farms + 2 mills
# per bakery. New buildings spread across a field area so ghosts do not stack.
FOOD_CHAIN_KINDS = ("Farm", "Mill", "Bakery")
FOOD_EXPANSION_ORIGIN = (2, 11)

# Food shortage signal. Neither metric works alone: bread-days-of-cover twitches
# on just-in-time eating bursts, and average nutrition craters every night because
# synced pawns cannot eat while asleep - so a healthy, bread-rich civ still dips to
# 0% saturation before breakfast. The honest signal is the *conjunction*: the pawns
# are actually hungry AND the civ has no bread buffer to fix it. A healthy civ's
# overnight dip has hungry pawns but a fat buffer, so it never fires; a real deficit
# has both. (The hunger gate also samples cover during the stable overnight window,
# dodging the daytime eating-burst noise.)
LOW_FOOD_COVER_DAYS = 1.0
LOW_FOOD_NEED = 0.5

LABORATORY_BUILDING_KIND = "Laboratory"
LABORATORY_BUILD_LOCATION = (7, 1)

BROKEN_STATES = (pawns.STATE_SLACKING, pawns.STATE_WANDERING)
RESCHEDULE_KINDS = ("unhappy_pawn", "pawn_breaking", "pawn_break")
RESTORATIVE_SCHEDULE = "rest"
ESSENTIAL_WORK_TYPES = frozenset(("water", "farming", "milling", "baking"))
LOWEST_SAFE_MODEL_ESSENTIAL_PRIORITY = 2
# The survival chain the model may not throttle via a production cap. Capping any
# of these at/near zero idles a food/water building (set_production_target is a
# ceiling: production halts once stock reaches the target), so the model is barred
# from targeting them at all - it grows food via place_building / priorities, not
# by capping essentials.
ESSENTIAL_GOODS = frozenset((Good.GRAIN, Good.FLOUR, Good.BREAD, Good.WATER))
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
        "research": list(state.research),
        "research_target": state.research_target,
        "research_points": state.research_points,
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
        # Conjunction (see LOW_FOOD_* notes): fire only when pawns are hungry AND
        # the bread buffer is gone, so an overnight saturation dip in a bread-rich
        # civ never trips it and the dig-out does not manically over-build.
        if food_need < LOW_FOOD_NEED and food_cover < LOW_FOOD_COVER_DAYS:
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
        market_demand = economy.market_bread_demand(state)
        if market_demand.unmet_buyers > 0:
            exceptions.append(
                CivilizationException(
                    "market_service_pressure",
                    building_id=market_demand.market_id,
                    detail=(
                        f"{market_demand.unmet_buyers} unmet bread buyers, "
                        f"{market_demand.sellable_bread} sellable bread"
                    ),
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
        # An LLM-sourced building_kind is untrusted input: a live model can
        # propose a plausible but nonexistent kind (seen in practice: "bread
        # storage"), which would otherwise reach construction and crash on the
        # first building_def lookup. Reject it here instead.
        if not buildings.is_known_kind(action.building_kind):
            return False
        if state.grid is not None:
            return state.grid.in_bounds(action.x, action.y)
        return True

    if action.kind == ACTION_SET_RESEARCH:
        return bool(action.tech) and action.tech in economy.RESEARCH_COSTS and action.tech not in state.research

    return False


def apply_actions(state: FactionState, actions: list[GovernorAction]) -> list[GovernorAction]:
    """Validate then apply each action; return the ones that took effect (B4)."""
    applied: list[GovernorAction] = []
    for action in actions:
        if not validate_action(state, action):
            continue
        if action.kind == ACTION_ASSIGN_PAWN:
            building = state.buildings[action.building_id]
            # assign_pawn is now the forced override (the arbiter's top lane): pin
            # the pawn here so the work arbiter keeps it instead of reassigning.
            pawn = state.pawns[action.pawn_id]
            work.release_staff_references(state, pawn.id, keep_building_id=building.id)
            building.staffed_by.append(action.pawn_id)
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
            state.research_target = action.tech
            applied.append(action)
        elif action.kind == ACTION_PLACE_BUILDING:
            # Realized by Track A construction; returning it lets the engine do
            # that without the governor mutating construction state directly.
            applied.append(action)
    return applied


def food_expansion_action(
    buildings: list[dict[str, Any]], construction: list[dict[str, Any]]
) -> GovernorAction | None:
    """The dig-out: which food building to add during a shortage, or ``None``.

    One building at a time - if a food-chain building is already under
    construction, wait for it rather than queueing a pile. Otherwise grow the
    stage that is short of the ratio that feeds the bakeries, front of chain first
    so a shortage reads as "plant more wheat": no bakery at all -> Bakery; too few
    farms for the bakeries -> Farm; too few mills -> Mill; otherwise raise the
    output ceiling with another Bakery. This is *additional* capacity (duplicates
    allowed), which ``BUILD_ORDER`` never adds - it only fills missing kinds.
    """
    if any(site.get("building_kind") in FOOD_CHAIN_KINDS for site in construction):
        return None
    counts = {kind: 0 for kind in FOOD_CHAIN_KINDS}
    for building in buildings:
        if building.get("kind") in counts:
            counts[building["kind"]] += 1
    farms, mills, bakeries = counts["Farm"], counts["Mill"], counts["Bakery"]
    if bakeries == 0:
        kind = "Bakery"
    elif farms < 4 * bakeries:
        kind = "Farm"
    elif mills < 2 * bakeries:
        kind = "Mill"
    else:
        # Already at the balanced ratio for the bakeries on hand. Adding more would
        # just churn, so stop growing - a lingering shortage here is a staffing or
        # productivity problem, not a building-count one.
        return None
    total = farms + mills + bakeries
    x = FOOD_EXPANSION_ORIGIN[0] + (total % 8) * 2
    y = FOOD_EXPANSION_ORIGIN[1] + (total // 8)
    return GovernorAction.place_building(kind, x, y)


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

        # 2) The dig-out: on a food shortage, grow more food capacity (plant more
        # wheat) before anything else. Food is the survival staple, so it outranks
        # water and the generic build order. The engine/Track A owns the cost check
        # and construction realization.
        if low_food:
            expansion = food_expansion_action(buildings, construction)
            if expansion is not None:
                actions.append(expansion)
                return actions

        # 3) Ask the engine to place the next missing build-1 chain link. The
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
        else:
            if LABORATORY_BUILDING_KIND not in existing and LABORATORY_BUILDING_KIND not in pending:
                actions.append(
                    GovernorAction.place_building(
                        LABORATORY_BUILDING_KIND,
                        LABORATORY_BUILD_LOCATION[0],
                        LABORATORY_BUILD_LOCATION[1],
                    )
                )
            else:
                faction = context.get("faction", {})
                if not faction.get("research_target"):
                    for tech in economy.RESEARCH_COSTS:
                        if tech not in faction.get("research", []):
                            actions.append(GovernorAction.set_research(tech))
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
    "woodworking, mining, research); level 1 is highest, 4 lowest, 0 disables it. This is your main "
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
    "- set_research {tech}: select a known research target; Laboratory work completes it.\n"
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


def partition_model_actions(
    context: dict[str, Any], actions: list[GovernorAction]
) -> tuple[list[GovernorAction], list[tuple[GovernorAction, str]]]:
    """Split model-origin actions into (allowed, [(rejected, reason), ...]).

    The rejected list carries a short reason per action so the decision audit can
    show *what* the model proposed and *why* the guard denied it, instead of the
    action silently vanishing (review E-2 / Slice B).
    """
    allowed: list[GovernorAction] = []
    rejected: list[tuple[GovernorAction, str]] = []
    for action in actions:
        reason = _model_action_reason(context, action)
        if reason is None:
            allowed.append(action)
        else:
            rejected.append((action, reason))
    return allowed, rejected


def filter_model_actions(context: dict[str, Any], actions: list[GovernorAction]) -> list[GovernorAction]:
    """Drop model-origin policy actions the safety guard denies (allowed subset)."""
    allowed, _rejected = partition_model_actions(context, actions)
    return allowed


def _model_action_reason(context: dict[str, Any], action: GovernorAction) -> str | None:
    """Why a model-origin action is unsafe, or ``None`` if the guard allows it.

    Default-deny allowlist (review E-2 / Slice B): every action kind needs an
    explicit rule here. Validation answers "is this structurally legal?"; this
    answers the narrower "may an *untrusted local model* emit this policy?". Kinds
    without an explicit allow rule are denied so the Governor/pawn autonomy
    boundary is enforced by policy, not by prompt etiquette. The "grow-safe"
    policy lets the model grow the economy (place buildings, retask essential
    priorities, pick research) but not shut down survival essentials or seize
    per-pawn control via a forced assignment.
    """
    kind = action.kind
    if kind == ACTION_SET_SCHEDULE:
        # Only a rest schedule, only for a named pawn that is actually flagged -
        # never a town-wide reschedule (that would idle the whole civ).
        if action.template != RESTORATIVE_SCHEDULE:
            return "schedule: only a rest schedule is allowed"
        if action.group == "all" or action.group is None:
            return "schedule: no town-wide reschedule"
        if not _rest_target_has_exception(context, action.group):
            return "schedule: target has no rest-worthy exception"
        return None
    if kind == ACTION_SET_WORK_PRIORITY:
        if action.group == "all":
            return "priority: no town-wide priority change"
        if action.work_type not in ESSENTIAL_WORK_TYPES:
            return "priority: only essential work types"
        if action.level is None:
            return None
        if not 0 < action.level <= LOWEST_SAFE_MODEL_ESSENTIAL_PRIORITY:
            return "priority: essential level out of safe range"
        return None
    if kind == ACTION_PLACE_BUILDING:
        # Grow-safe: the model may expand the economy. Unknown kinds are caught by
        # validate_action; placement only spends coin + queues a site, so it can
        # never idle a running essential.
        if not action.building_kind or not buildings.is_known_kind(action.building_kind):
            return "place: unknown building kind"
        return None
    if kind == ACTION_SET_PRODUCTION_TARGET:
        # Grow-safe with an essential-shutdown floor: production_target is a
        # ceiling, so capping a survival good idles its building. The model may
        # retarget non-essential goods, never the food/water chain.
        if action.amount is None:
            return "target: missing amount"
        if action.good in ESSENTIAL_GOODS:
            return "target: cannot cap an essential survival good"
        return None
    if kind == ACTION_SET_RESEARCH:
        # Research is the victory spine; choosing a tech cannot break survival.
        if not action.tech:
            return "research: missing tech"
        return None
    if kind == ACTION_ASSIGN_PAWN:
        # Forced override is the arbiter's top lane and the demonstrated
        # labor-conservation trigger (review E-1); it is an operator/fallback
        # lever, not a model action.
        return "assign_pawn: forced override is not a model-allowed action"
    return f"{kind}: no model-safety rule (default-deny)"


def _model_action_safe(context: dict[str, Any], action: GovernorAction) -> bool:
    """Back-compat boolean guard: True when the action is model-safe."""
    return _model_action_reason(context, action) is None


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
        # Model actions the safety guard denied this hour, with reasons - surfaced
        # in the decision audit so a rejected proposal is visible, not silent.
        self.last_guard_rejected: list[tuple[GovernorAction, str]] = []

    @property
    def last_source(self) -> str:
        """Which policy drove the last decide() - the blocking-path twin of the
        scheduler's per-hour origin (review E-4 / Slice D)."""
        return SOURCE_MODEL if self.last_outcome == "model" else SOURCE_FALLBACK

    def decide(self, context: dict[str, Any]) -> list[GovernorAction]:
        try:
            payload = self._propose(context) if self._propose is not None else self._ask_model(context)
            actions, self.last_guard_rejected = partition_model_actions(context, parse_action_list(payload))
        except Exception as exc:
            disabled = self._propose is None and (self.client is None or not self.client.enabled)
            self.last_outcome = "disabled" if disabled else "error"
            self.last_error = str(exc)
            self.last_guard_rejected = []
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

# Per-hour decision origin (review E-4 / Slice D): which policy actually drove
# THIS hour's actions. Distinct from GovernorStatus.state, which is pipeline
# health - a scheduler can be "idle"-healthy for 96 hours while every single
# hour's actions came from the fallback. The telemetry decision record carries
# this so the analyzer can count model *emissions* instead of scheduler hours.
SOURCE_MODEL = "model"
SOURCE_FALLBACK = "fallback"

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
        self._future: Future[tuple[list[GovernorAction], list[tuple[GovernorAction, str]], float]] | None = None
        self._pending: list[GovernorAction] | None = None
        self._next_time = 0.0
        self.status = self._idle_status()
        # Model actions the safety guard denied on the last completed call, with
        # reasons - carried to the decision audit like ``status.last_action_kinds``.
        self.last_guard_rejected: list[tuple[GovernorAction, str]] = []
        # Which policy drove the last decide(): SOURCE_MODEL only on the hour a
        # finished model decision was actually returned (review E-4 / Slice D).
        self.last_source = SOURCE_FALLBACK

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
            self.last_source = SOURCE_MODEL
            return actions
        self.last_source = SOURCE_FALLBACK
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
        self.last_source = SOURCE_FALLBACK
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
            actions, self.last_guard_rejected, latency = future.result()
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

    def _decide_actions(
        self, context: dict[str, Any]
    ) -> tuple[list[GovernorAction], list[tuple[GovernorAction, str]], float]:
        """Worker-thread body: ask the model and parse its action list."""
        start = self.clock()
        payload = self.client.complete_json(
            GOVERNOR_SYSTEM_PROMPT,
            {"civilization": context},
            schema=CIVILIZATION_ACTION_SCHEMA,
            name="civilization_actions",
        )
        actions, rejected = partition_model_actions(context, parse_action_list(payload))
        return actions, rejected, self.clock() - start
