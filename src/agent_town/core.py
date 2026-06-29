from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
# ============================================================================
# Civilization contract (Build 1) - frozen Phase 0 deliverable.
#
# These dataclasses and the `effective_work` seam (in mood.py) are the shared
# interface both build tracks depend on. See BLUEPRINT.md "Frozen contract".
# After Phase 0 this block is frozen: any change is a one-file PR that both
# tracks rebase on, never a silent edit.
#
# Track A (world/economy/buildings/construction) and Track B (pawns/mood/
# schedule/governor) meet only at `effective_work(pawn, recipe, time_of_day)`.
#
# Naming note: the refactor plan calls the exception-queue entity "Exception".
# It is implemented here as `CivilizationException` so it never shadows the builtin
# `Exception` - the LLM governor's hard fallback relies on `except Exception`.
# ============================================================================


class Good(Enum):
    """Tradeable / storable goods in the build-1 economy."""

    LOGS = "logs"
    PLANKS = "planks"
    GRAIN = "grain"
    FLOUR = "flour"
    BREAD = "bread"
    STONE = "stone"


# Pawn need keys tracked in build 1 (Pawn.needs). Convention: each value is in
# [0.0, 1.0] where 1.0 == fully satisfied and it decays toward 0.0 over time,
# restored by the matching schedule block plus the right good/building.
NEED_REST = "rest"
NEED_FOOD = "food"
NEED_RECREATION = "recreation"
BUILD1_NEEDS = (NEED_REST, NEED_FOOD, NEED_RECREATION)

# ScheduleTemplate.blocks entries - one per hour, 24 long.
SCHEDULE_WORK = "work"
SCHEDULE_SLEEP = "sleep"
SCHEDULE_REC = "rec"
SCHEDULE_ANY = "any"
SCHEDULE_BLOCK_KINDS = (SCHEDULE_WORK, SCHEDULE_SLEEP, SCHEDULE_REC, SCHEDULE_ANY)

# GovernorAction.kind values (see section 7 of the refactor plan).
ACTION_ASSIGN_PAWN = "assign_pawn"
ACTION_SET_SCHEDULE = "set_schedule"
ACTION_PLACE_BUILDING = "place_building"
ACTION_SET_PRODUCTION_TARGET = "set_production_target"
ACTION_SET_RESEARCH = "set_research"
ACTION_SET_WORK_PRIORITY = "set_work_priority"

# Work-priority levels (build-2 lane-based arbiter, Paper 3). RimWorld 1:1:
# 1 is the highest priority, 4 the lowest, and 0/absent means the work type is
# disabled for that pawn. ``work.py`` owns the lanes and selection logic.
WORK_PRIORITY_DISABLED = 0
WORK_PRIORITY_HIGHEST = 1
WORK_PRIORITY_LOWEST = 4


@dataclass(frozen=True)
class GridMap:
    """Tile grid. ``tiles[y][x]`` is the terrain kind at that cell."""

    width: int
    height: int
    tiles: tuple[tuple[str, ...], ...] = ()

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("GridMap width and height must be positive")
        if len(self.tiles) != self.height:
            raise ValueError("GridMap tiles must have one row per height")
        if any(len(row) != self.width for row in self.tiles):
            raise ValueError("GridMap tile rows must match width")

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def tile_at(self, x: int, y: int) -> str:
        if not self.in_bounds(x, y):
            raise IndexError(f"tile ({x}, {y}) out of bounds")
        return self.tiles[y][x]


@dataclass
class ResourceNode:
    """A harvestable node on the map (tree, field, stone outcrop)."""

    kind: Good
    amount: int
    x: int
    y: int


