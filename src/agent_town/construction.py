"""Construction sites and hauling. [Track A]

A building is placed first as a ``ConstructionSite``: required goods are hauled
in from the stockpile, then work is spent down. When goods are delivered and
``work_remaining`` hits zero the site flips into a built ``Building``.

Phase 0 status: signatures frozen, bodies stubbed. Implemented in milestone A3.
"""

from __future__ import annotations

from .core import Building, ConstructionSite, FactionState, Good


def place_construction_site(
    state: FactionState, kind: str, x: int, y: int, *, site_id: str
) -> ConstructionSite:
    """Create a site for ``kind`` at (x, y) with its required goods + work."""
    raise NotImplementedError("place_construction_site - Track A, milestone A3")


def haul_to_site(state: FactionState, site: ConstructionSite, good: Good, amount: int) -> int:
    """Move up to ``amount`` of ``good`` from stockpile into ``site``; return moved."""
    raise NotImplementedError("haul_to_site - Track A, milestone A3")


def goods_satisfied(site: ConstructionSite) -> bool:
    """Whether every required good has been delivered."""
    raise NotImplementedError("goods_satisfied - Track A, milestone A3")


def advance_construction(site: ConstructionSite, work: float) -> None:
    """Spend ``work`` against the site once its goods are satisfied."""
    raise NotImplementedError("advance_construction - Track A, milestone A3")


def complete_if_ready(state: FactionState, site: ConstructionSite) -> Building | None:
    """If goods delivered and work done, convert the site to a built Building."""
    raise NotImplementedError("complete_if_ready - Track A, milestone A3")
