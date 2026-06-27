from __future__ import annotations

from .core import Building, Good, Recipe


BUILDING_DEFINITIONS = {
    "forester": ("Forester", Recipe(inputs={}, outputs={Good.LOGS: 1}, work_units=1.0, skill="forestry")),
    "sawmill": ("Sawmill", Recipe(inputs={Good.LOGS: 2}, outputs={Good.PLANKS: 1}, work_units=1.0, skill="woodworking")),
    "farm": ("Farm", Recipe(inputs={}, outputs={Good.GRAIN: 1}, work_units=1.0, skill="farming")),
    "mill": ("Mill", Recipe(inputs={Good.GRAIN: 2}, outputs={Good.FLOUR: 1}, work_units=1.0, skill="milling")),
    "bakery": ("Bakery", Recipe(inputs={Good.FLOUR: 2}, outputs={Good.BREAD: 1}, work_units=1.0, skill="baking")),
    "quarry": ("Quarry", Recipe(inputs={}, outputs={Good.STONE: 1}, work_units=1.0, skill="mining")),
}


def create_building(kind: str, x: int, y: int) -> Building:
    normalized = kind.strip().lower()
    try:
        canonical_kind, recipe = BUILDING_DEFINITIONS[normalized]
    except KeyError as exc:
        raise ValueError(f"Unknown building kind: {kind}") from exc
    return Building(kind=canonical_kind, x=x, y=y, recipe=recipe, job_slots=1, built=True)
