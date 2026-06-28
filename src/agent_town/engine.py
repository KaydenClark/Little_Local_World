"""Reusable headless colony engine (integration milestone I1).

Extracts the I1 test-harness loop into a single reusable stepper so the viewer
(I3) and the LLM governor (I2) run against the same deterministic step the
fallback-survival regression proves. One call to :func:`step_hour` advances the
colony by one simulated hour:

1. the governor reads a context and emits policy actions; valid ones are
   applied, and ``place_building`` actions are realized as construction sites
   when the colony can afford them;
2. pending construction hauls its required goods and spends build work, flipping
   to a built ``Building`` when ready;
3. each pawn decays its needs, restores from its schedule block, eats when
   hungry and off-shift, recomputes mood, and advances its break state;
4. staffed, input-satisfied buildings produce through the ``effective_work``
   seam;
5. the clock advances one hour, and tax is collected on a day rollover.

The governor sets policy only; the engine owns affordability, construction
realization, and the per-pawn / production / tax tick. Same seed plus same
governor equals same outcome - the LLM governor is the only nondeterministic
layer and drops in behind the same ``Governor`` protocol.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import buildings, construction, economy, governor as governor_mod, mood, pawns, schedule
from .core import (
    ACTION_PLACE_BUILDING,
    FactionState,
    Good,
    GovernorAction,
    NEED_FOOD,
    SCHEDULE_ANY,
)

# Build work spent against a goods-satisfied construction site per hour. Build 1
# has no dedicated builder/hauler job; tying construction to pawn labour is a
# build-2 refinement. Kept a deterministic constant here.
CONSTRUCTION_WORK_PER_HOUR = 1.0

# A pawn eats one bread when off-shift (an "any" block) and at least this hungry.
EAT_FOOD_THRESHOLD = 0.65


@dataclass(frozen=True)
class StepResult:
    """What one :func:`step_hour` changed - for the viewer, logs, and tests."""

    actions_applied: tuple[GovernorAction, ...] = ()
    buildings_completed: tuple[str, ...] = ()
    days_rolled: int = 0
    tax_collected: int = 0


def step_hour(state: FactionState, gov: governor_mod.Governor | None = None) -> StepResult:
    """Advance the colony by one simulated hour under ``gov`` (fallback default)."""
    gov = gov or governor_mod.FallbackGovernor()

    actions = gov.decide(governor_mod.build_context(state))
    applied = governor_mod.apply_actions(state, actions)

    completed = _realize_placements(state, applied)
    completed.extend(_advance_construction(state))

    _advance_pawns(state)
    economy.production_tick(state)

    days_rolled = schedule.advance_clock(state, 1)
    tax_collected = economy.apply_daily_tax(state) if days_rolled else 0

    return StepResult(
        actions_applied=tuple(applied),
        buildings_completed=tuple(completed),
        days_rolled=days_rolled,
        tax_collected=tax_collected,
    )


def run(state: FactionState, gov: governor_mod.Governor | None = None, *, hours: int) -> list[StepResult]:
    """Step the colony ``hours`` times, returning each hour's result."""
    if hours < 0:
        raise ValueError("hours must be non-negative")
    gov = gov or governor_mod.FallbackGovernor()
    return [step_hour(state, gov) for _ in range(hours)]


def run_days(state: FactionState, gov: governor_mod.Governor | None = None, *, days: int) -> list[StepResult]:
    """Step the colony for ``days`` whole days."""
    if days < 0:
        raise ValueError("days must be non-negative")
    return run(state, gov, hours=days * schedule.HOURS_PER_DAY)


def _realize_placements(state: FactionState, applied: list[GovernorAction]) -> list[str]:
    """Turn affordable ``place_building`` actions into construction sites.

    The governor only proposes placement; the engine owns the cost check and the
    site so the governor never mutates construction state directly. A placement
    the colony cannot afford (coin or goods) is skipped rather than placed as a
    site that could never complete.
    """
    placed: list[str] = []
    for action in applied:
        if action.kind != ACTION_PLACE_BUILDING or action.building_kind is None:
            continue
        kind = action.building_kind
        build_cost = buildings.building_def(kind).build_cost
        coin_cost = construction.building_coin_cost(kind)
        if not economy.can_afford(state, build_cost, coin_cost=coin_cost):
            continue
        site_id = _unique_site_id(state, kind)
        construction.place_construction_site(state, kind, action.x or 0, action.y or 0, site_id=site_id)
        placed.append(site_id)
    return placed


def _advance_construction(state: FactionState) -> list[str]:
    """Haul goods to each pending site, spend build work, complete what is ready."""
    completed: list[str] = []
    for site in list(state.construction_sites.values()):
        for good, amount in site.required.items():
            missing = amount - site.delivered.get(good, 0)
            if missing > 0 and state.stockpile.counts.get(good, 0) > 0:
                construction.haul_to_site(state, site, good, missing)
        if construction.goods_satisfied(site):
            construction.advance_construction(site, CONSTRUCTION_WORK_PER_HOUR)
            building = construction.complete_if_ready(state, site)
            if building is not None:
                completed.append(building.id)
    return completed


def _advance_pawns(state: FactionState) -> None:
    """Per-pawn need decay, schedule restoration, eating, mood, and break state."""
    for pawn in state.pawns.values():
        block = schedule.block_for(pawn.schedule, state.time_of_day)
        pawns.decay_needs(pawn, 1.0)
        pawns.apply_schedule_block(pawn, block, 1.0)
        if (
            block == SCHEDULE_ANY
            and pawn.needs[NEED_FOOD] < EAT_FOOD_THRESHOLD
            and state.stockpile.counts.get(Good.BREAD, 0) > 0
        ):
            state.stockpile.remove(Good.BREAD, 1)
            pawns.restore_need(pawn, NEED_FOOD, 1.0)
        pawn.mood = mood.compute_mood(pawn)
        pawns.update_break_state(pawn)


def _unique_site_id(state: FactionState, kind: str) -> str:
    """A site id for ``kind`` that collides with no existing site or building."""
    base = kind.strip().lower()
    index = 1
    while True:
        candidate = f"{base}-{index}"
        if candidate not in state.construction_sites and candidate not in state.buildings:
            return candidate
        index += 1
