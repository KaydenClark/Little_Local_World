from __future__ import annotations

from collections import defaultdict
from math import floor
from typing import Iterable, Protocol


class Positioned(Protocol):
    id: str
    x: float
    y: float


class SpatialIndex:
    def __init__(self, items: Iterable[Positioned], *, cell_size: float = 128.0) -> None:
        if cell_size <= 0:
            raise ValueError("cell_size must be greater than zero")
        self.cell_size = float(cell_size)
        self._cells: dict[tuple[int, int], list[Positioned]] = defaultdict(list)
        for item in items:
            self._cells[self._cell_for(item.x, item.y)].append(item)

    def nearby(self, x: float, y: float, radius: float) -> list[Positioned]:
        if radius < 0:
            raise ValueError("radius must be greater than or equal to zero")

        min_cell = self._cell_for(x - radius, y - radius)
        max_cell = self._cell_for(x + radius, y + radius)
        candidates: list[Positioned] = []
        for cell_y in range(min_cell[1], max_cell[1] + 1):
            for cell_x in range(min_cell[0], max_cell[0] + 1):
                candidates.extend(self._cells.get((cell_x, cell_y), ()))
        return candidates

    def _cell_for(self, x: float, y: float) -> tuple[int, int]:
        return floor(x / self.cell_size), floor(y / self.cell_size)
