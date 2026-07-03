"""World: tile map and resource nodes. [Track A]

Owns the spatial substrate the economy sits on: a deterministic ``GridMap`` of
terrain tiles plus the harvestable ``ResourceNode`` list (trees -> logs, fields
-> grain, stone outcrops -> stone).

Physical sourcing (2026-07-02): nodes are no longer decorative. Every Tier 0
faucet draws from a located node with one of three mechanics
(see BLUEPRINT.md "Physical sourcing"):

- **Cultivated** (Farm -> grain): a field node cycles EMPTY -> GROWING -> READY.
  Planting is labor and consumes seed grain; growth is elapsed time (ticked here
  by :func:`advance_nodes`, whether or not a farmer is present); harvest is labor.
- **Extracted** (Forester -> logs, Quarry -> stone): harvesting depletes the
  node. Tree nodes regrow slowly toward ``max_amount``; stone does not regrow -
  a mined-out quarry face stays depleted (``node_depleted`` exception).
- **Replenished** (Water Well): the aquifer is inexhaustible at colony scale, so
  wells intentionally have no node - the "location, not a spigot" property holds
  without inventing an artificial water shortage.
"""

from __future__ import annotations

import random

from .core import (
    Building,
    FactionState,
    GridMap,
    Good,
    NODE_EMPTY,
    NODE_GROWING,
    NODE_READY,
    ResourceNode,
)

# Terrain tile kinds used by build 1.
TILE_GRASS = "grass"
TILE_TREE = "tree"
TILE_FIELD = "field"
TILE_STONE = "stone"
TILE_WATER = "water"

# --- Physical-sourcing constants ---------------------------------------------
# One crop takes a full game day to grow. Grain cannot appear faster than a
# growing season, regardless of how many farmers stand around the field.
FIELD_GROWTH_HOURS = 24
# A ripe field holds this much grain (one harvest's worth).
FIELD_YIELD = 24
# Trees regrow: a felled stand recovers one log every 4 hours, up to max_amount.
TREE_REGROW_PER_HOUR = 0.25

# Goods whose nodes are cultivated fields (plant/grow/harvest lifecycle).
CULTIVATED_GOODS = frozenset({Good.GRAIN})
# Goods whose extracted nodes regrow over time (renewable but slow).
REGROWING_GOODS = frozenset({Good.LOGS})


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
    nodes = [
        ResourceNode(
            kind=kind,
            amount=rng.randint(80, 140),
            x=position % grid.width,
            y=position // grid.width,
        )
        for kind, position in zip(kinds, positions)
    ]
    normalize_nodes(nodes)
    return nodes


def create_world(width: int, height: int, *, seed: int = 0) -> tuple[GridMap, list[ResourceNode]]:
    """Convenience: map + nodes for a seed."""
    grid = generate_map(width, height, seed=seed)
    return grid, scatter_resource_nodes(grid, seed=seed)


def normalize_nodes(nodes: list[ResourceNode]) -> None:
    """Give every node an id, a capacity, and a consistent lifecycle state.

    Idempotent and cheap, so the engine can call it every hour and hand-built
    test states keep working: nodes made before physical sourcing (no id, no
    max_amount) are adopted in place. Cultivated (grain) nodes are clamped to
    one harvest's worth (:data:`FIELD_YIELD`) - the old scatter rolled 80-140
    "grain" which is now several seasons, not one standing crop.
    """
    used_ids = {node.id for node in nodes if node.id}
    counter = 1
    for node in nodes:
        if not node.id:
            while f"node-{counter:02d}" in used_ids:
                counter += 1
            node.id = f"node-{counter:02d}"
            used_ids.add(node.id)
        if node.kind in CULTIVATED_GOODS:
            node.max_amount = FIELD_YIELD
            node.amount = min(node.amount, FIELD_YIELD)
        elif node.max_amount <= 0:
            node.max_amount = max(node.amount, 0)
        if node.state == NODE_READY and node.amount <= 0:
            node.state = NODE_EMPTY
        elif node.state == NODE_EMPTY and node.amount > 0:
            node.state = NODE_READY


def advance_nodes(state: FactionState) -> None:
    """One hour of node time: field growth and tree regrowth.

    Growth does not require a pawn's attention - only planting and harvesting
    are labor. A field keeps growing while its farmer works the Mill; a felled
    tree stand recovers on its own. Stone never regrows.
    """
    normalize_nodes(state.resource_nodes)
    for node in state.resource_nodes:
        if node.kind in CULTIVATED_GOODS:
            if node.state == NODE_GROWING:
                node.growth_progress += 1.0
                if node.growth_progress >= FIELD_GROWTH_HOURS:
                    node.state = NODE_READY
                    node.amount = node.max_amount or FIELD_YIELD
                    node.growth_progress = 0.0
        elif node.kind in REGROWING_GOODS and node.amount < node.max_amount:
            node.growth_progress += TREE_REGROW_PER_HOUR
            regrown = int(node.growth_progress)
            if regrown > 0:
                node.growth_progress -= regrown
                node.amount = min(node.max_amount, node.amount + regrown)
                if node.amount > 0 and node.state == NODE_EMPTY:
                    node.state = NODE_READY


