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


BUILDING_DEFS: dict[str, BuildingDef] = {
    "forester": BuildingDef(
        kind="Forester",
        recipe=Recipe(inputs={}, outputs={Good.LOGS: 1}, work_units=1.0, skill="forestry"),
        job_slots=1,
        build_cost={Good.PLANKS: 4, Good.STONE: 2},
        build_work=4.0,
    ),
    "sawmill": BuildingDef(
        kind="Sawmill",
        recipe=Recipe(inputs={Good.LOGS: 2}, outputs={Good.PLANKS: 1}, work_units=1.0, skill="woodworking"),
        job_slots=1,
        build_cost={Good.PLANKS: 4, Good.STONE: 2},
        build_work=4.0,
    ),
    "farm": BuildingDef(
        kind="Farm",
        recipe=Recipe(inputs={}, outputs={Good.GRAIN: 1}, work_units=1.0, skill="farming"),
        job_slots=1,
        build_cost={Good.PLANKS: 4, Good.STONE: 2},
        build_work=4.0,
    ),
    "mill": BuildingDef(
        kind="Mill",
        recipe=Recipe(inputs={Good.GRAIN: 2}, outputs={Good.FLOUR: 1}, work_units=1.0, skill="milling"),
        job_slots=1,
        build_cost={Good.PLANKS: 4, Good.STONE: 2},
        build_work=4.0,
    ),
    "bakery": BuildingDef(
        kind="Bakery",
        recipe=Recipe(inputs={Good.FLOUR: 2}, outputs={Good.BREAD: 4}, work_units=1.0, skill="baking"),
        job_slots=1,
        build_cost={Good.PLANKS: 4, Good.STONE: 2},
        build_work=4.0,
    ),
    "water well": BuildingDef(
        kind="Water Well",
        recipe=Recipe(inputs={}, outputs={Good.WATER: 3}, work_units=1.0, skill="water"),
        job_slots=1,
        build_cost={Good.PLANKS: 4, Good.STONE: 2},
        build_work=4.0,
    ),
    "quarry": BuildingDef(
        kind="Quarry",
        recipe=Recipe(inputs={}, outputs={Good.STONE: 1}, work_units=1.0, skill="mining"),
        job_slots=1,
        build_cost={Good.PLANKS: 4, Good.STONE: 2},
        build_work=4.0,
    ),
    "laboratory": BuildingDef(
        kind="Laboratory",
        recipe=Recipe(inputs={}, outputs={}, work_units=1.0, skill="research"),
        job_slots=1,
        build_cost={Good.PLANKS: 8, Good.STONE: 4},
        build_work=6.0,
    ),
    "market": BuildingDef(
        kind="Market",
        recipe=Recipe(inputs={}, outputs={}, work_units=1.0, skill="commerce"),
        job_slots=1,
        build_cost={Good.PLANKS: 8, Good.STONE: 4},
        build_work=6.0,
    ),
    "storehouse": BuildingDef(
        kind="Storehouse",
        recipe=None,
        job_slots=0,
        build_cost={Good.PLANKS: 10, Good.STONE: 6},
        build_work=6.0,
    ),
}


def building_def(kind: str) -> BuildingDef:
    """Look up a building definition by kind."""
    normalized = kind.strip().lower().replace("_", " ").replace("-", " ")
    try:
        return BUILDING_DEFS[normalized]
    except KeyError as exc:
        raise ValueError(f"Unknown building kind: {kind}") from exc


def is_known_kind(kind: str) -> bool:
    """Whether ``kind`` names a real building in the catalogue.

    A non-raising check for callers that must validate an *untrusted* kind
    string before committing to it - the LLM governor's ``place_building``
    action is the reason this exists: a live model can propose a plausible but
    nonexistent kind (e.g. "bread storage"), and without this check that string
    reaches construction and crashes on the first ``building_def`` lookup.
    """
    if not kind:
        return False
    normalized = kind.strip().lower().replace("_", " ").replace("-", " ")
    return normalized in BUILDING_DEFS


def make_building(kind: str, x: int, y: int, *, building_id: str, built: bool = True) -> Building:
    """Instantiate a Building of ``kind`` from its definition."""
    if not building_id:
        raise ValueError("building_id is required")
    definition = building_def(kind)
    return Building(
        id=building_id,
        kind=definition.kind,
        x=x,
        y=y,
        recipe=definition.recipe,
        job_slots=definition.job_slots,
        built=built,
    )


def open_slots(building: Building) -> int:
    """How many unfilled job slots ``building`` has."""
    return max(0, building.job_slots - len(building.staffed_by))
