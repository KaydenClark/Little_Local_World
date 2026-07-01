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

from dataclasses import dataclass
from typing import Callable

from . import mood
from .core import BUILD1_NEEDS, FactionState, Good, Pawn, Recipe, Stockpile

# Base output rate per unit of summed effective work, per tick.
BASE_RATE = 1.0
WATER_UNITS_PER_PAWN_DAY = 1.0
DAILY_WAGE = 1
MARKET_KIND = "Market"
STOREHOUSE_KIND = "Storehouse"
STOREHOUSE_CAPACITY_BONUS = 120
MARKET_DAILY_BREAD_EXPORT_LIMIT = 4
MARKET_BREAD_RESERVE_PER_PAWN = 6
MARKET_BREAD_PRICE = 1
TECH_EFFICIENT_BAKING = "efficient_baking"
RESEARCH_COSTS = {TECH_EFFICIENT_BAKING: 4}
LABORATORY_KIND = "Laboratory"

WorkFn = Callable[[Pawn, Recipe, int], float]


@dataclass(frozen=True)
class HouseholdSpendingResult:
    """Daily household spending through a staffed Market."""

    revenue: int = 0
    bread_sold: int = 0
    sales_tax: int = 0
    unmet_bread_buyers: int = 0


@dataclass(frozen=True)
class MarketBreadDemand:
    """Bread demand that a staffed Market can or cannot fulfill today."""

    market_id: str | None = None
    buyers: int = 0
    sellable_bread: int = 0
    unmet_buyers: int = 0


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
    """Advance every staffed, built, input-satisfied building by one tick.

    A building's ``production_target`` (set by the governor's
    ``set_production_target`` lever) caps each named output good at ``amount`` in
    the stockpile: once the civilization already holds that much, the building
    stops making it. This makes the lever real - without it the governor could
    "set a target" that changed nothing. Untargeted goods stay unbounded.
    """
    refresh_storage_capacity(state)
    for building_id, building in state.buildings.items():
        recipe = building.recipe
        if not building.built or recipe is None or not building.staffed_by:
            continue
        if recipe.work_units <= 0:
            raise ValueError("Recipe work_units must be positive")
        cycles = int(building_output_rate(state, building_id, work_fn) // recipe.work_units)
        if cycles <= 0:
            continue
        outputs = _effective_outputs(recipe.outputs, state.research)
        input_limit = _input_limited_cycles(state.stockpile, recipe.inputs)
        if input_limit is not None:
            cycles = min(cycles, input_limit)
        target_limit = _target_limited_cycles(
            state.stockpile, outputs, building.production_target
        )
        if target_limit is not None:
            cycles = min(cycles, target_limit)
        storage_limit = _storage_limited_cycles(state.stockpile, recipe.inputs, outputs)
        if storage_limit is not None:
            cycles = min(cycles, storage_limit)
        if cycles <= 0:
            continue
        for good, amount in recipe.inputs.items():
            _validate_recipe_amount(good, amount)
            state.stockpile.remove(good, amount * cycles)
        for good, amount in outputs.items():
            _validate_recipe_amount(good, amount)
            state.stockpile.add(good, amount * cycles)


def research_tick(state: FactionState, *, work_fn: WorkFn = mood.effective_work) -> tuple[str, ...]:
    """Advance active research from staffed Laboratories; return completed techs.

    ``set_research`` selects ``state.research_target``. This function makes that
    policy real: each staffed Laboratory contributes whole research points using
    the same effective-work seam as production. Completing a tech records it in
    ``state.research`` and clears the active target/progress.
    """
    target = state.research_target
    if not target:
        return ()
    cost = RESEARCH_COSTS.get(target)
    if cost is None:
        state.research_target = None
        state.research_points = 0
        return ()
    if target in state.research:
        state.research_target = None
        state.research_points = 0
        return ()

    gained = 0
    for building_id, building in state.buildings.items():
        recipe = building.recipe
        if (
            building.kind != LABORATORY_KIND
            or not building.built
            or recipe is None
            or not building.staffed_by
        ):
            continue
        if recipe.work_units <= 0:
            raise ValueError("Recipe work_units must be positive")
        gained += int(building_output_rate(state, building_id, work_fn) // recipe.work_units)

    if gained <= 0:
        return ()
    state.research_points += gained
    if state.research_points < cost:
        return ()

    state.research = state.research + (target,)
    state.research_target = None
    state.research_points = 0
    return (target,)


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


def storage_fullness(state: FactionState) -> float | None:
    """Faction stockpile fullness in [0, 1], or None when storage is uncapped."""
    refresh_storage_capacity(state)
    return state.stockpile.fullness()


def refresh_storage_capacity(state: FactionState) -> int | None:
    """Apply built Storehouse capacity bonuses to the finite stockpile cap."""
    if state.stockpile.capacity is None and state.stockpile.base_capacity is None:
        return None
    base = state.stockpile.base_capacity
    if base is None:
        base = state.stockpile.capacity or 0
        state.stockpile.base_capacity = base
    storehouses = sum(
        1
        for building in state.buildings.values()
        if building.kind == STOREHOUSE_KIND and building.built
    )
    state.stockpile.capacity = base + storehouses * STOREHOUSE_CAPACITY_BONUS
    return state.stockpile.capacity


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


def pay_daily_wages(state: FactionState) -> int:
    """Pay one daily wage to assigned pawns, transferring treasury coin to them."""
    paid = 0
    for pawn in sorted(state.pawns.values(), key=lambda p: p.id):
        if pawn.assignment is None or state.coin < DAILY_WAGE:
            continue
        state.coin -= DAILY_WAGE
        pawn.coin += DAILY_WAGE
        paid += DAILY_WAGE
    return paid


def apply_market_sales(state: FactionState) -> int:
    """Sell a small bread surplus through a staffed Market; return treasury revenue."""
    if not _has_staffed_market(state):
        return 0
    bread = state.stockpile.counts.get(Good.BREAD, 0)
    reserve = len(state.pawns) * MARKET_BREAD_RESERVE_PER_PAWN
    surplus = max(0, bread - reserve)
    sold = min(MARKET_DAILY_BREAD_EXPORT_LIMIT, surplus)
    if sold <= 0:
        return 0
    state.stockpile.remove(Good.BREAD, sold)
    revenue = sold * MARKET_BREAD_PRICE
    state.coin += revenue
    return revenue


def apply_household_spending(state: FactionState) -> HouseholdSpendingResult:
    """Let pawns buy one bread each from a staffed Market above the reserve.

    This is the first household-spending slice, not a full private economy:
    wallets fund purchases, treasury receives Market revenue, and sales tax is
    collected from remaining buyer wallets when the tax rate produces whole coin.
    """
    demand = market_bread_demand(state)
    if demand.market_id is None:
        return HouseholdSpendingResult()

    buyers: list[Pawn] = [
        pawn
        for pawn in sorted(state.pawns.values(), key=lambda p: p.id)
        if pawn.coin >= MARKET_BREAD_PRICE
    ]
    if demand.sellable_bread <= 0 or not buyers:
        return HouseholdSpendingResult(unmet_bread_buyers=demand.unmet_buyers)

    served = buyers[: demand.sellable_bread]
    served_ids = {pawn.id for pawn in served}
    for pawn in sorted(state.pawns.values(), key=lambda p: p.id):
        if pawn.id not in served_ids:
            continue
        pawn.coin -= MARKET_BREAD_PRICE
        state.stockpile.remove(Good.BREAD, 1)

    revenue = len(served) * MARKET_BREAD_PRICE
    if revenue <= 0:
        return HouseholdSpendingResult(unmet_bread_buyers=demand.unmet_buyers)

    state.coin += revenue
    sales_tax = _collect_sales_tax(served, revenue, state.tax_rate)
    state.coin += sales_tax
    return HouseholdSpendingResult(
        revenue=revenue,
        bread_sold=len(served),
        sales_tax=sales_tax,
        unmet_bread_buyers=demand.unmet_buyers,
    )


def market_bread_demand(state: FactionState) -> MarketBreadDemand:
    """Return staffed-Market bread demand, supply, and unmet buyer count.

    This is the first district/service-pressure signal: if wallets want Market
    bread but the reserve leaves too little sellable stock, the governor and
    telemetry can report that the service loop is constrained instead of hiding
    it behind a quiet zero sale.
    """
    market = _staffed_market(state)
    if market is None:
        return MarketBreadDemand()
    buyers = sum(1 for pawn in state.pawns.values() if pawn.coin >= MARKET_BREAD_PRICE)
    bread = state.stockpile.counts.get(Good.BREAD, 0)
    reserve = len(state.pawns) * MARKET_BREAD_RESERVE_PER_PAWN
    sellable = max(0, bread - reserve)
    return MarketBreadDemand(
        market_id=market.id,
        buyers=buyers,
        sellable_bread=sellable,
        unmet_buyers=max(0, buyers - sellable),
    )


def apply_daily_tax(state: FactionState) -> int:
    """Add the day's tax income to ``state.coin``; return the amount added."""
    income = daily_tax_income(state) + _collect_income_tax(state)
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


def _target_limited_cycles(
    stockpile: Stockpile, outputs: dict[Good, int], targets: dict[Good, int]
) -> int | None:
    """Cycles allowed before any targeted output good reaches its stock target.

    A production target caps a good at ``amount`` in the stockpile. Because a
    cycle is atomic, the cap is the largest whole batch that does not overshoot
    the target, so the stock settles at the nearest multiple of the per-cycle
    yield at or below ``amount`` (never above it). A target already met yields 0
    cycles, so the building idles instead of overproducing. Returns ``None`` when
    no output good is targeted, leaving production unbounded as before.
    """
    if not targets:
        return None
    limits = []
    for good, per_cycle in outputs.items():
        target = targets.get(good)
        if target is None:
            continue
        if per_cycle <= 0:
            continue
        remaining = target - stockpile.counts.get(good, 0)
        limits.append(max(0, remaining) // per_cycle)
    if not limits:
        return None
    return min(limits)


def _storage_limited_cycles(
    stockpile: Stockpile, inputs: dict[Good, int], outputs: dict[Good, int]
) -> int | None:
    """Cycles allowed by finite stockpile capacity.

    Capacity is measured as total stored units. Only recipes that grow total
    stored units need limiting; transforms such as logs -> planks can still run
    while full because consuming inputs frees more capacity than the output uses.
    """
    available = stockpile.available_capacity()
    if available is None:
        return None
    net_growth = sum(outputs.values()) - sum(inputs.values())
    if net_growth <= 0:
        return None
    return available // net_growth


def _effective_outputs(outputs: dict[Good, int], research: tuple[str, ...]) -> dict[Good, int]:
    """Return recipe outputs after completed research effects."""
    if TECH_EFFICIENT_BAKING not in research or Good.BREAD not in outputs:
        return outputs
    adjusted = dict(outputs)
    adjusted[Good.BREAD] = adjusted[Good.BREAD] + 1
    return adjusted


def _has_staffed_market(state: FactionState) -> bool:
    return _staffed_market(state) is not None


def _staffed_market(state: FactionState):
    return next(
        (
            building
            for building in state.buildings.values()
            if building.kind == MARKET_KIND and building.built and bool(building.staffed_by)
        ),
        None,
    )


def _collect_income_tax(state: FactionState) -> int:
    tax_rate = max(0.0, state.tax_rate)
    if tax_rate <= 0.0:
        return 0
    collected = 0
    for pawn in sorted(state.pawns.values(), key=lambda p: p.id):
        tax = int(pawn.coin * tax_rate)
        if tax <= 0:
            continue
        pawn.coin -= tax
        collected += tax
    return collected


def _collect_sales_tax(buyers: list[Pawn], revenue: int, tax_rate: float) -> int:
    tax_due = int(revenue * max(0.0, tax_rate))
    if tax_due <= 0:
        return 0
    collected = 0
    for pawn in buyers:
        if tax_due <= 0:
            break
        tax = min(pawn.coin, tax_due)
        if tax <= 0:
            continue
        pawn.coin -= tax
        collected += tax
        tax_due -= tax
    return collected


def _validate_recipe_amount(good: Good, amount: int) -> None:
    if not isinstance(good, Good):
        raise TypeError("Recipe goods must use Good enum values")
    if amount <= 0:
        raise ValueError("Recipe amounts must be positive")
