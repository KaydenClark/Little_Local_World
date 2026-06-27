from __future__ import annotations

from dataclasses import asdict, fields
import json
from pathlib import Path
import sqlite3
from typing import Any

from .contracts import AgentState, EventState, LocationState, MemoryState, ReplayEvent, WorldState
from .core import Simulation, simulation_from_state


SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    tick INTEGER NOT NULL,
    elapsed REAL NOT NULL,
    payload TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS replay_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id INTEGER NOT NULL,
    tick INTEGER NOT NULL,
    elapsed REAL NOT NULL,
    kind TEXT NOT NULL,
    payload TEXT NOT NULL,
    FOREIGN KEY(snapshot_id) REFERENCES snapshots(id)
);
"""


def save_snapshot(path: str | Path, sim: Simulation) -> int:
    db_path = _normalize_path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    state = sim.snapshot()
    with sqlite3.connect(db_path) as connection:
        connection.executescript(SCHEMA)
        cursor = connection.execute(
            "INSERT INTO snapshots (tick, elapsed, payload) VALUES (?, ?, ?)",
            (state.tick, state.elapsed, json.dumps(_world_state_to_json(state), separators=(",", ":"))),
        )
        snapshot_id = int(cursor.lastrowid)
        connection.executemany(
            """
            INSERT INTO replay_events (snapshot_id, tick, elapsed, kind, payload)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    snapshot_id,
                    event.tick,
                    event.elapsed,
                    event.kind,
                    json.dumps(dict(event.payload), separators=(",", ":")),
                )
                for event in state.replay_events
            ],
        )
    return snapshot_id


def load_snapshot(path: str | Path, snapshot_id: int | None = None) -> WorldState:
    db_path = _normalize_path(path)
    with sqlite3.connect(db_path) as connection:
        row = _load_snapshot_row(connection, snapshot_id)
    return _world_state_from_json(json.loads(row["payload"]))


def load_simulation(path: str | Path, snapshot_id: int | None = None) -> Simulation:
    return simulation_from_state(load_snapshot(path, snapshot_id))


def _normalize_path(path: str | Path) -> Path:
    if not str(path).strip():
        raise ValueError("database path is required")
    return Path(path)


def _load_snapshot_row(connection: sqlite3.Connection, snapshot_id: int | None) -> sqlite3.Row:
    connection.row_factory = sqlite3.Row
    if snapshot_id is None:
        cursor = connection.execute("SELECT payload FROM snapshots ORDER BY id DESC LIMIT 1")
    else:
        cursor = connection.execute("SELECT payload FROM snapshots WHERE id = ?", (snapshot_id,))
    row = cursor.fetchone()
    if row is None:
        raise KeyError("snapshot not found")
    return row


def _world_state_to_json(state: WorldState) -> dict[str, Any]:
    return asdict(state)


def _world_state_from_json(data: dict[str, Any]) -> WorldState:
    allowed = {field.name for field in fields(WorldState)}
    extra = set(data) - allowed
    if extra:
        raise ValueError(f"Unknown world state fields: {sorted(extra)}")
    return WorldState(
        tick=int(data["tick"]),
        elapsed=float(data["elapsed"]),
        locations=tuple(LocationState(**location) for location in data.get("locations", [])),
        agents=tuple(_agent_state_from_json(agent) for agent in data.get("agents", [])),
        events=tuple(EventState(**event) for event in data.get("events", [])),
        replay_events=tuple(ReplayEvent(**event) for event in data.get("replay_events", [])),
    )


def _agent_state_from_json(data: dict[str, Any]) -> AgentState:
    return AgentState(
        id=str(data["id"]),
        name=str(data["name"]),
        x=float(data["x"]),
        y=float(data["y"]),
        color=tuple(int(channel) for channel in data["color"]),
        traits=tuple(str(trait) for trait in data.get("traits", [])),
        energy=float(data["energy"]),
        hunger=float(data["hunger"]),
        social=float(data["social"]),
        curiosity=float(data["curiosity"]),
        activity=str(data["activity"]),
        goal=str(data["goal"]),
        destination=str(data["destination"]),
        decision_cooldown=float(data["decision_cooldown"]),
        conversation_cooldown=float(data["conversation_cooldown"]),
        memories=tuple(MemoryState(**memory) for memory in data.get("memories", [])),
        suggestions=tuple(str(suggestion) for suggestion in data.get("suggestions", [])),
        relationships=tuple((str(agent_id), float(value)) for agent_id, value in data.get("relationships", [])),
        home=str(data["home"]),
        workplace=str(data["workplace"]),
        preferred_places=tuple(str(place) for place in data.get("preferred_places", [])),
        sprite_index=int(data["sprite_index"]),
        last_speech=str(data["last_speech"]),
        emote=str(data["emote"]),
        emote_timer=float(data["emote_timer"]),
        last_llm_turn=float(data["last_llm_turn"]),
    )
