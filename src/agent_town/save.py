"""Save/load: the civilization persists between sessions.

The product is a pocket universe that lives on the desktop - the pawns'
reality must not reset every time the window closes. This module serializes
the whole ``FactionState`` to versioned JSON and restores it exactly, so a
saved-then-loaded civilization steps identically to one that never stopped
(the deterministic engine makes that testable, and ``tests/test_save.py``
pins it).

Design rules:

- **The state is the save.** Everything the engine reads round-trips: pawns
  (thoughts, priorities, forced assignments), buildings (staffing, banked
  cycle progress, targets, owned field), stockpile with its conservation
  journal, construction sites, resource nodes mid-growth, research, seed
  grain, clock, and the map itself. ``work_decisions`` is deliberately
  dropped - the arbiter rewrites it every hour.
- **Static data is rebuilt, not stored.** A building's recipe/job_slots come
  from its kind via ``buildings.make_building``, so recipe rebalances apply
  to old saves instead of fossilizing.
- **Dict order is preserved** (JSON objects keep insertion order in Python):
  engine iteration order over pawns/buildings is part of determinism.
- Saves are plain local files under ``saves/`` (gitignored). No cloud, no
  telemetry - the same local-only trust boundary as everything else.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import buildings as buildings_mod
from .core import (
    Building,
    ConstructionSite,
    FactionState,
    Good,
    GridMap,
    JobRef,
    Pawn,
    ResourceNode,
    Stockpile,
    Thought,
)

SAVE_FORMAT = 1
DEFAULT_SAVE_DIR = Path("saves")
AUTOSAVE_NAME = "autosave.json"


# --- Serialize ----------------------------------------------------------------


def _goods_dict(counts: dict[Good, int]) -> dict[str, int]:
    return {good.value: count for good, count in counts.items()}


def _job_ref(ref: JobRef | None) -> dict | None:
    if ref is None:
        return None
    return {"building_id": ref.building_id, "role": ref.role}


def to_dict(state: FactionState) -> dict:
    """The whole civilization as a JSON-safe dict (versioned)."""
    return {
        "format": SAVE_FORMAT,
        "coin": state.coin,
        "research": list(state.research),
        "research_target": state.research_target,
        "research_points": state.research_points,
        "season": state.season,
        "tax_rate": state.tax_rate,
        "day": state.day,
        "time_of_day": state.time_of_day,
        "seed": state.seed,
        "seed_grain": state.seed_grain,
        "stockpile": {
            "counts": _goods_dict(state.stockpile.counts),
            "capacity": state.stockpile.capacity,
            "base_capacity": state.stockpile.base_capacity,
            "flow_in": _goods_dict(state.stockpile.flow_in),
            "flow_out": _goods_dict(state.stockpile.flow_out),
        },
        "grid": None
        if state.grid is None
        else {
            "width": state.grid.width,
            "height": state.grid.height,
            "tiles": [list(row) for row in state.grid.tiles],
        },
        "resource_nodes": [
            {
                "kind": node.kind.value,
                "amount": node.amount,
                "x": node.x,
                "y": node.y,
                "id": node.id,
                "state": node.state,
                "growth_progress": node.growth_progress,
                "max_amount": node.max_amount,
            }
            for node in state.resource_nodes
        ],
        "buildings": [
            {
                "id": building.id,
                "kind": building.kind,
                "x": building.x,
                "y": building.y,
                "built": building.built,
                "staffed_by": list(building.staffed_by),
                "production_target": _goods_dict(building.production_target),
                "production_progress": building.production_progress,
                "source_node_id": building.source_node_id,
            }
            for building in state.buildings.values()
        ],
        "construction_sites": [
            {
                "id": site.id,
                "building_kind": site.building_kind,
                "x": site.x,
                "y": site.y,
                "required": _goods_dict(site.required),
                "delivered": _goods_dict(site.delivered),
                "work_remaining": site.work_remaining,
            }
            for site in state.construction_sites.values()
        ],
        "pawns": [
            {
                "id": pawn.id,
                "name": pawn.name,
                "skills": dict(pawn.skills),
                "traits": list(pawn.traits),
                "wants": list(pawn.wants),
                "needs": dict(pawn.needs),
                "mood": pawn.mood,
                "mood_target": pawn.mood_target,
                "thoughts": [
                    {
                        "kind": t.kind,
                        "label": t.label,
                        "value": t.value,
                        "age": t.age,
                        "stack": t.stack,
                        "duration": t.duration,
                    }
                    for t in pawn.thoughts
                ],
                "schedule": pawn.schedule,
                "assignment": _job_ref(pawn.assignment),
                "work_priorities": dict(pawn.work_priorities),
                "forced_assignment": _job_ref(pawn.forced_assignment),
                "x": pawn.x,
                "y": pawn.y,
                "home_x": pawn.home_x,
                "home_y": pawn.home_y,
                "coin": pawn.coin,
                "state": pawn.state,
            }
            for pawn in state.pawns.values()
        ],
    }


# --- Deserialize ---------------------------------------------------------------


def _goods_from(data: dict[str, int]) -> dict[Good, int]:
    return {Good(name): count for name, count in data.items()}


def _job_ref_from(data: dict | None) -> JobRef | None:
    if not data:
        return None
    return JobRef(building_id=data["building_id"], role=data["role"])


def from_dict(data: dict) -> FactionState:
    """Rebuild a FactionState from :func:`to_dict` output."""
    version = data.get("format")
    if version != SAVE_FORMAT:
        raise ValueError(f"Unsupported save format {version!r} (expected {SAVE_FORMAT})")

    stock_data = data["stockpile"]
    stockpile = Stockpile(
        counts=_goods_from(stock_data["counts"]),
        capacity=stock_data["capacity"],
        base_capacity=stock_data["base_capacity"],
        flow_in=_goods_from(stock_data["flow_in"]),
        flow_out=_goods_from(stock_data["flow_out"]),
    )

    grid = None
    if data.get("grid"):
        grid_data = data["grid"]
        grid = GridMap(
            width=grid_data["width"],
            height=grid_data["height"],
            tiles=tuple(tuple(row) for row in grid_data["tiles"]),
        )

    state = FactionState(
        stockpile=stockpile,
        coin=data["coin"],
        research=tuple(data["research"]),
        research_target=data["research_target"],
        research_points=data["research_points"],
        season=data["season"],
        tax_rate=data["tax_rate"],
        day=data["day"],
        time_of_day=data["time_of_day"],
        seed=data["seed"],
        seed_grain=data.get("seed_grain", 0),
        grid=grid,
    )

    for node_data in data["resource_nodes"]:
        state.resource_nodes.append(
            ResourceNode(
                kind=Good(node_data["kind"]),
                amount=node_data["amount"],
                x=node_data["x"],
                y=node_data["y"],
                id=node_data["id"],
                state=node_data["state"],
                growth_progress=node_data["growth_progress"],
                max_amount=node_data["max_amount"],
            )
        )

    for b_data in data["buildings"]:
        # Rebuild from the catalogue so recipe/job_slots stay current, then
        # restore the dynamic fields the engine actually mutates.
        building = buildings_mod.make_building(
            b_data["kind"], b_data["x"], b_data["y"], building_id=b_data["id"], built=b_data["built"]
        )
        building.staffed_by = list(b_data["staffed_by"])
        building.production_target = _goods_from(b_data["production_target"])
        building.production_progress = b_data["production_progress"]
        building.source_node_id = b_data.get("source_node_id")
        state.buildings[building.id] = building

    for s_data in data["construction_sites"]:
        state.construction_sites[s_data["id"]] = ConstructionSite(
            id=s_data["id"],
            building_kind=s_data["building_kind"],
            x=s_data["x"],
            y=s_data["y"],
            required=_goods_from(s_data["required"]),
            delivered=_goods_from(s_data["delivered"]),
            work_remaining=s_data["work_remaining"],
        )

    for p_data in data["pawns"]:
        state.pawns[p_data["id"]] = Pawn(
            id=p_data["id"],
            name=p_data["name"],
            skills=dict(p_data["skills"]),
            traits=tuple(p_data["traits"]),
            wants=tuple(p_data["wants"]),
            needs=dict(p_data["needs"]),
            mood=p_data["mood"],
            mood_target=p_data["mood_target"],
            thoughts=[
                Thought(
                    kind=t["kind"],
                    label=t["label"],
                    value=t["value"],
                    age=t["age"],
                    stack=t["stack"],
                    duration=t["duration"],
                )
                for t in p_data["thoughts"]
            ],
            schedule=p_data["schedule"],
            assignment=_job_ref_from(p_data["assignment"]),
            work_priorities={wt: int(level) for wt, level in p_data["work_priorities"].items()},
            forced_assignment=_job_ref_from(p_data["forced_assignment"]),
            x=p_data["x"],
            y=p_data["y"],
            home_x=p_data["home_x"],
            home_y=p_data["home_y"],
            coin=p_data["coin"],
            state=p_data["state"],
        )

    return state


# --- Files ---------------------------------------------------------------------


def save_state(state: FactionState, path: Path | str) -> Path:
    """Write the civilization to ``path`` atomically (write temp, then replace)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(to_dict(state)), encoding="utf-8")
    tmp.replace(path)
    return path


def load_state(path: Path | str) -> FactionState:
    """Read a civilization back from ``path``."""
    return from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def autosave_path(save_dir: Path | str = DEFAULT_SAVE_DIR) -> Path:
    return Path(save_dir) / AUTOSAVE_NAME


def load_autosave(save_dir: Path | str = DEFAULT_SAVE_DIR) -> FactionState | None:
    """The saved civilization if a readable autosave exists, else None.

    A corrupt or incompatible save returns None rather than crashing the boot -
    the viewer falls back to a fresh world and the old file is left in place
    for inspection.
    """
    path = autosave_path(save_dir)
    if not path.exists():
        return None
    try:
        return load_state(path)
    except Exception:
        return None