@dataclass
class Stockpile:
    """Faction-wide good counts. Behaviour implemented by Track A (A1)."""

    counts: dict[Good, int] = field(default_factory=dict)

    def add(self, good: Good, amount: int) -> None:
        _validate_good_amount(good, amount)
        self.counts[good] = self.counts.get(good, 0) + amount

    def remove(self, good: Good, amount: int) -> None:
        _validate_good_amount(good, amount)
        available = self.counts.get(good, 0)
        if available < amount:
            raise ValueError(f"Insufficient {good.value}: need {amount}, have {available}")
        remaining = available - amount
        if remaining:
            self.counts[good] = remaining
        else:
            self.counts.pop(good, None)

    def has(self, good: Good, amount: int) -> bool:
        if not isinstance(good, Good):
            raise TypeError("Stockpile goods must use Good enum values")
        if amount < 0:
            raise ValueError("Stockpile required amounts must be non-negative")
        return self.counts.get(good, 0) >= amount


def _validate_good_amount(good: Good, amount: int) -> None:
    if not isinstance(good, Good):
        raise TypeError("Stockpile goods must use Good enum values")
    if amount <= 0:
        raise ValueError("Stockpile amounts must be positive")


@dataclass
class Recipe:
    """A production rule: consume ``inputs`` and ``work_units`` -> ``outputs``."""

    inputs: dict[Good, int]
    outputs: dict[Good, int]
    work_units: float
    skill: str


@dataclass(frozen=True)
class JobRef:
    """A pawn's current job slot: a building plus the role it fills."""

    building_id: str
    role: str


@dataclass
class Building:
    """A placed building. ``id`` keys it inside FactionState.buildings."""

    id: str
    kind: str
    x: int
    y: int
    recipe: Recipe | None = None
    job_slots: int = 0
    staffed_by: list[str] = field(default_factory=list)
    built: bool = True
    production_target: dict[Good, int] = field(default_factory=dict)


@dataclass
class ConstructionSite:
    """A pending build. ``id`` keys it inside FactionState.construction_sites."""

    id: str
    building_kind: str
    x: int
    y: int
    required: dict[Good, int] = field(default_factory=dict)
    delivered: dict[Good, int] = field(default_factory=dict)
    work_remaining: float = 0.0


@dataclass
class Thought:
    """A named moodlet on a pawn's mood ledger (RimWorld-style).

    ``value`` is a point contribution on the 0-100 mood scale (e.g. Hungry = -6).
    Situational thoughts (hunger, rest/rec, traits, wants) are recomputed each
    tick; ``age``/``stack`` are used by persistent event thoughts (e.g. Catharsis)
    that decay over time. ``duration`` is the lifetime in hours for event thoughts
    (0 == situational, never stored/aged).
    """

    kind: str
    label: str
    value: float
    age: int = 0
    stack: int = 1
    duration: int = 0


@dataclass
class RejectedJob:
    """A job a pawn's arbiter considered but did not take, with the why.

    Spectator telemetry only (Paper 3 "show why the top rejected candidate
    lost"). ``reason`` is a short human string such as ``"reserved"`` or
    ``"lower priority (4)"``.
    """

    building_id: str
    work_type: str
    reason: str


@dataclass
class WorkDecision:
    """The work arbiter's latest decision for one pawn (Paper 3 decision trace).

    ``lane`` is the winning decision lane (see ``work.py`` LANE_* constants).
    ``building_id``/``work_type`` are the pawn's standing work assignment for the
    lane that won (``None`` when idle/hard-state). ``rejected`` lists the top
    candidates the normal-work lane passed over, so the inspector can explain why
    a pawn chose one job over another instead of looking arbitrary.
    """

    lane: str
    building_id: str | None = None
    work_type: str | None = None
    reason: str = ""
    rejected: list[RejectedJob] = field(default_factory=list)


@dataclass
class Pawn:
    """A colonist. Owned by Track B; the engine reads it for production."""

    id: str
    name: str
    skills: dict[str, int] = field(default_factory=dict)
    traits: tuple[str, ...] = ()
    wants: tuple[str, ...] = ()
    needs: dict[str, float] = field(default_factory=dict)
    mood: float = 50.0
    mood_target: float = 50.0
    thoughts: list[Thought] = field(default_factory=list)
    schedule: str = "default"
    assignment: JobRef | None = None
    # Per-work-type manual priorities (work_type -> 1..4; 0/absent = disabled).
    # Empty means "derive from skill" (see work.default_priority). The work
    # arbiter reads these; the governor/player set them via set_work_priority.
    work_priorities: dict[str, int] = field(default_factory=dict)
    # A governor/player override (the forced lane). When set, the arbiter pins
    # the pawn to this job instead of choosing one; it is set by assign_pawn.
    forced_assignment: JobRef | None = None
    x: int = 0
    y: int = 0
    home_x: int = 0
    home_y: int = 0
    state: str = "idle"


