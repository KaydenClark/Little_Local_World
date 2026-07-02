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

from . import mood, pawns, world
from .core import (
    BUILD1_NEEDS,
    Building,
    FactionState,
    Good,
    NEED_FOOD,
    NODE_EMPTY,
    NODE_GROWING,
    NODE_READY,
    Pawn,
    Recipe,
    Stockpile,
)

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

# --- Physical sourcing (BLUEPRINT "Physical sourcing" refinement) -------------
# Tier 0 faucets that must draw from a located map node instead of minting their
# output from labor alone. The Water Well is deliberately absent: its source is
# the aquifer (replenished mechanic), inexhaustible at colony scale.
SOURCED_BUILDING_GOODS: dict[str, Good] = {
    "Farm": Good.GRAIN,
    "Forester": Good.LOGS,
    "Quarry": Good.STONE,
}
# Planting a field consumes this much seed grain from the faction seed reserve.
PLANT_SEED_COST = 2
# Harvests divert grain back into the seed reserve until it holds this much,
# before any grain reaches the stockpile - each field is self-seeding.
SEED_RESERVE_TARGET = 8
# Grain harvested from a ripe field per completed work cycle. Harvesting is
# faster than the old mint-1-per-cycle faucet because the grain already exists
# on the field; the growing season is the rate limiter, not the sickle.
HARVEST_UNITS_PER_CYCLE = 4

# Farm field status codes (work arbiter, governor exceptions, and viewer).
FIELD_READY = "ready"  # ripe crop standing - harvest is real work
FIELD_GROWING = "growing"  # crop growing - nothing for a farmer to do here
FIELD_PLANTABLE = "plantable"  # empty field and seed on hand - planting is work
FIELD_NO_SEED = "no_seed"  # empty field, seed reserve short - blocked
FIELD_UNCLAIMED = "unclaimed"  # farm has not broken ground yet (will on first work)

