from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol


@dataclass(frozen=True)
class MemoryState:
    tick: int
    text: str


@dataclass(frozen=True)
class EventState:
    tick: int
    text: str


@dataclass(frozen=True)
class LocationState:
    name: str
    x: float
    y: float
    kind: str
    radius: float


@dataclass(frozen=True)
class AgentState:
    id: str
    name: str
    x: float
    y: float
    color: tuple[int, int, int]
    traits: tuple[str, ...]
    energy: float
    hunger: float
    social: float
    curiosity: float
    activity: str
    goal: str
    destination: str
    decision_cooldown: float
    conversation_cooldown: float
    memories: tuple[MemoryState, ...]
    suggestions: tuple[str, ...]
    relationships: tuple[tuple[str, float], ...]
    home: str
    workplace: str
    preferred_places: tuple[str, ...]
    sprite_index: int
    last_speech: str
    emote: str
    emote_timer: float
    last_llm_turn: float


@dataclass(frozen=True)
class ReplayEvent:
    tick: int
    elapsed: float
    kind: str
    payload: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WorldState:
    tick: int
    elapsed: float
    locations: tuple[LocationState, ...]
    agents: tuple[AgentState, ...]
    events: tuple[EventState, ...]
    replay_events: tuple[ReplayEvent, ...] = ()


@dataclass(frozen=True)
class RenderSnapshot:
    world: WorldState
    selected_agent_id: str = ""
    visible_agent_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class PlannerRequest:
    agent_id: str
    world: WorldState
    context: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PlannerResult:
    agent_id: str
    destination: str
    intent: str
    speech: str = ""
    memory: str = ""
    relationship_target: str = ""
    relationship_effect: float = 0.0


@dataclass(frozen=True)
class ModelProfile:
    name: str
    tier: str
    max_context_tokens: int
    expected_ram_gb: float
    expected_vram_gb: float
    concurrency: int
    notes: str = ""


class SimulationSystem(Protocol):
    name: str

    def step(self, world: WorldState, dt: float) -> tuple[ReplayEvent, ...]:
        ...
