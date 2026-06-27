from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from typing import Any

from .core import Agent, EventEntry, Location, MemoryEntry, Simulation


SCHEMA_VERSION = 1


class SQLiteSimulationStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def save_snapshot(self, sim: Simulation, *, label: str = "latest") -> None:
        label = _clean_label(label)
        payload = simulation_to_snapshot(sim)
        encoded = json.dumps(payload, separators=(",", ":"))
        events = payload["events"]

        connection = self._connect()
        try:
            with connection:
                self._initialize(connection)
                connection.execute(
                    """
                    INSERT OR REPLACE INTO snapshots(label, tick, elapsed, data)
                    VALUES (?, ?, ?, ?)
                    """,
                    (label, sim.tick, sim.elapsed, encoded),
                )
                connection.execute("DELETE FROM event_log WHERE label = ?", (label,))
                connection.executemany(
                    """
                    INSERT INTO event_log(label, position, tick, text)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        (label, position, int(event["tick"]), str(event["text"]))
                        for position, event in enumerate(events)
                    ),
                )
        finally:
            connection.close()

    def load_snapshot(self, *, label: str = "latest") -> Simulation:
        label = _clean_label(label)
        connection = self._connect()
        try:
            self._initialize(connection)
            row = connection.execute(
                "SELECT data FROM snapshots WHERE label = ?",
                (label,),
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            raise KeyError(f"No simulation snapshot saved for label: {label}")
        return simulation_from_snapshot(json.loads(row[0]))

    def load_event_log(self, *, label: str = "latest") -> list[EventEntry]:
        label = _clean_label(label)
        connection = self._connect()
        try:
            self._initialize(connection)
            rows = connection.execute(
                """
                SELECT tick, text FROM event_log
                WHERE label = ?
                ORDER BY position
                """,
                (label,),
            ).fetchall()
        finally:
            connection.close()
        return [EventEntry(tick=int(row[0]), text=str(row[1])) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(str(self.path))

    def _initialize(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS metadata(
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS snapshots(
                label TEXT PRIMARY KEY,
                tick INTEGER NOT NULL,
                elapsed REAL NOT NULL,
                data TEXT NOT NULL,
                saved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS event_log(
                label TEXT NOT NULL,
                position INTEGER NOT NULL,
                tick INTEGER NOT NULL,
                text TEXT NOT NULL,
                PRIMARY KEY(label, position)
            )
            """
        )
        connection.execute(
            "INSERT OR REPLACE INTO metadata(key, value) VALUES ('schema_version', ?)",
            (str(SCHEMA_VERSION),),
        )


def simulation_to_snapshot(sim: Simulation) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "tick": sim.tick,
        "elapsed": sim.elapsed,
        "rng_state": _jsonable_random_state(sim.rng.getstate()),
        "locations": [
            {
                "name": location.name,
                "x": location.x,
                "y": location.y,
                "kind": location.kind,
                "radius": location.radius,
            }
            for location in sim.locations.values()
        ],
        "agents": [_agent_to_snapshot(agent) for agent in sim.agents.values()],
        "events": [{"tick": event.tick, "text": event.text} for event in sim.events],
    }


def simulation_from_snapshot(snapshot: dict[str, Any]) -> Simulation:
    if not isinstance(snapshot, dict):
        raise ValueError("Simulation snapshot must be a JSON object")
    if int(snapshot.get("schema_version", 0)) != SCHEMA_VERSION:
        raise ValueError("Unsupported simulation snapshot schema version")

    locations = [_location_from_snapshot(item) for item in _require_list(snapshot, "locations")]
    agents = [_agent_from_snapshot(item) for item in _require_list(snapshot, "agents")]
    sim = Simulation(locations, agents)
    sim.tick = int(snapshot["tick"])
    sim.elapsed = float(snapshot["elapsed"])
    sim.events = [_event_from_snapshot(item) for item in _require_list(snapshot, "events")]
    if "rng_state" in snapshot:
        sim.rng.setstate(_random_state_from_json(snapshot["rng_state"]))
    sim.last_step_metrics = sim._empty_step_metrics()
    return sim


