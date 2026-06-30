"""Stockpile behaviour, production, and the tax loop. [Track A]

Drives the deterministic economy each tick: staffed buildings with inputs turn
work into goods, and once per day the civilization earns coin from
``f(avg_mood, population, tax_rate)``. Coin gates new construction.

The one cross-track seam lives here: production multiplies a building's base
rate by the sum of ``effective_work`` across its staffed pawns. Track B owns
``effective_work`` (mood.py); Track A only depends on its signature.

Phase 0 status: signatures frozen, bodies stubbed. Implemented in A2 and A4.
"""

from __future__ import annotations

from typing import Callable

from . import mood
from .core import BUILD1_NEEDS, FactionState, Good, Pawn, Recipe, Stockpile

# Base output rate per unit of summed effective work, per tick.
BASE_RATE = 1.0
WATER_UNITS_PER_PAWN_DAY = 1.0

WorkFn = Callable[[Pawn, Recipe, int], float]


def stockpile_add(stockpile: Stockpile, good: Good, amount: int) -> None:
    """Add ``amount`` of ``good`` (delegates to Stockpile.add)."""
    stockpile.add(good, amount)


def building_output_rate(state: FactionState, building_id: str, work_fn: WorkFn) -> float:
    """``BASE_RATE * sum(effective_work)`` across the building's staffed pawns."""
    building = state.buildings.get(building_id)
    if building is None or not building.built or building.recipe is None:
        return 0.0
    total_work = 0.0
    for pawn_id in building.staffed_by:
        pawn = state.pawns.get(pawn_id)
        if pawn is not None:
            total_work += work_fn(pawn, building.recipe, state.time_of_day)
    return BASE_RATE * total_work


def production_tick(state: FactionState, *, work_fn: WorkFn = mood.effective_work) -> None:
    """Advance every staffed, built, input-satisfied building by one tick."""
    for building_id, building in state.buildings.items():
        recipe = building.recipe
        if not building.built or recipe is None or not building.staffed_by:
            continue
        if recipe.work_units <= 0:
            raise ValueError("Recipe work_units must be positive")
        cycles = int(building_output_rate(state, building_id, work_fn) // recipe.work_units)
        if cycles <= 0:
            continue
        input_limit = _input_limited_cycles(state.stockpile, recipe.inputs)
        if input_limit is not None:
            cycles = min(cycles, input_limit)
        if cycles <= 0:
            continue
        for good, amount in recipe.inputs.items():
            _validate_recipe_amount(good, amount)
            state.stockpile.remove(good, amount * cycles)
        for good, amount in recipe.outputs.items():
            _validate_recipe_amount(good, amount)
            state.stockpile.add(good, amount * cycles)


def average_mood(state: FactionState) -> float:
    """Mean pawn mood across the civilization on the 0-100 scale (0.0 if empty)."""
    if not state.pawns:
        return 0.0
    return sum(pawn.mood for pawn in state.pawns.values()) / len(state.pawns)


def average_need(state: FactionState, need: str) -> float:
    """Mean satisfaction of ``need`` across the civilization, in [0, 1] (0.0 if empty).

    Powers the viewer's Civ stats bar. A pawn missing the need reads as satisfied
    (1.0), matching the "needs start full" convention in ``pawns.decay_needs``.
    """
    if need not in BUILD1_NEEDS:
        raise ValueError(f"unknown tracked need: {need!r}")
    if not state.pawns:
        return 0.0
    total = sum(max(0.0, min(1.0, pawn.needs.get(need, 1.0))) for pawn in state.pawns.values())
    return total / len(state.pawns)


def water_days_of_cover(state: FactionState) -> float:
    """How many pawn-days the current water stockpile can cover."""
    population = len(state.pawns)
    if population == 0:
        return float("inf")
    return state.stockpile.counts.get(Good.WATER, 0) / (population * WATER_UNITS_PER_PAWN_DAY)


def daily_tax_income(state: FactionState) -> int:
    """Coin earned for one day from ``f(avg_mood, population, tax_rate)``.

    ``average_mood`` is now 0-100, so it is normalised back to [0, 1] here; this
    keeps the day-1 coin output identical to the pre-0-100 calibration.
    """
    population = len(state.pawns)
    if population == 0:
        return 0
    tax_rate = max(0.0, state.tax_rate)
    return int(population * (average_mood(state) / mood.MOOD_MAX) * tax_rate * 10)


def apply_daily_tax(state: FactionState) -> int:
    """Add the day's tax income to ``state.coin``; return the amount added."""
    income = daily_tax_income(state)
    state.coin += income
    return income


def can_afford(state: FactionState, cost: dict[Good, int], *, coin_cost: int = 0) -> bool:
    """Whether the civilization has the goods and coin for ``cost``."""
    if coin_cost < 0:
        raise ValueError("coin_cost must be non-negative")
    if state.coin < coin_cost:
        return False
    for good, amount in cost.items():
        if not state.stockpile.has(good, amount):
            return False
    return True


def _input_limited_cycles(stockpile: Stockpile, inputs: dict[Good, int]) -> int | None:
    if not inputs:
        return None
    limits = []
    for good, amount in inputs.items():
        _validate_recipe_amount(good, amount)
        limits.append(stockpile.counts.get(good, 0) // amount)
    return min(limits)


def _validate_recipe_amount(good: Good, amount: int) -> None:
    if not isinstance(good, Good):
        raise TypeError("Recipe goods must use Good enum values")
    if amount <= 0:
        raise ValueError("Recipe amounts must be positive")
