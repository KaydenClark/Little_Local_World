from __future__ import annotations

from .buildings import create_building
from .core import ConstructionSite, FactionState, Good


CONSTRUCTION_REQUIRED = {Good.PLANKS: 4, Good.STONE: 2}
CONSTRUCTION_WORK_UNITS = 4.0
BUILDING_COSTS = {
    "Forester": 4,
    "Sawmill": 8,
    "Farm": 4,
    "Mill": 8,
    "Bakery": 10,
    "Quarry": 6,
}


def building_cost(building_kind: str) -> int:
    building = create_building(building_kind, 0, 0)
    return BUILDING_COSTS[building.kind]


def place_building(state: FactionState, building_kind: str, x: int, y: int) -> ConstructionSite:
    cost = building_cost(building_kind)
    if state.coin < cost:
        raise ValueError(f"Insufficient coin: need {cost}, have {state.coin}")

    site = create_construction_site(building_kind, x, y)
    state.coin -= cost
    state.construction_sites.append(site)
    return site


def create_construction_site(building_kind: str, x: int, y: int) -> ConstructionSite:
    building = create_building(building_kind, x, y)
    return ConstructionSite(
        building_kind=building.kind,
        required=dict(CONSTRUCTION_REQUIRED),
        delivered={},
        work_remaining=CONSTRUCTION_WORK_UNITS,
        x=x,
        y=y,
    )


def advance_construction(state: FactionState, site: ConstructionSite, dt: float) -> None:
    if dt <= 0:
        return

    _deliver_available_goods(state, site)
    if not _all_goods_delivered(site):
        return

    site.work_remaining = max(0.0, site.work_remaining - dt)
    if site.work_remaining > 0:
        return

    building = create_building(site.building_kind, site.x, site.y)
    building.built = True
    state.buildings.append(building)
    if site in state.construction_sites:
        state.construction_sites.remove(site)


def _deliver_available_goods(state: FactionState, site: ConstructionSite) -> None:
    for good, required_amount in site.required.items():
        if not isinstance(good, Good):
            raise TypeError("Construction goods must use Good enum values")
        if required_amount <= 0:
            raise ValueError("Construction required amounts must be positive")

        delivered_amount = site.delivered.get(good, 0)
        missing = required_amount - delivered_amount
        if missing <= 0:
            continue

        available = state.stockpile.counts.get(good, 0)
        delivered_now = min(missing, available)
        if delivered_now <= 0:
            continue

        state.stockpile.remove(good, delivered_now)
        site.delivered[good] = delivered_amount + delivered_now


def _all_goods_delivered(site: ConstructionSite) -> bool:
    return all(site.delivered.get(good, 0) >= amount for good, amount in site.required.items())
