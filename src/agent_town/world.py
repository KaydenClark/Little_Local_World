from __future__ import annotations

import random

from .core import Good, GridMap, ResourceNode


def create_grid_map(width: int, height: int) -> GridMap:
    return GridMap(width=width, height=height, tiles=("grass",) * (width * height))


def place_resource_nodes(grid: GridMap, seed: int) -> tuple[ResourceNode, ...]:
    total_tiles = grid.width * grid.height
    if total_tiles < 3:
        raise ValueError("Resource node placement requires at least 3 map tiles")

    rng = random.Random(seed)
    positions = rng.sample(range(total_tiles), 3)
    kinds = (Good.LOGS, Good.GRAIN, Good.STONE)
    return tuple(
        ResourceNode(
            kind=kind,
            amount=rng.randint(80, 140),
            x=position % grid.width,
            y=position // grid.width,
        )
        for kind, position in zip(kinds, positions)
    )