def harvest_node(node: ResourceNode, amount: int) -> int:
    """Deplete up to ``amount`` from ``node``; return the amount actually taken."""
    if amount <= 0:
        raise ValueError("harvest amount must be positive")
    harvested = min(amount, node.amount)
    node.amount -= harvested
    if node.amount <= 0:
        node.state = NODE_EMPTY
        node.growth_progress = 0.0
    return harvested


def nodes_of_kind(nodes: list[ResourceNode], kind: Good) -> list[ResourceNode]:
    """All non-empty nodes yielding ``kind``."""
    if not isinstance(kind, Good):
        raise TypeError("resource node kind must use Good enum values")
    return [node for node in nodes if node.kind == kind and node.amount > 0]


def node_by_id(state: FactionState, node_id: str | None) -> ResourceNode | None:
    """The node with ``node_id``, or None."""
    if not node_id:
        return None
    for node in state.resource_nodes:
        if node.id == node_id:
            return node
    return None


def harvestable_amount(state: FactionState, kind: Good) -> int:
    """Total standing amount across every node of ``kind`` (extractor supply)."""
    return sum(node.amount for node in state.resource_nodes if node.kind == kind)


def harvest_from_nodes(state: FactionState, kind: Good, amount: int, *, near: tuple[int, int]) -> int:
    """Harvest up to ``amount`` of ``kind`` across nodes, nearest-first.

    Extractors (Forester, Quarry) share the map's nodes rather than owning one,
    so depletion spreads outward from the building. Deterministic: ties break on
    node id. Returns the amount actually taken.
    """
    if amount <= 0:
        return 0
    remaining = amount
    candidates = sorted(
        (node for node in state.resource_nodes if node.kind == kind and node.amount > 0),
        key=lambda n: (max(abs(n.x - near[0]), abs(n.y - near[1])), n.id),
    )
    for node in candidates:
        if remaining <= 0:
            break
        remaining -= harvest_node(node, remaining)
    return amount - remaining


def farm_field(state: FactionState, building: Building) -> ResourceNode | None:
    """The field node a Farm owns, or None if it has not claimed one yet.

    Read-only lookup - safe for the viewer and the work arbiter. The engine's
    production path uses :func:`claim_farm_field` to bind or break new ground.
    """
    return node_by_id(state, building.source_node_id)


def claim_farm_field(state: FactionState, building: Building) -> ResourceNode:
    """Bind a Farm to its field: nearest unclaimed grain node, else new ground.

    A claimed wild field keeps whatever crop is standing on it. Breaking new
    ground next to the farm creates an EMPTY field (nothing grows on it until a
    farmer plants seed) - this is what makes the dig-out honest: a brand-new
    Farm cannot mint grain the hour it opens.
    """
    normalize_nodes(state.resource_nodes)
    existing = farm_field(state, building)
    if existing is not None:
        return existing
    claimed_ids = {
        b.source_node_id for b in state.buildings.values() if b.source_node_id
    }
    candidates = sorted(
        (
            node
            for node in state.resource_nodes
            if node.kind == Good.GRAIN and node.id not in claimed_ids
        ),
        key=lambda n: (max(abs(n.x - building.x), abs(n.y - building.y)), n.id),
    )
    if candidates:
        field = candidates[0]
    else:
        x, y = building.x + 1, building.y + 1
        if state.grid is not None:
            x = max(0, min(state.grid.width - 1, x))
            y = max(0, min(state.grid.height - 1, y))
        field = create_field_node(state, x, y, field_id=f"field-{building.id}")
    building.source_node_id = field.id
    return field


def create_field_node(
    state: FactionState, x: int, y: int, *, field_id: str, ripe: bool = False
) -> ResourceNode:
    """Break new cropland at (x, y): an owned field node, EMPTY unless ``ripe``."""
    field = ResourceNode(
        kind=Good.GRAIN,
        amount=FIELD_YIELD if ripe else 0,
        x=x,
        y=y,
        id=field_id,
        state=NODE_READY if ripe else NODE_EMPTY,
        max_amount=FIELD_YIELD,
    )
    state.resource_nodes.append(field)
    return field
