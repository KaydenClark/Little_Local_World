from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


Point = tuple[float, float]


@dataclass(frozen=True)
class PathResult:
    waypoints: tuple[Point, ...]
    cost: float
    complete: bool = True


class PathfindingService(Protocol):
    def find_path(self, start: Point, goal: Point) -> PathResult:
        ...


class DirectPathfinder:
    def find_path(self, start: Point, goal: Point) -> PathResult:
        return PathResult(
            waypoints=(start, goal),
            cost=abs(goal[0] - start[0]) + abs(goal[1] - start[1]),
            complete=True,
        )
