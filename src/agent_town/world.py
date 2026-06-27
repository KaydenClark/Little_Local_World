"""World: tile map and resource nodes. [Track A]

Owns the spatial substrate the economy sits on: a deterministic ``GridMap`` of
terrain tiles plus the harvestable ``ResourceNode`` list (trees -> logs, fields
-> grain, stone outcrops -> stone).

Phase 0 status: signatures frozen, bodies stubbed. Implemented in milestone A1.
"""

from __future__ import annotations

from .core import GridMap, Good, ResourceNode

# Terrain tile kinds used by build 1.
TILE_GRASS = "grass"
TILE_TREE = "tree"
TILE_FIELD = "field"
TILE_STONE = "stone"
TILE_WATER = "water"


def generate_map(width: int, height: int, *, seed: int = 0) -> GridMap:
    """Build a deterministic terrain grid for a ``seed``."""
    raise NotImplementedError("generate_map - Track A, milestone A1")


def scatter_resource_nodes(grid: GridMap, *, seed: int = 0) -> list[ResourceNode]:
    """Place harvestable nodes on the grid deterministically for a ``seed``."""
    raise NotImplementedError("scatter_resource_nodes - Track A, milestone A1")


def create_world(width: int, height: int, *, seed: int = 0) -> tuple[GridMap, list[ResourceNode]]:
    """Convenience: map + nodes for a seed."""
    raise NotImplementedError("create_world - Track A, milestone A1")


def harvest_node(node: ResourceNode, amount: int) -> int:
    """Deplete up to ``amount`` from ``node``; return the amount actually taken."""
    raise NotImplementedError("harvest_node - Track A, milestone A1")


def nodes_of_kind(nodes: list[ResourceNode], kind: Good) -> list[ResourceNode]:
    """All non-empty nodes yielding ``kind``."""
    raise NotImplementedError("nodes_of_kind - Track A, milestone A1")
