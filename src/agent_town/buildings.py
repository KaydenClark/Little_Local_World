"""Building definitions and job slots. [Track A]

The catalogue of building kinds: which recipe each runs, how many pawns it can
staff, and what it costs to construct. The three build-1 chains live here.

Phase 0 status: signatures frozen, bodies stubbed. Implemented in milestone A2.
"""

from __future__ import annotations

from dataclasses import dataclass

from .core import Building, Good, Recipe


@dataclass(frozen=True)
class BuildingDef:
    """Static definition of a building kind."""

    kind: str
    recipe: Recipe | None
    job_slots: int
    build_cost: dict[Good, int]
    build_work: float


# Populated in A2: Forester, Sawmill, Farm, Mill, Bakery, Quarry.
BUILDING_DEFS: dict[str, BuildingDef] = {}


def building_def(kind: str) -> BuildingDef:
    """Look up a building definition by kind."""
    raise NotImplementedError("building_def - Track A, milestone A2")


def make_building(kind: str, x: int, y: int, *, building_id: str, built: bool = True) -> Building:
    """Instantiate a Building of ``kind`` from its definition."""
    raise NotImplementedError("make_building - Track A, milestone A2")


def open_slots(building: Building) -> int:
    """How many unfilled job slots ``building`` has."""
    raise NotImplementedError("open_slots - Track A, milestone A2")
