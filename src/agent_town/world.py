from __future__ import annotations

from .core import GridMap, ResourceNode


def create_grid_map(width: int, height: int) -> GridMap:
    raise NotImplementedError("Grid map generation is implemented in Track A1")


def place_resource_nodes(grid: GridMap, seed: int) -> tuple[ResourceNode, ...]:
    raise NotImplementedError("Resource node placement is implemented in Track A1")
