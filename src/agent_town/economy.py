"""Stockpile behaviour, production, and the tax loop. [Track A]

Drives the deterministic economy each tick: staffed buildings with inputs turn
work into goods, and once per day the colony earns coin from
``f(avg_mood, population, tax_rate)``. Coin gates new construction.

The one cross-track seam lives here: production multiplies a building's base
rate by the sum of ``effective_work`` across its staffed pawns. Track B owns
``effective_work`` (mood.py); Track A only depends on its signature.

Phase 0 status: signatures frozen, bodies stubbed. Implemented in A2 and A4.
"""

from __future__ import annotations

from typing import Callable

from . import mood
from .core import FactionState, Good, Pawn, Recipe, Stockpile

# Base output rate per unit of summed effective work, per tick.
BASE_RATE = 1.0

WorkFn = Callable[[Pawn, Recipe, int], float]


def stockpile_add(stockpile: Stockpile, good: Good, amount: int) -> None:
    """Add ``amount`` of ``good`` (delegates to Stockpile.add)."""
    raise NotImplementedError("stockpile_add - Track A, milestone A1")


def building_output_rate(state: FactionState, building_id: str, work_fn: WorkFn) -> float:
    """``BASE_RATE * sum(effective_work)`` across the building's staffed pawns."""
    raise NotImplementedError("building_output_rate - Track A, milestone A2")


def production_tick(state: FactionState, *, work_fn: WorkFn = mood.effective_work) -> None:
    """Advance every staffed, built, input-satisfied building by one tick."""
    raise NotImplementedError("production_tick - Track A, milestone A2")


def average_mood(state: FactionState) -> float:
    """Mean pawn mood across the colony (0.0 if empty)."""
    raise NotImplementedError("average_mood - Track A, milestone A4")


def daily_tax_income(state: FactionState) -> int:
    """Coin earned for one day from ``f(avg_mood, population, tax_rate)``."""
    raise NotImplementedError("daily_tax_income - Track A, milestone A4")


def apply_daily_tax(state: FactionState) -> int:
    """Add the day's tax income to ``state.coin``; return the amount added."""
    raise NotImplementedError("apply_daily_tax - Track A, milestone A4")


def can_afford(state: FactionState, cost: dict[Good, int], *, coin_cost: int = 0) -> bool:
    """Whether the colony has the goods and coin for ``cost``."""
    raise NotImplementedError("can_afford - Track A, milestone A4")
