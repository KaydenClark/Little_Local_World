"""World: tile map and resource nodes. [Track A]

Owns the spatial substrate the economy sits on: a deterministic ``GridMap`` of
terrain tiles plus the harvestable ``ResourceNode`` list (trees -> logs, fields
-> grain, stone outcrops -> stone).

Phase 0 status: signatures frozen, bodies stubbed. Implemented in milestone A1.
"""

from __future__ import annotations

import random

from .core import GridMap, Good, ResourceNode

# Terrain tile kinds used by build 1.
TILE_GRASS = "grass"
TILE_TREE = "tree"
TILE_FIELD = "field"
TILE_STONE = "stone"
TILE_WATER = "water"


def generate_map(width: int, height: int, *, seed: int = 0) -> GridMap:
    """Build a deterministic terrain grid for a ``seed``."""
    if width <= 0 or height <= 0:
        raise ValueError("map width and height must be positive")

    tiles = [[TILE_GRASS for _x in range(width)] for _y in range(height)]
    total_tiles = width * height
    rng = random.Random(seed)

    def set_sample(kind: str, count: int) -> None:
        count = min(count, total_tiles)
        for position in rng.sample(range(total_tiles), count):
            tiles[position // width][position % width] = kind

    set_sample(TILE_WATER, max(1, total_tiles // 24))
    set_sample(TILE_TREE, max(1, total_tiles // 12))
    set_sample(TILE_FIELD, max(1, total_tiles // 16))
    set_sample(TILE_STONE, max(1, total_tiles // 18))
    return GridMap(width=width, height=height, tiles=tuple(tuple(row) for row in tiles))


def scatter_resource_nodes(grid: GridMap, *, seed: int = 0) -> list[ResourceNode]:
    """Place harvestable nodes on the grid deterministically for a ``seed``."""
    total_tiles = grid.width * grid.height
    if total_tiles < 3:
        raise ValueError("resource node placement requires at least 3 map tiles")

    rng = random.Random(seed)
    positions = rng.sample(range(total_tiles), 3)
    kinds = (Good.LOGS, Good.GRAIN, Good.STONE)
    return [
        ResourceNode(
            kind=kind,
            amount=rng.randint(80, 140),
            x=position % grid.width,
            y=position // grid.width,
        )
        for kind, position in zip(kinds, positions)
    ]


def create_world(width: int, height: int, *, seed: int = 0) -> tuple[GridMap, list[ResourceNode]]:
    """Convenience: map + nodes for a seed."""
    grid = generate_map(width, height, seed=seed)
    return grid, scatter_resource_nodes(grid, seed=seed)


def harvest_node(node: ResourceNode, amount: int) -> int:
    """Deplete up to ``amount`` from ``node``; return the amount actually taken."""
    if amount <= 0:
        raise ValueError("harvest amount must be positive")
    harvested = min(amount, node.amount)
    node.amount -= harvested
    return harvested


def nodes_of_kind(nodes: list[ResourceNode], kind: Good) -> list[ResourceNode]:
    """All non-empty nodes yielding ``kind``."""
    if not isinstance(kind, Good):
        raise TypeError("resource node kind must use Good enum values")
    return [node for node in nodes if node.kind == kind and node.amount > 0]
