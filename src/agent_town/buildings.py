from __future__ import annotations

from .core import Building, Good, Recipe


def create_building(kind: str, x: int, y: int) -> Building:
    normalized = kind.strip().lower()
    if normalized == "forester":
        return Building(
            kind="Forester",
            x=x,
            y=y,
            recipe=Recipe(inputs={}, outputs={Good.LOGS: 1}, work_units=1.0, skill="forestry"),
            job_slots=1,
            built=True,
        )
    if normalized == "sawmill":
        return Building(
            kind="Sawmill",
            x=x,
            y=y,
            recipe=Recipe(inputs={Good.LOGS: 2}, outputs={Good.PLANKS: 1}, work_units=1.0, skill="woodworking"),
            job_slots=1,
            built=True,
        )
    raise ValueError(f"Unknown building kind: {kind}")