def _agent_to_snapshot(agent: Agent) -> dict[str, Any]:
    return {
        "id": agent.id,
        "name": agent.name,
        "x": agent.x,
        "y": agent.y,
        "color": list(agent.color),
        "traits": list(agent.traits),
        "energy": agent.energy,
        "hunger": agent.hunger,
        "social": agent.social,
        "curiosity": agent.curiosity,
        "activity": agent.activity,
        "goal": agent.goal,
        "destination": agent.destination,
        "decision_cooldown": agent.decision_cooldown,
        "conversation_cooldown": agent.conversation_cooldown,
        "memories": [{"tick": memory.tick, "text": memory.text} for memory in agent.memories],
        "suggestions": list(agent.suggestions),
        "relationships": dict(agent.relationships),
        "home": agent.home,
        "workplace": agent.workplace,
        "preferred_places": list(agent.preferred_places),
        "sprite_index": agent.sprite_index,
        "last_speech": agent.last_speech,
        "emote": agent.emote,
        "emote_timer": agent.emote_timer,
        "last_llm_turn": agent.last_llm_turn,
    }


def _agent_from_snapshot(snapshot: Any) -> Agent:
    data = _require_dict(snapshot, "agent")
    return Agent(
        id=str(data["id"]),
        name=str(data["name"]),
        x=float(data["x"]),
        y=float(data["y"]),
        color=tuple(int(value) for value in data["color"]),
        traits=tuple(str(value) for value in data["traits"]),
        energy=float(data["energy"]),
        hunger=float(data["hunger"]),
        social=float(data["social"]),
        curiosity=float(data["curiosity"]),
        activity=str(data["activity"]),
        goal=str(data["goal"]),
        destination=str(data["destination"]),
        decision_cooldown=float(data["decision_cooldown"]),
        conversation_cooldown=float(data["conversation_cooldown"]),
        memories=[_memory_from_snapshot(item) for item in _require_list(data, "memories")],
        suggestions=[str(value) for value in data["suggestions"]],
        relationships={str(key): float(value) for key, value in data["relationships"].items()},
        home=str(data["home"]),
        workplace=str(data["workplace"]),
        preferred_places=tuple(str(value) for value in data["preferred_places"]),
        sprite_index=int(data["sprite_index"]),
        last_speech=str(data["last_speech"]),
        emote=str(data["emote"]),
        emote_timer=float(data["emote_timer"]),
        last_llm_turn=float(data["last_llm_turn"]),
    )


def _location_from_snapshot(snapshot: Any) -> Location:
    data = _require_dict(snapshot, "location")
    return Location(
        name=str(data["name"]),
        x=float(data["x"]),
        y=float(data["y"]),
        kind=str(data["kind"]),
        radius=float(data["radius"]),
    )


def _memory_from_snapshot(snapshot: Any) -> MemoryEntry:
    data = _require_dict(snapshot, "memory")
    return MemoryEntry(tick=int(data["tick"]), text=str(data["text"]))


def _event_from_snapshot(snapshot: Any) -> EventEntry:
    data = _require_dict(snapshot, "event")
    return EventEntry(tick=int(data["tick"]), text=str(data["text"]))


def _jsonable_random_state(state: object) -> object:
    return json.loads(json.dumps(state))


def _random_state_from_json(value: Any) -> object:
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError("Invalid random state in simulation snapshot")
    version, internal_state, gauss = value
    if not isinstance(internal_state, list):
        raise ValueError("Invalid random internal state in simulation snapshot")
    return int(version), tuple(int(item) for item in internal_state), gauss


def _require_dict(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"Snapshot field must be an object: {field}")
    return value


def _require_list(value: dict[str, Any], field: str) -> list[Any]:
    result = value.get(field)
    if not isinstance(result, list):
        raise ValueError(f"Snapshot field must be a list: {field}")
    return result


def _clean_label(label: str) -> str:
    cleaned = " ".join(str(label).split())[:80]
    if not cleaned:
        raise ValueError("Snapshot label is required")
    return cleaned