# Bread a pawn eats per day at steady state, derived from the need model so the
# food cover metric tracks the real drain: a full day of food decay divided by
# the nutrition one loaf restores. Powers ``food_days_of_cover`` (the food twin
# of ``water_days_of_cover``) and the governor's ``low_food`` early warning.
BREAD_UNITS_PER_PAWN_DAY = (pawns.NEED_DECAY_PER_HOUR[NEED_FOOD] * 24.0) / pawns.BREAD_NUTRITION

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

    Production is **continuous, not lumpy**: each building banks its per-hour
    ``effective_work`` into ``production_progress`` and completes a whole cycle
    every time the bank reaches ``recipe.work_units``. This is what makes a
    slowed pawn count - a starving pawn at the hunger floor contributes a
    fraction of a cycle per hour and finishes one every few hours, instead of the
    old ``int(rate // work_units)`` flooring that silently dropped any per-hour
    work below one whole cycle to zero (which turned every food shortage into an
    unrecoverable spiral). ``production_progress`` only ever holds a *fractional*
    cycle: whole cycles the pawn banks are always spent from the bank, and any the
    limits (no inputs / target met) will not let it run are simply lost work, never
    accumulated into a burst it fires on resume.
    """
    refresh_storage_capacity(state)
    world.normalize_nodes(state.resource_nodes)
    for building_id, building in state.buildings.items():
        recipe = building.recipe
        if not building.built or recipe is None or not building.staffed_by:
            continue
        if recipe.work_units <= 0:
            raise ValueError("Recipe work_units must be positive")
        source_good = SOURCED_BUILDING_GOODS.get(building.kind)
        if source_good is Good.GRAIN:
            _farm_tick(state, building, work_fn)
            continue
        if source_good is not None:
            _extraction_tick(state, building, source_good, work_fn)
            continue
        building.production_progress += building_output_rate(state, building_id, work_fn)
        runnable = int(building.production_progress // recipe.work_units)
        if runnable <= 0:
            continue
        # Spend every whole cycle out of the bank so only the sub-cycle remainder
        # carries; cycles the limits block are lost, not banked (no resume burst).
        building.production_progress -= runnable * recipe.work_units
        cycles = runnable
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


def field_status(state: FactionState, building: Building) -> str:
    """What a Farm's field offers a farmer right now (read-only, no binding).

    One of :data:`FIELD_READY`, :data:`FIELD_GROWING`, :data:`FIELD_PLANTABLE`,
    :data:`FIELD_NO_SEED`, :data:`FIELD_UNCLAIMED`. The work arbiter treats
    ``ready``/``plantable``/``unclaimed`` as real work; ``growing`` and
    ``no_seed`` free the farmer for other jobs.
    """
    node = world.farm_field(state, building)
    if node is None:
        return FIELD_PLANTABLE if state.seed_grain >= PLANT_SEED_COST else FIELD_UNCLAIMED
    if node.state == NODE_GROWING:
        return FIELD_GROWING
    if node.state == NODE_READY and node.amount > 0:
        return FIELD_READY
    return FIELD_PLANTABLE if state.seed_grain >= PLANT_SEED_COST else FIELD_NO_SEED


def field_growth_fraction(state: FactionState, building: Building) -> float | None:
    """0..1 growth progress of a Farm's growing field, or None when not growing."""
    node = world.farm_field(state, building)
    if node is None or node.state != NODE_GROWING:
        return None
    return max(0.0, min(1.0, node.growth_progress / world.FIELD_GROWTH_HOURS))


def source_depleted(state: FactionState, building: Building) -> bool:
    """Whether an extractor (Forester/Quarry) has no standing source left."""
    source_good = SOURCED_BUILDING_GOODS.get(building.kind)
    if source_good is None or source_good is Good.GRAIN:
        return False
    return world.harvestable_amount(state, source_good) <= 0


def _banked_cycles(state: FactionState, building: Building, work_fn: WorkFn) -> int:
    """Bank this hour's effective work; return the whole cycles now spendable."""
    recipe = building.recipe
    building.production_progress += building_output_rate(state, building.id, work_fn)
    runnable = int(building.production_progress // recipe.work_units)
    if runnable > 0:
        building.production_progress -= runnable * recipe.work_units
    return runnable


def _units_allowed(stockpile: Stockpile, good: Good, targets: dict[Good, int]) -> int | None:
    """How many single units of ``good`` may enter storage (target + capacity)."""
    limits: list[int] = []
    target = targets.get(good)
    if target is not None:
        limits.append(max(0, target - stockpile.counts.get(good, 0)))
    available = stockpile.available_capacity()
    if available is not None:
        limits.append(available)
    return min(limits) if limits else None


def _farm_tick(state: FactionState, building: Building, work_fn: WorkFn) -> None:
    """Cultivated production: plant (labor + seed) -> grow (time) -> harvest (labor).

    The field node is the source of grain, not the farmer's hands: an EMPTY
    field yields nothing however hard the pawn works, and a GROWING field needs
    time, not labor (the work arbiter frees the farmer meanwhile). Harvested
    grain first tops up the faction seed reserve (each field is self-seeding),
    then enters the stockpile through the conservation ledger - the field is the
    named external source. Grain that storage cannot take stays standing on the
    field rather than vanishing.
    """
    cycles = _banked_cycles(state, building, work_fn)
    if cycles <= 0:
        return
    field = world.claim_farm_field(state, building)

    if field.state == NODE_EMPTY:
        if state.seed_grain >= PLANT_SEED_COST:
            state.seed_grain -= PLANT_SEED_COST
            field.state = NODE_GROWING
            field.growth_progress = 0.0
        # Remaining cycles this hour are lost work - you cannot harvest a field
        # you just planted, and no-seed idling is surfaced as an exception.
        return

    if field.state != NODE_READY or field.amount <= 0:
        return

    want = cycles * HARVEST_UNITS_PER_CYCLE
    seed_take = min(field.amount, want, max(0, SEED_RESERVE_TARGET - state.seed_grain))
    if seed_take > 0:
        world.harvest_node(field, seed_take)
        state.seed_grain += seed_take
        want -= seed_take
    if want <= 0 or field.amount <= 0:
        return
    allowed = _units_allowed(state.stockpile, Good.GRAIN, building.production_target)
    units = min(want, field.amount) if allowed is None else min(want, field.amount, allowed)
    if units <= 0:
        return
    taken = world.harvest_node(field, units)
    if taken > 0:
        state.stockpile.add(Good.GRAIN, taken)


def _extraction_tick(state: FactionState, building: Building, good: Good, work_fn: WorkFn) -> None:
    """Extracted production: labor harvests real standing nodes, nearest-first.

    Output per cycle matches the recipe, but every unit now leaves a located
    node: a Quarry mines its outcrops dry (stone never regrows - the face is
    mined out) and a Forester's stands thin out and slowly recover
    (``world.advance_nodes``). No nodes left means no output, surfaced as a
    ``node_depleted`` exception rather than silent free goods.
    """
    cycles = _banked_cycles(state, building, work_fn)
    if cycles <= 0:
        return
    per_cycle = building.recipe.outputs.get(good, 0)
    if per_cycle <= 0:
        return
    want = cycles * per_cycle
    allowed = _units_allowed(state.stockpile, good, building.production_target)
    if allowed is not None:
        want = min(want, allowed)
    standing = world.harvestable_amount(state, good)
    want = min(want, standing)
    if want <= 0:
        return
    taken = world.harvest_from_nodes(state, good, want, near=(building.x, building.y))
    if taken > 0:
        state.stockpile.add(good, taken)


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


def food_days_of_cover(state: FactionState) -> float:
    """How many pawn-days of eating the current bread stockpile can cover.

    The food twin of :func:`water_days_of_cover`, using only finished bread (the
    thing pawns can actually eat) - grain and flour in the pipeline are latent,
    not edible, so they are deliberately excluded. This is the early-warning
    number the governor acts on before the reserve reaches zero.
    """
    population = len(state.pawns)
    if population == 0:
        return float("inf")
    return state.stockpile.counts.get(Good.BREAD, 0) / (population * BREAD_UNITS_PER_PAWN_DAY)


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
