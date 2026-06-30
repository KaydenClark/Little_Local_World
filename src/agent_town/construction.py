"""Construction sites and hauling. [Track A]

A building is placed first as a ``ConstructionSite``: required goods are hauled
in from the stockpile, then work is spent down. When goods are delivered and
``work_remaining`` hits zero the site flips into a built ``Building``.

Phase 0 status: signatures frozen, bodies stubbed. Implemented in milestone A3.
"""

from __future__ import annotations

from . import buildings
from .core import Building, ConstructionSite, FactionState, Good


BUILDING_COIN_COSTS = {
    "Forester": 4,
    "Sawmill": 8,
    "Farm": 4,
    "Mill": 8,
    "Bakery": 10,
    "Water Well": 6,
    "Quarry": 6,
    "Laboratory": 12,
}


def building_coin_cost(kind: str) -> int:
    """Coin cost for placing a building construction site."""
    definition = buildings.building_def(kind)
    return BUILDING_COIN_COSTS[definition.kind]


def place_construction_site(
    state: FactionState, kind: str, x: int, y: int, *, site_id: str
) -> ConstructionSite:
    """Create a site for ``kind`` at (x, y) with its required goods + work."""
    if not site_id:
        raise ValueError("site_id is required")
    if site_id in state.construction_sites or site_id in state.buildings:
        raise ValueError(f"Duplicate site/building id: {site_id}")
    if state.grid is not None and not state.grid.in_bounds(x, y):
        raise ValueError(f"construction site ({x}, {y}) out of bounds")

    definition = buildings.building_def(kind)
    coin_cost = building_coin_cost(kind)
    if state.coin < coin_cost:
        raise ValueError(f"Insufficient coin: need {coin_cost}, have {state.coin}")

    site = ConstructionSite(
        id=site_id,
        building_kind=definition.kind,
        x=x,
        y=y,
        required=dict(definition.build_cost),
        delivered={},
        work_remaining=definition.build_work,
    )
    state.coin -= coin_cost
    state.construction_sites[site.id] = site
    return site


def haul_to_site(state: FactionState, site: ConstructionSite, good: Good, amount: int) -> int:
    """Move up to ``amount`` of ``good`` from stockpile into ``site``; return moved."""
    if amount <= 0:
        raise ValueError("haul amount must be positive")
    if good not in site.required:
        return 0
    missing = site.required[good] - site.delivered.get(good, 0)
    if missing <= 0:
        return 0
    moved = min(amount, missing, state.stockpile.counts.get(good, 0))
    if moved <= 0:
        return 0
    state.stockpile.remove(good, moved)
    site.delivered[good] = site.delivered.get(good, 0) + moved
    return moved


def goods_satisfied(site: ConstructionSite) -> bool:
    """Whether every required good has been delivered."""
    return all(site.delivered.get(good, 0) >= amount for good, amount in site.required.items())


def advance_construction(site: ConstructionSite, work: float) -> None:
    """Spend ``work`` against the site once its goods are satisfied."""
    if work < 0:
        raise ValueError("construction work must be non-negative")
    if not goods_satisfied(site):
        return
    site.work_remaining = max(0.0, site.work_remaining - work)


def complete_if_ready(state: FactionState, site: ConstructionSite) -> Building | None:
    """If goods delivered and work done, convert the site to a built Building."""
    if not goods_satisfied(site) or site.work_remaining > 0:
        return None
    building = buildings.make_building(
        site.building_kind,
        site.x,
        site.y,
        building_id=site.id,
        built=True,
    )
    state.buildings[building.id] = building
    state.construction_sites.pop(site.id, None)
    return building
