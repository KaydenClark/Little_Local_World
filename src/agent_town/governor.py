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

from typing import Any, Protocol

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