@dataclass(frozen=True)
class ScheduleTemplate:
    """A 24-hour schedule; ``blocks[hour]`` is one of SCHEDULE_BLOCK_KINDS."""

    name: str
    blocks: tuple[str, ...]

    def __post_init__(self) -> None:
        if len(self.blocks) != 24:
            raise ValueError("ScheduleTemplate.blocks must have length 24")

    def block_at(self, hour: int) -> str:
        return self.blocks[hour % 24]


@dataclass
class FactionState:
    """Root state the engine steps and the governor summarises.

    The refactor-plan table lists the economic/people fields; ``grid`` and
    ``resource_nodes`` are included here because build 1 is single-faction /
    single-map, so this is the natural root container for the whole civilization.
    """

    stockpile: Stockpile = field(default_factory=Stockpile)
    coin: int = 0
    pawns: dict[str, Pawn] = field(default_factory=dict)
    buildings: dict[str, Building] = field(default_factory=dict)
    construction_sites: dict[str, ConstructionSite] = field(default_factory=dict)
    # The work arbiter's latest per-pawn decision trace (keyed by pawn id),
    # rewritten each engine hour. Pure telemetry the viewer reads; not gameplay.
    work_decisions: dict[str, WorkDecision] = field(default_factory=dict)
    research: tuple[str, ...] = ()
    season: str = "spring"
    tax_rate: float = 0.1
    day: int = 0
    time_of_day: int = 0
    seed: int = 0
    grid: GridMap | None = None
    resource_nodes: list[ResourceNode] = field(default_factory=list)


@dataclass(frozen=True)
class CivilizationException:
    """An item in the governor's exception queue (plan entity "Exception")."""

    kind: str
    pawn_id: str | None = None
    building_id: str | None = None
    detail: str = ""


@dataclass(frozen=True)
class GovernorAction:
    """A single policy command. Use the classmethods to build valid actions."""

    kind: str
    pawn_id: str | None = None
    group: str | None = None
    building_id: str | None = None
    building_kind: str | None = None
    role: str | None = None
    template: str | None = None
    good: Good | None = None
    amount: int | None = None
    x: int | None = None
    y: int | None = None
    tech: str | None = None
    work_type: str | None = None
    level: int | None = None

    @classmethod
    def assign_pawn(cls, pawn_id: str, building_id: str, role: str) -> "GovernorAction":
        return cls(kind=ACTION_ASSIGN_PAWN, pawn_id=pawn_id, building_id=building_id, role=role)

    @classmethod
    def set_schedule(cls, pawn_id_or_group: str, template: str) -> "GovernorAction":
        return cls(kind=ACTION_SET_SCHEDULE, group=pawn_id_or_group, template=template)

    @classmethod
    def set_work_priority(cls, pawn_id_or_group: str, work_type: str, level: int) -> "GovernorAction":
        return cls(kind=ACTION_SET_WORK_PRIORITY, group=pawn_id_or_group, work_type=work_type, level=level)

    @classmethod
    def place_building(cls, kind: str, x: int, y: int) -> "GovernorAction":
        return cls(kind=ACTION_PLACE_BUILDING, building_kind=kind, x=x, y=y)

    @classmethod
    def set_production_target(cls, building_id: str, good: Good, amount: int) -> "GovernorAction":
        return cls(kind=ACTION_SET_PRODUCTION_TARGET, building_id=building_id, good=good, amount=amount)

    @classmethod
    def set_research(cls, tech: str) -> "GovernorAction":
        return cls(kind=ACTION_SET_RESEARCH, tech=tech)
