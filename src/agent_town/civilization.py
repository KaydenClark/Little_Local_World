"""Default civilization scenario for the viewer (integration milestone I3).

Seeds a deterministic build-1 ``FactionState`` the engine can step and the
viewer can render: a tile world with resource nodes, the build-1 production
buildings placed on the grid, and a dozen pawns skilled for them. It mirrors the
seeded I1 survival civilization so the rendered civilization also sustains under the fallback
governor.
"""

from __future__ import annotations

from . import buildings, pawns, world
from .core import FactionState, Good, Pawn

CIVILIZATION_WIDTH = 24
CIVILIZATION_HEIGHT = 16

# (kind, tile_x, tile_y) for the starting build-1 buildings. Positions are
# visual only - build-1 recipes do not consume the underlying tile/node.
STARTING_BUILDINGS: tuple[tuple[str, int, int], ...] = (
    ("Forester", 3, 3),
    ("Sawmill", 6, 3),
    ("Quarry", 9, 3),
    ("Farm", 3, 8),
    ("Farm", 6, 8),
    ("Farm", 9, 8),
    ("Mill", 14, 5),
    ("Mill", 17, 5),
    ("Bakery", 14, 10),
    ("Bakery", 17, 10),
)

# (name, primary skill) for the dozen starting pawns. Skills line up with the
# building set so the fallback governor can staff every slot.
STARTING_PAWNS: tuple[tuple[str, str], ...] = (
    ("Forester Fen", "forestry"),
    ("Sawyer Bram", "woodworking"),
    ("Mason Cole", "mining"),
    ("Farmer Wren", "farming"),
    ("Farmer Pell", "farming"),
    ("Farmer Tansy", "farming"),
    ("Miller Odi", "milling"),
    ("Miller Sage", "milling"),
    ("Baker Rye", "baking"),
    ("Baker Pim", "baking"),
    ("Hand Mly", "farming"),
    ("Hand Dob", "baking"),
)

# Mood-positive traits keep the seeded civilization alive under the fallback governor,
# matching the I1 survival civilization.
PAWN_TRAITS = ("industrious", "optimist", "tough")


def create_default_civilization(*, seed: int = 7) -> FactionState:
    """Build the seeded build-1 civilization the viewer renders and the engine steps."""
    grid, nodes = world.create_world(CIVILIZATION_WIDTH, CIVILIZATION_HEIGHT, seed=seed)
    state = FactionState(
        coin=20,
        tax_rate=0.2,
        time_of_day=7,
        grid=grid,
        resource_nodes=nodes,
    )
    state.stockpile.add(Good.BREAD, 12)

    counts: dict[str, int] = {}
    for kind, x, y in STARTING_BUILDINGS:
        counts[kind] = counts.get(kind, 0) + 1
        building = buildings.make_building(kind, x, y, building_id=f"{kind.lower()}{counts[kind]}")
        state.buildings[building.id] = building

    for index, (name, skill) in enumerate(STARTING_PAWNS):
        px = 2 + (index % 6) * 3
        py = 13 - (index // 6)
        state.pawns[f"pawn{index:02d}"] = Pawn(
            id=f"pawn{index:02d}",
            name=name,
            skills={skill: 19},
            traits=PAWN_TRAITS,
            needs={need: 1.0 for need in pawns.BUILD1_NEEDS},
            mood=80.0,
            schedule="default",
            x=px,
            y=py,
        )

    return state
