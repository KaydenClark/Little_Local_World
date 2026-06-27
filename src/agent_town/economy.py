from __future__ import annotations

from .core import Building, FactionState, Good, Stockpile


def advance_economy(state: FactionState, dt: float) -> None:
    if dt <= 0:
        return
    for building in state.buildings:
        _advance_building_production(state.stockpile, building, dt)


def _advance_building_production(stockpile: Stockpile, building: Building, dt: float) -> None:
    if not building.built or building.recipe is None or not building.staffed_by:
        return
    if building.recipe.work_units <= 0:
        raise ValueError("Recipe work_units must be positive")

    staff_count = len(building.staffed_by)
    cycles = int((dt * staff_count) / building.recipe.work_units)
    if cycles <= 0:
        return

    input_limit = _input_limited_cycles(stockpile, building.recipe.inputs)
    if input_limit is not None:
        cycles = min(cycles, input_limit)
    if cycles <= 0:
        return

    for good, amount in building.recipe.inputs.items():
        stockpile.remove(good, amount * cycles)
    for good, amount in building.recipe.outputs.items():
        _validate_recipe_amount(good, amount)
        stockpile.add(good, amount * cycles)


def _input_limited_cycles(stockpile: Stockpile, inputs: dict[Good, int]) -> int | None:
    if not inputs:
        return None

    limits: list[int] = []
    for good, amount in inputs.items():
        _validate_recipe_amount(good, amount)
        limits.append(stockpile.counts.get(good, 0) // amount)
    return min(limits)


def _validate_recipe_amount(good: Good, amount: int) -> None:
    if not isinstance(good, Good):
        raise TypeError("Recipe goods must use Good enum values")
    if amount <= 0:
        raise ValueError("Recipe amounts must be positive")
