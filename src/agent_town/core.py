from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import hypot
import random

from .spatial import SpatialIndex


WORLD_WIDTH = 2400
WORLD_HEIGHT = 1600
MAX_EVENT_LOG = 80
SOCIAL_INTERACTION_RADIUS = 115.0
SOCIAL_CELL_SIZE = 140.0


# ============================================================================
# Colony contract (Build 1) - frozen Phase 0 deliverable.
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
# It is implemented here as `ColonyException` so it never shadows the builtin
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
class Pawn:
    """A colonist. Owned by Track B; the engine reads it for production."""

    id: str
    name: str
    skills: dict[str, int] = field(default_factory=dict)
    traits: tuple[str, ...] = ()
    wants: tuple[str, ...] = ()
    needs: dict[str, float] = field(default_factory=dict)
    mood: float = 0.5
    schedule: str = "default"
    assignment: JobRef | None = None
    x: int = 0
    y: int = 0
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
    single-map, so this is the natural root container for the whole colony.
    """

    stockpile: Stockpile = field(default_factory=Stockpile)
    coin: int = 0
    pawns: dict[str, Pawn] = field(default_factory=dict)
    buildings: dict[str, Building] = field(default_factory=dict)
    construction_sites: dict[str, ConstructionSite] = field(default_factory=dict)
    research: tuple[str, ...] = ()
    season: str = "spring"
    tax_rate: float = 0.1
    day: int = 0
    time_of_day: int = 0
    grid: GridMap | None = None
    resource_nodes: list[ResourceNode] = field(default_factory=list)


@dataclass(frozen=True)
class ColonyException:
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

    @classmethod
    def assign_pawn(cls, pawn_id: str, building_id: str, role: str) -> "GovernorAction":
        return cls(kind=ACTION_ASSIGN_PAWN, pawn_id=pawn_id, building_id=building_id, role=role)

    @classmethod
    def set_schedule(cls, pawn_id_or_group: str, template: str) -> "GovernorAction":
        return cls(kind=ACTION_SET_SCHEDULE, group=pawn_id_or_group, template=template)

    @classmethod
    def place_building(cls, kind: str, x: int, y: int) -> "GovernorAction":
        return cls(kind=ACTION_PLACE_BUILDING, building_kind=kind, x=x, y=y)

    @classmethod
    def set_production_target(cls, building_id: str, good: Good, amount: int) -> "GovernorAction":
        return cls(kind=ACTION_SET_PRODUCTION_TARGET, building_id=building_id, good=good, amount=amount)

    @classmethod
    def set_research(cls, tech: str) -> "GovernorAction":
        return cls(kind=ACTION_SET_RESEARCH, tech=tech)


# ============================================================================
# Legacy social-sim (AI-Town wander sim). Retired when the viewer is rewritten
# to render colony state (integration milestone I3). Kept importable so the
# existing Pygame viewer and its tests keep passing during the refactor.
# ============================================================================


def _clean_text(value: str, limit: int) -> str:
    return " ".join(str(value).split())[:limit]


@dataclass(frozen=True)
class Location:
    name: str
    x: float
    y: float
    kind: str
    radius: float = 72


@dataclass
class MemoryEntry:
    tick: int
    text: str


@dataclass
class EventEntry:
    tick: int
    text: str


@dataclass(frozen=True)
class DecisionResult:
    destination: str
    intent: str
    speech: str = ""
    memory: str = ""
    relationship_target: str = ""
    relationship_effect: float = 0.0


@dataclass
class Agent:
    id: str
    name: str
    x: float
    y: float
    color: tuple[int, int, int]
    traits: tuple[str, ...]
    energy: float = 0.75
    hunger: float = 0.25
    social: float = 0.45
    curiosity: float = 0.45
    activity: str = "getting oriented"
    goal: str = "settle into town"
    destination: str = "Town Square"
    decision_cooldown: float = 0.0
    conversation_cooldown: float = 0.0
    memories: list[MemoryEntry] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    relationships: dict[str, float] = field(default_factory=dict)
    home: str = "North Apartments"
    workplace: str = "Maker Hall"
    preferred_places: tuple[str, ...] = ()
    # Index into characters.png (16px tiles, step 17). Only column 0 (index = row * 54)
    # holds full single-tile character art; other columns are cape/hood/hat fragments
    # meant to be layered, and row 4 (index 216) is empty. Pick from column 0 only.
    sprite_index: int = 0
    last_speech: str = ""
    emote: str = ""
    emote_timer: float = 0.0
    last_llm_turn: float = -9999.0

    def remember(self, tick: int, text: str, limit: int = 8) -> None:
        cleaned = _clean_text(text, 180)
        if not cleaned:
            return
        self.memories.append(MemoryEntry(tick=tick, text=cleaned))
        if len(self.memories) > limit:
            self.memories = self.memories[-limit:]

    def add_suggestion(self, text: str) -> None:
        cleaned = text.strip()
        if cleaned:
            self.suggestions.append(cleaned[:160])
            self.decision_cooldown = 0.0


class Simulation:
    def __init__(
        self,
        locations: list[Location],
        agents: list[Agent],
        *,
        seed: int = 7,
    ) -> None:
        self.locations = {location.name: location for location in locations}
        self.agents = {agent.id: agent for agent in agents}
        self._validate_initial_state()
        self.tick = 0
        self.elapsed = 0.0
        self.rng = random.Random(seed)
        self.events: list[EventEntry] = []
        self.last_step_metrics: dict[str, int] = self._empty_step_metrics()
        self.record_event("Town day started.")

    def step(self, dt: float) -> None:
        if dt <= 0:
            return

        self.elapsed += dt
        self.tick += 1
        metrics = self._empty_step_metrics()
        self._advance_agents(dt)
        self._resolve_social_interactions(metrics)
        self.last_step_metrics = metrics

    def _empty_step_metrics(self) -> dict[str, int]:
        return {
            "agents": len(self.agents),
            "social_candidate_visits": 0,
            "social_distance_checks": 0,
            "conversations_started": 0,
        }

    def _advance_agents(self, dt: float) -> None:
        for agent in self.agents.values():
            self._update_needs(agent, dt)
            self._update_emote(agent, dt)
            agent.decision_cooldown = max(0.0, agent.decision_cooldown - dt)
            agent.conversation_cooldown = max(0.0, agent.conversation_cooldown - dt)

            destination = self.locations[agent.destination]
            if self._distance(agent.x, agent.y, destination.x, destination.y) <= destination.radius:
                self._apply_location_effect(agent, destination, dt)
                if agent.decision_cooldown == 0:
                    self._choose_next_action(agent)
            else:
                self._move_toward(agent, destination, dt)

    def suggest(self, agent_id: str, text: str) -> None:
        if agent_id not in self.agents:
            raise KeyError(f"Unknown agent: {agent_id}")
        self.agents[agent_id].add_suggestion(text)
        if text.strip():
            self.record_event(f"Suggestion queued for {self.agents[agent_id].name}.")

    def apply_decision(self, agent_id: str, decision: DecisionResult) -> None:
        if agent_id not in self.agents:
            raise KeyError(f"Unknown agent: {agent_id}")

        destination_name = _clean_text(decision.destination, 80)
        if destination_name not in self.locations:
            raise ValueError(f"Unknown destination: {destination_name}")

        intent = _clean_text(decision.intent, 120)
        if not intent:
            raise ValueError("Decision intent is required")

        relationship_target = _clean_text(decision.relationship_target, 40)
        if relationship_target:
            if relationship_target not in self.agents:
                raise ValueError(f"Unknown relationship target: {relationship_target}")
            if relationship_target == agent_id:
                raise ValueError("Relationship target cannot be the acting agent")

        agent = self.agents[agent_id]
        speech = _clean_text(decision.speech, 140)
        memory = _clean_text(decision.memory, 160)
        effect = self._clamp(float(decision.relationship_effect), -0.1, 0.1)

        agent.destination = destination_name
        agent.goal = intent
        agent.activity = f"heading to {destination_name}"
        agent.decision_cooldown = max(agent.decision_cooldown, 8.0)
        agent.last_llm_turn = self.elapsed

        if speech:
            agent.last_speech = speech
            agent.emote = self._emote_for_text(speech)
            agent.emote_timer = 10.0
            self.record_event(f"{agent.name}: {speech}")

        agent.remember(self.tick, memory or f"Made a new plan: {intent}.")

        if relationship_target:
            agent.relationships[relationship_target] = self._clamp(
                agent.relationships.get(relationship_target, 0.3) + effect
            )
            self.record_event(f"{agent.name} reconsidered {self.agents[relationship_target].name}.")

    def record_event(self, text: str) -> None:
        cleaned = _clean_text(text, 180)
        if not cleaned:
            return
        self.events.append(EventEntry(tick=self.tick, text=cleaned))
        if len(self.events) > MAX_EVENT_LOG:
            self.events = self.events[-MAX_EVENT_LOG:]

    def agent_location_name(self, agent: Agent) -> str:
        closest = min(
            self.locations.values(),
            key=lambda location: self._distance(agent.x, agent.y, location.x, location.y),
        )
        if self._distance(agent.x, agent.y, closest.x, closest.y) <= closest.radius:
            return closest.name
        return "between places"

    def relationship_label(self, agent: Agent, other_id: str) -> str:
        value = agent.relationships.get(other_id, 0.3)
        if value >= 0.76:
            return "close"
        if value >= 0.56:
            return "friendly"
        if value >= 0.34:
            return "familiar"
        if value >= 0.18:
            return "distant"
        return "strained"

    def _validate_initial_state(self) -> None:
        if len(self.locations) == 0:
            raise ValueError("Simulation requires at least one location")
        for agent in self.agents.values():
            if agent.destination not in self.locations:
                raise ValueError(f"Unknown destination for {agent.id}: {agent.destination}")
            if agent.home not in self.locations:
                agent.home = agent.destination
            if agent.workplace not in self.locations:
                agent.workplace = agent.destination

    def _update_needs(self, agent: Agent, dt: float) -> None:
        energy_drain = 0.007 if "restless" in agent.traits else 0.006
        curiosity_gain = 0.006 if "curious" in agent.traits or "inventive" in agent.traits else 0.004
        social_gain = 0.003 if "private" in agent.traits else 0.005
        if "social" in agent.traits or "warm" in agent.traits:
            social_gain += 0.002

        agent.energy = self._clamp(agent.energy - energy_drain * dt)
        agent.hunger = self._clamp(agent.hunger + 0.008 * dt)
        agent.social = self._clamp(agent.social + social_gain * dt)
        agent.curiosity = self._clamp(agent.curiosity + curiosity_gain * dt)

    def _update_emote(self, agent: Agent, dt: float) -> None:
        if agent.emote_timer <= 0:
            return
        agent.emote_timer = max(0.0, agent.emote_timer - dt)
        if agent.emote_timer == 0:
            agent.emote = ""

    def _apply_location_effect(self, agent: Agent, location: Location, dt: float) -> None:
        if location.kind == "home":
            agent.energy = self._clamp(agent.energy + 0.035 * dt)
            agent.activity = "resting at home"
            agent.emote = agent.emote or "sleep"
            agent.emote_timer = max(agent.emote_timer, 1.0)
        elif location.kind == "food":
            agent.hunger = self._clamp(agent.hunger - 0.045 * dt)
            agent.activity = "eating and listening"
            agent.emote = agent.emote or "happy"
            agent.emote_timer = max(agent.emote_timer, 1.0)
        elif location.kind == "social":
            agent.social = self._clamp(agent.social - 0.018 * dt)
            agent.activity = "looking for conversation"
        elif location.kind == "knowledge":
            agent.curiosity = self._clamp(agent.curiosity - 0.026 * dt)
            agent.activity = "studying notes"
            agent.emote = agent.emote or "idea"
            agent.emote_timer = max(agent.emote_timer, 1.0)
        elif location.kind == "work":
            agent.energy = self._clamp(agent.energy - 0.008 * dt)
            agent.social = self._clamp(agent.social - 0.004 * dt)
            agent.activity = "working on a project"
        else:
            agent.activity = "wandering and observing"

    def _choose_next_action(self, agent: Agent) -> None:
        suggestion_destination = self._destination_from_suggestion(agent)
        if suggestion_destination is not None:
            agent.destination = suggestion_destination.name
            agent.goal = f"try suggestion: {agent.suggestions.pop(0)}"
            agent.activity = f"heading to {agent.destination}"
            agent.remember(self.tick, f"Decided to follow a suggestion toward {agent.destination}.")
            self.record_event(f"{agent.name} followed a suggestion toward {agent.destination}.")
            agent.decision_cooldown = 10.0
            return

        if agent.energy < 0.28:
            destination = self._nearest_kind_or_none(agent, "home") or self.rng.choice(list(self.locations.values()))
            agent.goal = "recover energy"
        elif agent.hunger > 0.72:
            destination = self._nearest_kind_or_none(agent, "food") or self.rng.choice(list(self.locations.values()))
            agent.goal = "find a meal"
        elif agent.social > 0.70:
            destination = self._nearest_kind_or_none(agent, "social") or self.rng.choice(list(self.locations.values()))
            agent.goal = "find someone to talk with"
        elif agent.curiosity > 0.68:
            destination = self._nearest_kind_or_none(agent, "knowledge") or self.rng.choice(list(self.locations.values()))
            agent.goal = "learn something useful"
        else:
            destination = self._routine_destination(agent)
            agent.goal = self.rng.choice(
                [
                    "keep a loose routine",
                    "notice what changed",
                    "look for a useful conversation",
                    "think about tomorrow",
                ]
            )

        agent.destination = destination.name
        agent.activity = f"heading to {destination.name}"
        agent.decision_cooldown = self.rng.uniform(8.0, 18.0)

    def _routine_destination(self, agent: Agent) -> Location:
        day_fraction = (self.elapsed % 300.0) / 300.0
        if day_fraction < 0.16:
            food = self._nearest_kind_or_none(agent, "food")
            if food is not None:
                return food
        if day_fraction < 0.54 and agent.workplace in self.locations:
            return self.locations[agent.workplace]
        if day_fraction < 0.74 and agent.preferred_places and self.rng.random() < 0.65:
            choices = [self.locations[name] for name in agent.preferred_places if name in self.locations]
            if choices:
                return self.rng.choice(choices)
        if day_fraction < 0.88:
            social = self._nearest_kind_or_none(agent, "social")
            if social is not None:
                return social
        if agent.home in self.locations:
            return self.locations[agent.home]
        return self.rng.choice(list(self.locations.values()))

    def _destination_from_suggestion(self, agent: Agent) -> Location | None:
        if not agent.suggestions:
            return None

        suggestion = agent.suggestions[0].lower()
        for location in self.locations.values():
            if location.name.lower() in suggestion:
                return location

        keyword_to_kind = {
            "eat": "food",
            "food": "food",
            "rest": "home",
            "sleep": "home",
            "talk": "social",
            "meet": "social",
            "study": "knowledge",
            "learn": "knowledge",
            "work": "work",
        }
        for keyword, kind in keyword_to_kind.items():
            if keyword in suggestion:
                return self._nearest_kind(agent, kind)
        return None

    def _resolve_social_interactions(self, metrics: dict[str, int] | None = None) -> None:
        agents = list(self.agents.values())
        order_by_id = {agent.id: index for index, agent in enumerate(agents)}
        location_by_id = {agent.id: self.agent_location_name(agent) for agent in agents}
        spatial_index = SpatialIndex(agents, cell_size=SOCIAL_CELL_SIZE)

        for first in agents:
            if first.conversation_cooldown > 0:
                continue

            first_location = location_by_id[first.id]
            if first_location == "between places":
                continue

            candidates = spatial_index.nearby(first.x, first.y, SOCIAL_INTERACTION_RADIUS)
            if metrics is not None:
                metrics["social_candidate_visits"] += len(candidates)

            for second in sorted(candidates, key=lambda agent: order_by_id[agent.id]):
                if order_by_id[second.id] <= order_by_id[first.id]:
                    continue
                if second.conversation_cooldown > 0:
                    continue
                if first_location != location_by_id[second.id]:
                    continue
                if metrics is not None:
                    metrics["social_distance_checks"] += 1
                if self._distance(first.x, first.y, second.x, second.y) > SOCIAL_INTERACTION_RADIUS:
                    continue
                self._start_conversation(first, second)
                if metrics is not None:
                    metrics["conversations_started"] += 1
                break

    def _start_conversation(self, first: Agent, second: Agent) -> None:
        location_name = self.agent_location_name(first)
        topic = self.rng.choice(
            [
                "town rumors",
                "a small project",
                "where everyone has been spending time",
                "what to do later",
            ]
        )
        first.activity = f"talking with {second.name}"
        second.activity = f"talking with {first.name}"
        first.last_speech = f"{topic.capitalize()}?"
        second.last_speech = "Let's compare notes."
        first.emote = "dots"
        second.emote = "happy"
        first.emote_timer = 6.0
        second.emote_timer = 6.0
        first.social = self._clamp(first.social - 0.20)
        second.social = self._clamp(second.social - 0.20)
        first.relationships[second.id] = self._clamp(first.relationships.get(second.id, 0.3) + 0.04)
        second.relationships[first.id] = self._clamp(second.relationships.get(first.id, 0.3) + 0.04)
        first.remember(self.tick, f"Talked with {second.name} at {location_name} about {topic}.")
        second.remember(self.tick, f"Talked with {first.name} at {location_name} about {topic}.")
        self.record_event(f"{first.name} and {second.name} talked at {location_name}.")
        first.conversation_cooldown = 20.0
        second.conversation_cooldown = 20.0

    def _nearest_kind(self, agent: Agent, kind: str) -> Location:
        nearest = self._nearest_kind_or_none(agent, kind)
        if nearest is None:
            raise ValueError(f"No location with kind {kind!r}")
        return nearest

    def _nearest_kind_or_none(self, agent: Agent, kind: str) -> Location | None:
        candidates = [location for location in self.locations.values() if location.kind == kind]
        if not candidates:
            return None
        return min(candidates, key=lambda location: self._distance(agent.x, agent.y, location.x, location.y))

    def _move_toward(self, agent: Agent, location: Location, dt: float) -> None:
        dx = location.x - agent.x
        dy = location.y - agent.y
        distance = hypot(dx, dy)
        if distance == 0:
            return
        speed = 74.0 if agent.energy > 0.35 else 48.0
        travel = min(distance, speed * dt)
        agent.x += dx / distance * travel
        agent.y += dy / distance * travel
        agent.activity = f"walking to {location.name}"

    @staticmethod
    def _emote_for_text(text: str) -> str:
        lowered = text.lower()
        if any(word in lowered for word in ("idea", "learn", "think", "study", "plan")):
            return "idea"
        if any(word in lowered for word in ("friend", "like", "thanks", "glad")):
            return "heart"
        if any(word in lowered for word in ("why", "where", "what", "?")):
            return "question"
        if any(word in lowered for word in ("tired", "rest", "sleep")):
            return "sleep"
        return "dots"

    @staticmethod
    def _distance(ax: float, ay: float, bx: float, by: float) -> float:
        return hypot(ax - bx, ay - by)

    @staticmethod
    def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
        return max(lower, min(upper, value))


def create_default_simulation() -> Simulation:
    locations = [
        Location("Town Square", 1180, 780, "social", 120),
        Location("North Apartments", 530, 360, "home", 95),
        Location("South Row Homes", 1780, 1280, "home", 95),
        Location("Greenhouse Cafe", 760, 1110, "food", 88),
        Location("Archive Library", 1600, 455, "knowledge", 92),
        Location("Maker Hall", 1880, 800, "work", 96),
        Location("Riverside Park", 420, 1160, "social", 115),
        Location("Clinic Garden", 1260, 1240, "quiet", 82),
    ]
    agents = [
        Agent(
            "mira",
            "Mira",
            1120,
            760,
            (91, 141, 239),
            ("curious", "direct", "pattern-seeker"),
            destination="Town Square",
            home="North Apartments",
            workplace="Archive Library",
            preferred_places=("Archive Library", "Town Square"),
            sprite_index=0,
        ),
        Agent(
            "sol",
            "Sol",
            1240,
            820,
            (245, 158, 66),
            ("warm", "restless", "connector"),
            destination="Town Square",
            home="South Row Homes",
            workplace="Greenhouse Cafe",
            preferred_places=("Greenhouse Cafe", "Riverside Park"),
            sprite_index=54,
        ),
        Agent(
            "juno",
            "Juno",
            560,
            410,
            (98, 197, 126),
            ("careful", "observant", "routine-bound"),
            destination="North Apartments",
            home="North Apartments",
            workplace="Clinic Garden",
            preferred_places=("Clinic Garden", "Archive Library"),
            sprite_index=108,
        ),
        Agent(
            "tess",
            "Tess",
            1790,
            1210,
            (219, 103, 137),
            ("inventive", "private", "stubborn"),
            destination="South Row Homes",
            home="South Row Homes",
            workplace="Maker Hall",
            preferred_places=("Maker Hall", "Clinic Garden"),
            sprite_index=162,
        ),
        Agent(
            "orin",
            "Orin",
            1550,
            500,
            (178, 132, 232),
            ("bookish", "kind", "historian"),
            destination="Archive Library",
            home="North Apartments",
            workplace="Archive Library",
            preferred_places=("Archive Library", "Town Square"),
            sprite_index=270,
        ),
        Agent(
            "vale",
            "Vale",
            1840,
            840,
            (86, 190, 200),
            ("practical", "social", "fixer"),
            destination="Maker Hall",
            home="South Row Homes",
            workplace="Maker Hall",
            preferred_places=("Maker Hall", "Greenhouse Cafe"),
            sprite_index=324,
        ),
        Agent(
            "rhea",
            "Rhea",
            740,
            1070,
            (230, 205, 92),
            ("generous", "curious", "gossip-aware"),
            destination="Greenhouse Cafe",
            home="South Row Homes",
            workplace="Greenhouse Cafe",
            preferred_places=("Greenhouse Cafe", "Town Square"),
            sprite_index=378,
        ),
        Agent(
            "pax",
            "Pax",
            430,
            1120,
            (132, 196, 98),
            ("quiet", "patient", "naturalist"),
            destination="Riverside Park",
            home="North Apartments",
            workplace="Riverside Park",
            preferred_places=("Riverside Park", "Clinic Garden"),
            sprite_index=432,
        ),
        Agent(
            "ivo",
            "Ivo",
            1280,
            1210,
            (220, 130, 88),
            ("restless", "ambitious", "competitive"),
            destination="Clinic Garden",
            home="South Row Homes",
            workplace="Maker Hall",
            preferred_places=("Maker Hall", "Town Square"),
            sprite_index=486,
        ),
        Agent(
            "nia",
            "Nia",
            1210,
            760,
            (238, 132, 190),
            ("warm", "private", "mediator"),
            destination="Town Square",
            home="North Apartments",
            workplace="Clinic Garden",
            preferred_places=("Town Square", "Riverside Park"),
            sprite_index=540,
        ),
    ]
    return Simulation(locations, agents)
