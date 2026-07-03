"""Default civilization scenario for the viewer (integration milestone I3).

Seeds a deterministic build-1 ``FactionState`` the engine can step and the
viewer can render: a tile world with resource nodes, the build-1 production
buildings placed on the grid, and a dozen pawns skilled for them. It mirrors the
seeded I1 survival civilization so the rendered civilization also sustains under the fallback
governor.
"""

from __future__ import annotations

from . import buildings, pawns, world
from .core import FactionState, Good, NODE_GROWING, Pawn

CIVILIZATION_WIDTH = 24
CIVILIZATION_HEIGHT = 16
DEFAULT_STOCKPILE_CAPACITY = 240
# Seed grain "brought from the old country": enough to plant every starting
# field once (4 farms x PLANT_SEED_COST 2) before harvest diversion tops the
# reserve back up. Physical sourcing bootstrap - never purchased.
STARTING_SEED_GRAIN = 8
# Starting fields are staggered through the growth cycle so harvests arrive in
# a rolling rhythm instead of one synchronized burst: one field ripe on day 0,
# the rest partway grown, spaced roughly a quarter-season apart.
FIELD_STAGGER_HOURS = (None, 18, 12, 6)  # None = starts ripe
# Surplus-producer ceilings. Primary producers (water, logs, planks, stone) have
# weak or bursty sinks, so with the finite stockpile cap (above) an uncapped
# producer floods shared storage and crowds the food chain out until the civ
# starves - both merge lines carried this latently (integration shipped the cap,
# the crisis line shipped the sustain floor, neither balanced the producers). A
# starting `production_target` (a ceiling: production halts once stock reaches it)
# keeps each surplus good at a working buffer and leaves ~90 units of headroom for
# grain/flour/bread. Buffers stay well above construction's needs (~4 planks / 2
# stone per building). The governor can still retarget any of them.
SURPLUS_PRODUCTION_TARGETS: dict[str, tuple[Good, int]] = {
    "Water Well": (Good.WATER, 48),
    "Forester": (Good.LOGS, 24),
    "Sawmill": (Good.PLANKS, 40),
    "Quarry": (Good.STONE, 40),
}

# (kind, tile_x, tile_y) for the starting build-1 buildings. Positions are
# visual only - build-1 recipes do not consume the underlying tile/node.
STARTING_BUILDINGS: tuple[tuple[str, int, int], ...] = (
    ("Forester", 3, 3),
    ("Sawmill", 6, 3),
    ("Quarry", 9, 3),
    ("Farm", 3, 8),
    ("Farm", 6, 8),
    ("Farm", 9, 8),
    ("Farm", 12, 8),
    ("Mill", 14, 5),
    ("Mill", 17, 5),
    ("Bakery", 14, 10),
    ("Bakery", 17, 10),
    ("Water Well", 20, 8),
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
    ("Wellkeeper Vale", "water"),
)

# Mood-positive traits keep the seeded civilization alive under the fallback governor,
# matching the I1 survival civilization.
PAWN_TRAITS = ("industrious", "optimist", "tough")


def bootstrap_farm_fields(state: FactionState) -> None:
    """Give every unbound Farm an established field (physical sourcing bootstrap).

    A settled colony did not just break ground: its farms arrived mid-season.
    Each Farm without a field gets one beside it, staggered through the growth
    cycle (:data:`FIELD_STAGGER_HOURS`) so one field is ripe on day 0 and the
    rest ripen in a rolling rhythm instead of a synchronized burst. Also seeds
    the faction seed-grain reserve if it is empty. Used by the default viewer
    civilization and the seeded survival-oracle civs in tests; a *newly built*
    Farm mid-run never goes through this - it breaks bare ground and must plant.
    """
    if state.seed_grain <= 0:
        state.seed_grain = STARTING_SEED_GRAIN
    farms = sorted(
        (
            building
            for building in state.buildings.values()
            if building.kind == "Farm" and world.farm_field(state, building) is None
        ),
        key=lambda b: b.id,
    )
    for index, farm in enumerate(farms):
        stagger = FIELD_STAGGER_HOURS[index % len(FIELD_STAGGER_HOURS)]
        x, y = farm.x + 1, farm.y + 1
        if state.grid is not None:
            x = max(0, min(state.grid.width - 1, x))
            y = max(0, min(state.grid.height - 1, y))
        field = world.create_field_node(
            state, x, y, field_id=f"field-{farm.id}", ripe=stagger is None
        )
        if stagger is not None:
            field.state = NODE_GROWING
            field.growth_progress = float(world.FIELD_GROWTH_HOURS - stagger)
        farm.source_node_id = field.id


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
    state.stockpile.capacity = DEFAULT_STOCKPILE_CAPACITY
    state.stockpile.base_capacity = DEFAULT_STOCKPILE_CAPACITY
    state.stockpile.add(Good.BREAD, 48)
    state.stockpile.add(Good.WATER, 24)
    state.seed_grain = STARTING_SEED_GRAIN

    counts: dict[str, int] = {}
    for kind, x, y in STARTING_BUILDINGS:
        counts[kind] = counts.get(kind, 0) + 1
        building_id = f"{kind.lower().replace(' ', '')}{counts[kind]}"
        building = buildings.make_building(kind, x, y, building_id=building_id)
        surplus_target = SURPLUS_PRODUCTION_TARGETS.get(kind)
        if surplus_target is not None:
            good, amount = surplus_target
            building.production_target[good] = amount
        state.buildings[building.id] = building
    bootstrap_farm_fields(state)

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
            home_x=px,
            home_y=py,
        )

    return state
