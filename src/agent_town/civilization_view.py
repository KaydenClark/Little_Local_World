"""Civilization viewer (integration milestone I3).

Renders the build-1 civilization ``FactionState`` - terrain tiles, resource nodes,
buildings, pawns, and a HUD - and steps the engine so the civilization visibly runs.
The live viewer governs via a non-blocking :class:`CivilizationDecisionScheduler` (a
local LLM on autopilot, with the deterministic fallback covering every gap);
press ``L`` to toggle the LLM on and off. Uses the authored civilization sprite set
(``assets/civilization``), falling back to simple shapes only where no sprite exists
(e.g. grain/stone nodes, pawns).

This is the default ``python -m agent_town`` view after the legacy social-sim
viewer was retired.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field

import pygame

from . import buildings, economy, engine, health, mood, telemetry, work
from .assets import CivilizationAssetManifest, load_civilization_manifest
from .core import (
    ACTION_ASSIGN_PAWN,
    ACTION_PLACE_BUILDING,
    ACTION_SET_PRODUCTION_TARGET,
    ACTION_SET_RESEARCH,
    ACTION_SET_SCHEDULE,
    ACTION_SET_WORK_PRIORITY,
    CivilizationException,
    ConstructionSite,
    FactionState,
    Good,
    GovernorAction,
    NEED_FOOD,
    NEED_RECREATION,
    NEED_REST,
    NEED_WATER,
)
from .civilization import create_default_civilization
from .governor import (
    GOV_DISABLED,
    GOV_IDLE,
    GOV_INVALID,
    GOV_OFFLINE,
    GOV_THINKING,
    CivilizationDecisionScheduler,
    FallbackGovernor,
    Governor,
    build_exception_queue,
)
from .pawns import STATE_WANDERING, STATE_SLACKING

MARGIN = 12
HUD_HEIGHT = 118
INSPECTOR_WIDTH = 288
PAWN_ROSTER_HEIGHT = 66
STEP_INTERVAL = 0.6  # real seconds per simulated hour at normal speed
SMOKE_FRAMES = 8
BUILDING_TILE_WIDTH = 2  # buildings are scaled to this many tiles wide
PAWN_RENDER_HEIGHT = 26  # pawn sprites are scaled to this height (aspect kept)
MIN_ZOOM = 0.7
MAX_ZOOM = 2.2
ZOOM_STEP = 1.18
CAMERA_PAN_PX = 70

BACKGROUND = (38, 44, 38)
HUD_BG = (18, 20, 18)
HUD_TEXT = (226, 230, 220)
PANEL_BG = (18, 23, 25)
PANEL_BG_2 = (25, 31, 34)
PANEL_BG_3 = (35, 40, 43)
PANEL_BORDER = (85, 96, 100)
PANEL_HILITE = (142, 112, 65)
INSPECTOR_BG = PANEL_BG
INSPECTOR_BORDER = PANEL_BORDER
INSPECTOR_TEXT = (222, 228, 216)
INSPECTOR_MUTED = (158, 166, 154)
SELECTION = (245, 220, 92)
SELECTION_OUTER = (245, 248, 238)
HOVER = (255, 212, 92)
DANGER = (235, 80, 70)
IDLE_BADGE_BG = (24, 24, 24)
IDLE_BADGE_ICON = (255, 196, 0)
NEED_GOOD = (69, 205, 214)
NEED_WARN = (232, 150, 79)
NEED_BAD = (214, 84, 73)
WATER_TINT = (54, 104, 168, 150)
LABEL_BG = (0, 0, 0, 140)
LABEL_TEXT = (240, 240, 230)

# GridMap terrain kind -> base tile sprite name.
TERRAIN_TILE = {
    "grass": "grass",
    "tree": "grass",
    "field": "dirt",
    "stone": "pavement",
    "water": "grass",
}

# Building kind -> sprite name. Raw extractors use the smaller house3, processors
# the wide house; house2 is reserved for the build-2 residence. Stand-ins until
# per-kind art lands.
BUILDING_SPRITE = {
    "Forester": "house3",
    "Quarry": "house3",
    "Farm": "house3",
    "Sawmill": "house",
    "Mill": "house",
    "Bakery": "house",
    "Water Well": "house3",
}
DEFAULT_BUILDING_SPRITE = "house"

# Resource-node Good -> prop sprite name (None draws a coloured marker).
NODE_PROP = {Good.LOGS: "tree"}
NODE_MARKER_COLOR = {Good.GRAIN: (214, 188, 84), Good.STONE: (150, 150, 158)}

HUD_GOODS = (
    ("Bread", Good.BREAD),
    ("Water", Good.WATER),
    ("Grain", Good.GRAIN),
    ("Flour", Good.FLOUR),
    ("Logs", Good.LOGS),
    ("Planks", Good.PLANKS),
    ("Stone", Good.STONE),
)

# Civ-wide need readouts shown in the top-left Civ stats panel. Mood is drawn
# first (own colour).
CIV_STATS_NEEDS = (
    ("Food", NEED_FOOD),
    ("Water", NEED_WATER),
    ("Recreation", NEED_RECREATION),
    ("Rest", NEED_REST),
)
CIV_STATS_WIDTH = 224

# Work-priority grid (RimWorld Work tab). Columns are the build-1 work types,
# ordered by their natural priority (the arbiter's tiebreaker), with short labels.
WORK_GRID_TYPES = sorted(work.WORK_TYPE_ORDER, key=lambda wt: -work.work_type_order(wt))
WORK_TYPE_LABEL = {
    "water": "Water",
    "farming": "Farm",
    "milling": "Mill",
    "baking": "Bake",
    "forestry": "Frst",
    "woodworking": "Wood",
    "mining": "Mine",
    "research": "Rsrch",
}
# Priority -> cell colour (1 highest/brightest .. 4 lowest; 0/disabled is blank).
WORK_PRIORITY_COLOR = {
    1: (86, 170, 108),
    2: (120, 156, 96),
    3: (150, 140, 80),
    4: (120, 110, 74),
}
# Decision-lane -> readable label + colour for the inspector trace.
LANE_LABEL = {
    work.LANE_FORCED: ("Forced (override)", (214, 180, 110)),
    work.LANE_HARD_STATE: ("Mental break", (224, 130, 110)),
    work.LANE_MEDICAL: ("Medical rest", (224, 130, 110)),
    work.LANE_SELF_CARE: ("Self-care", (220, 200, 120)),
    work.LANE_EMERGENCY: ("Emergency", (224, 130, 110)),
    work.LANE_NORMAL_WORK: ("Normal work", (140, 200, 150)),
    work.LANE_IDLE: ("Idle", (150, 156, 148)),
}

# Bottom-strip command buttons. "Work" opens the work-priority grid; the rest are
# still visual placeholders until their build-2 actions exist.
HUD_BUTTONS = ("Architect", "Work", "Assign", "Research", "History", "Menu")
HUD_BUTTON_W = 104
HUD_BUTTON_H = 28

HUD_MUTED = (150, 156, 148)
GOVERNOR_STATUS_COLOR = {
    GOV_IDLE: (140, 200, 150),
    GOV_THINKING: (220, 200, 120),
    GOV_OFFLINE: (224, 130, 110),
    GOV_INVALID: (224, 130, 110),
    GOV_DISABLED: HUD_MUTED,
}

EXCEPTION_SEVERITY_RANK = {
    health.CRITICAL: 0,
    health.WARN: 1,
    health.INFO: 2,
}
EXCEPTION_SEVERITY = {
    "pawn_break": health.CRITICAL,
    "pawn_breaking": health.CRITICAL,
    "low_water": health.WARN,
    "missing_inputs": health.WARN,
    "unstaffed_building": health.WARN,
    "unhappy_pawn": health.WARN,
    "idle_pawn": health.WARN,
    "skill_mismatch": health.WARN,
}
EXCEPTION_KIND_RANK = {
    "pawn_break": 0,
    "pawn_breaking": 1,
    "low_water": 2,
    "missing_inputs": 3,
    "unstaffed_building": 4,
    "unhappy_pawn": 5,
    "skill_mismatch": 6,
    "idle_pawn": 7,
}
GOVERNOR_CARD_WIDTH = 332
GOVERNOR_CARD_HEIGHT = 146
EXCEPTION_STACK_WIDTH = 318
EXCEPTION_STACK_MAX = 4


@dataclass(frozen=True)
class ExceptionStackItem:
    """One compact, severity-sorted problem for the right-edge observer stack."""

    kind: str
    severity: str
    title: str
    cause: str
    subject: str = ""


@dataclass(frozen=True)
class GovernorCardSummary:
    """Short, derived situation report for the always-visible Governor card."""

    plan: str
    phase: str
    bottleneck: str
    confidence: int
    last_reallocation: str
    exception_count: int
    top_exception: ExceptionStackItem | None = None


def governor_status_line(gov: Governor) -> tuple[str, tuple[int, int, int]]:
    """A one-line HUD summary of how the civilization is being governed right now.

    A plain governor (no ``status``) reads as fallback autopilot; a
    :class:`CivilizationDecisionScheduler` reports its live LLM connection state and
    the ``L`` toggle that switches it on and off.
    """
    status = getattr(gov, "status", None)
    if status is None:
        return ("Governor: fallback (autopilot)   pawns coloured by mood", HUD_MUTED)

    color = GOVERNOR_STATUS_COLOR.get(status.state, HUD_MUTED)
    model = status.model.rsplit("/", 1)[-1] if status.model else "local model"
    if status.state == GOV_DISABLED:
        text = "Governor: fallback (autopilot)   press L to connect a local LLM"
    elif status.state == GOV_THINKING:
        text = f"Governor: LLM {model}   thinking... (fallback covering)   L: disconnect"
    elif status.state == GOV_IDLE:
        kinds = ", ".join(status.last_action_kinds) or "no change"
        latency = f" {status.last_latency:.1f}s" if status.last_latency else ""
        text = f"Governor: LLM {model}   last decision{latency}: {kinds}   L: disconnect"
    else:  # offline / invalid
        text = f"Governor: LLM {model} unreachable - fallback covering   L: retry"
    return (text, color)


def _pawn_name(state: FactionState, pawn_id: str | None) -> str:
    if not pawn_id:
        return ""
    pawn = state.pawns.get(pawn_id)
    return pawn.name if pawn is not None else pawn_id


def _building_name(state: FactionState, building_id: str | None) -> str:
    if not building_id:
        return ""
    building = state.buildings.get(building_id)
    return building.kind if building is not None else building_id


def _exception_severity(exc: CivilizationException) -> str:
    return EXCEPTION_SEVERITY.get(exc.kind, health.INFO)


def _exception_subject(state: FactionState, exc: CivilizationException) -> str:
    if exc.pawn_id:
        return _pawn_name(state, exc.pawn_id)
    if exc.building_id:
        return _building_name(state, exc.building_id)
    return "Civilization"


def _exception_title_and_cause(state: FactionState, exc: CivilizationException) -> tuple[str, str]:
    subject = _exception_subject(state, exc)
    if exc.kind == "pawn_break":
        return (f"Pawn break: {subject}", f"{subject} is in a mental break ({exc.detail}).")
    if exc.kind == "pawn_breaking":
        return (f"Break risk: {subject}", f"{subject} is below the break band ({exc.detail}).")
    if exc.kind == "unhappy_pawn":
        return (f"Low mood: {subject}", f"{subject} needs schedule or supply relief ({exc.detail}).")
    if exc.kind == "idle_pawn":
        return (f"Idle pawn: {subject}", "No legal job won the work arbiter.")
    if exc.kind == "skill_mismatch":
        building = _building_name(state, exc.building_id)
        return (f"Mismatch: {subject}", f"{subject} is weak for {building} ({exc.detail}).")
    if exc.kind == "unstaffed_building":
        return (f"Unstaffed: {subject}", "No pawn has claimed this work slot.")
    if exc.kind == "missing_inputs":
        return (f"Missing inputs: {subject}", f"{subject} is blocked on {exc.detail}.")
    if exc.kind == "low_water":
        return ("Low water", f"Water reserve or need is below the safe line ({exc.detail}).")
    return (exc.kind.replace("_", " ").title(), exc.detail or "Needs attention.")


def exception_stack_items(state: FactionState) -> list[ExceptionStackItem]:
    """Active governor exceptions sorted for the observer stack."""
    items: list[ExceptionStackItem] = []
    for exc in build_exception_queue(state):
        title, cause = _exception_title_and_cause(state, exc)
        items.append(
            ExceptionStackItem(
                kind=exc.kind,
                severity=_exception_severity(exc),
                title=title,
                cause=cause,
                subject=_exception_subject(state, exc),
            )
        )
    return sorted(
        items,
        key=lambda item: (
            EXCEPTION_SEVERITY_RANK.get(item.severity, 99),
            EXCEPTION_KIND_RANK.get(item.kind, 99),
            item.title,
            item.kind,
        ),
    )


def _action_kinds_from(actions: list[GovernorAction] | tuple | None) -> list[str]:
    kinds: list[str] = []
    for action in actions or ():
        if isinstance(action, str):
            kinds.append(action)
        else:
            kind = getattr(action, "kind", "")
            if kind:
                kinds.append(kind)
    return kinds


def _last_reallocation_text(gov: Governor | None, last_actions: list[GovernorAction] | tuple | None) -> str:
    kinds = _action_kinds_from(last_actions)
    if not kinds:
        status = getattr(gov, "status", None)
        kinds = _action_kinds_from(getattr(status, "last_action_kinds", ()) if status is not None else ())
    if not kinds:
        return "No recent policy change"

    labels = {
        ACTION_SET_WORK_PRIORITY: "Adjusted work priorities",
        ACTION_SET_SCHEDULE: "Changed schedules",
        ACTION_ASSIGN_PAWN: "Forced an assignment",
        ACTION_PLACE_BUILDING: "Queued construction",
        ACTION_SET_PRODUCTION_TARGET: "Changed production targets",
        ACTION_SET_RESEARCH: "Changed research",
    }
    primary = labels.get(kinds[-1], kinds[-1].replace("_", " ").title())
    if len(kinds) == 1:
        return primary
    return f"{primary} (+{len(kinds) - 1} more)"


def _governor_phase(gov: Governor | None) -> str:
    status = getattr(gov, "status", None)
    if status is None:
        return "Fallback autopilot"
    if status.state == GOV_THINKING:
        return "Local model thinking"
    if status.state == GOV_IDLE:
        return "Local model idle"
    if status.state in (GOV_OFFLINE, GOV_INVALID):
        return "Fallback covering model issue"
    if status.state == GOV_DISABLED:
        return "Fallback autopilot"
    return str(status.state).replace("_", " ").title()


def _plan_for_exception(item: ExceptionStackItem) -> str:
    if item.kind == "low_water":
        return "Stabilize water reserve"
    if item.kind in ("pawn_break", "pawn_breaking", "unhappy_pawn"):
        return "Recover pawn mood"
    if item.kind == "idle_pawn":
        return "Rebalance idle labour"
    if item.kind == "unstaffed_building":
        return "Staff open work"
    if item.kind == "missing_inputs":
        return "Unblock production"
    if item.kind == "skill_mismatch":
        return "Fix role mismatch"
    return f"Handle {item.title.lower()}"


def _confidence_for(gov: Governor | None, items: list[ExceptionStackItem]) -> int:
    if not items:
        confidence = 88
    elif items[0].severity == health.CRITICAL:
        confidence = 54
    else:
        confidence = 72

    status = getattr(gov, "status", None)
    if status is not None:
        if status.state == GOV_THINKING:
            confidence -= 4
        elif status.state in (GOV_OFFLINE, GOV_INVALID):
            confidence -= 10
    return max(10, min(99, confidence))


def governor_card_summary(
    state: FactionState,
    gov: Governor | None = None,
    *,
    last_actions: list[GovernorAction] | tuple | None = None,
) -> GovernorCardSummary:
    """Derive the Governor card from current state; it never mutates the sim."""
    items = exception_stack_items(state)
    top = items[0] if items else None
    if top is not None:
        plan = _plan_for_exception(top)
        bottleneck = top.cause
    elif state.construction_sites:
        first_site = sorted(state.construction_sites.values(), key=lambda s: s.id)[0]
        plan = f"Finish {first_site.building_kind}"
        bottleneck = "Construction work in progress"
    elif idle_pawn_count(state):
        plan = "Rebalance idle labour"
        bottleneck = f"{idle_pawn_count(state)} pawn(s) idle"
    else:
        plan = "Keep essentials stable"
        bottleneck = "No active exceptions"

    return GovernorCardSummary(
        plan=plan,
        phase=_governor_phase(gov),
        bottleneck=bottleneck,
        confidence=_confidence_for(gov, items),
        last_reallocation=_last_reallocation_text(gov, last_actions),
        exception_count=len(items),
        top_exception=top,
    )


@dataclass
class Camera:
    """Screen transform for the civilization map.

    Offsets are stored in unscaled world pixels so pan and zoom can compose
    without drifting. The viewer owns input; rendering only reads this transform.
    """

    offset_x: float = 0.0
    offset_y: float = 0.0
    zoom: float = 1.0

    def scaled_tile_size(self, base_tile: int) -> int:
        return max(8, round(base_tile * self.zoom))

    def tile_top_left_to_screen(
        self, tile_x: int, tile_y: int, origin: tuple[int, int], base_tile: int
    ) -> tuple[int, int]:
        return self.world_to_screen(tile_x * base_tile, tile_y * base_tile, origin)

    def tile_center_to_screen(
        self, tile_x: int, tile_y: int, origin: tuple[int, int], base_tile: int
    ) -> tuple[int, int]:
        half = base_tile / 2.0
        return self.world_to_screen(tile_x * base_tile + half, tile_y * base_tile + half, origin)

    def world_to_screen(self, world_x: float, world_y: float, origin: tuple[int, int]) -> tuple[int, int]:
        return (
            origin[0] + round((world_x - self.offset_x) * self.zoom),
            origin[1] + round((world_y - self.offset_y) * self.zoom),
        )

    def screen_to_tile(self, pos: tuple[int, int], origin: tuple[int, int], base_tile: int) -> tuple[int, int]:
        world_x = (pos[0] - origin[0]) / self.zoom + self.offset_x
        world_y = (pos[1] - origin[1]) / self.zoom + self.offset_y
        return (int(world_x // base_tile), int(world_y // base_tile))

    def pan(self, screen_dx: float, screen_dy: float) -> None:
        self.offset_x += screen_dx / self.zoom
        self.offset_y += screen_dy / self.zoom

    def zoom_by(self, factor: float, anchor: tuple[int, int], origin: tuple[int, int]) -> None:
        old_zoom = self.zoom
        world_x = (anchor[0] - origin[0]) / old_zoom + self.offset_x
        world_y = (anchor[1] - origin[1]) / old_zoom + self.offset_y
        self.zoom = max(MIN_ZOOM, min(MAX_ZOOM, self.zoom * factor))
        self.offset_x = world_x - (anchor[0] - origin[0]) / self.zoom
        self.offset_y = world_y - (anchor[1] - origin[1]) / self.zoom

    def clamp_to_world(self, world_size: tuple[int, int], viewport_size: tuple[int, int]) -> None:
        visible_w = max(1.0, viewport_size[0] / self.zoom)
        visible_h = max(1.0, viewport_size[1] / self.zoom)
        max_x = max(0.0, world_size[0] - visible_w)
        max_y = max(0.0, world_size[1] - visible_h)
        self.offset_x = max(0.0, min(self.offset_x, max_x))
        self.offset_y = max(0.0, min(self.offset_y, max_y))


@dataclass
class CivilizationAssets:
    """Loaded civilization sprites: raw surfaces plus pre-scaled building sprites."""

    tile_size: int
    surfaces: dict[str, pygame.Surface] = field(default_factory=dict)
    buildings_scaled: dict[str, pygame.Surface] = field(default_factory=dict)
    pawns_scaled: dict[str, pygame.Surface] = field(default_factory=dict)


def load_civilization_assets(manifest: CivilizationAssetManifest | None = None) -> CivilizationAssets:
    """Load every civilization sprite and pre-scale building + pawn sprites."""
    manifest = manifest or load_civilization_manifest()
    assets = CivilizationAssets(tile_size=manifest.tile_size)
    for name in manifest.sprite_files:
        surface = pygame.image.load(str(manifest.path(name))).convert_alpha()
        assets.surfaces[name] = surface

    target_w = BUILDING_TILE_WIDTH * manifest.tile_size
    for name in ("house", "house2", "house3"):
        sprite = assets.surfaces[name]
        scale = target_w / sprite.get_width()
        size = (target_w, max(1, round(sprite.get_height() * scale)))
        assets.buildings_scaled[name] = pygame.transform.smoothscale(sprite, size)

    for path in sorted(manifest.directory.glob("pawn_*.png")):
        sprite = pygame.image.load(str(path)).convert_alpha()
        scale = PAWN_RENDER_HEIGHT / sprite.get_height()
        size = (max(1, round(sprite.get_width() * scale)), PAWN_RENDER_HEIGHT)
        assets.pawns_scaled[path.stem] = pygame.transform.scale(sprite, size)
    return assets


def _mood_color(mood: float) -> tuple[int, int, int]:
    """Red (low) -> yellow -> green (high) for a 0..1 mood."""
    mood = max(0.0, min(1.0, mood))
    if mood < 0.5:
        t = mood / 0.5
        return (210, int(60 + 150 * t), 60)
    t = (mood - 0.5) / 0.5
    return (int(210 - 140 * t), 210, int(60 + 30 * t))


def _need_bar_color(value: float) -> tuple[int, int, int]:
    """Readable need bar color: red danger, amber pressure, cyan stable."""
    value = max(0.0, min(1.0, value))
    if value < 0.25:
        return NEED_BAD
    if value < 0.55:
        return NEED_WARN
    return NEED_GOOD


def _top_skills(pawn, limit: int = 10) -> list[tuple[str, int]]:
    """Highest skills first, with stable alphabetical ordering for ties."""
    return sorted(pawn.skills.items(), key=lambda item: (-item[1], item[0]))[:limit]


def _pawn_status_label(pawn) -> str:
    """Short health-style badge for the pawn sheet."""
    if pawn.state == STATE_WANDERING:
        return "Breaking"
    if pawn.state == STATE_SLACKING:
        return "Stressed"
    if pawn.mood < 35:
        return "Unhappy"
    if min(pawn.needs.values(), default=1.0) < 0.25:
        return "Needs care"
    return "Healthy"


def render_civilization(
    surface: pygame.Surface,
    state: FactionState,
    assets: CivilizationAssets,
    font: pygame.font.Font,
    origin: tuple[int, int],
    *,
    status_line: tuple[str, tuple[int, int, int]] | None = None,
    camera: Camera | None = None,
    selected_pawn_id: str | None = None,
    hovered_pawn_id: str | None = None,
    show_inspector: bool = False,
    show_work_grid: bool = False,
    show_history: bool = False,
    events: list | None = None,
    alert: tuple[str, int] | None = None,
    governor_summary: GovernorCardSummary | None = None,
) -> None:
    """Draw the whole civilization (tiles, nodes, buildings, pawns, HUD) onto ``surface``."""
    camera = camera or Camera()
    surface.fill(BACKGROUND)
    grid = state.grid
    base_ts = assets.tile_size
    ts = camera.scaled_tile_size(base_ts)
    ox, oy = origin
    map_rect = pygame.Rect(
        0,
        PAWN_ROSTER_HEIGHT,
        surface.get_width(),
        surface.get_height() - HUD_HEIGHT - PAWN_ROSTER_HEIGHT,
    )
    inspector_rect = None
    if show_inspector:
        inspector_rect = pygame.Rect(
            surface.get_width() - INSPECTOR_WIDTH,
            0,
            INSPECTOR_WIDTH,
            surface.get_height() - HUD_HEIGHT,
        )
        map_rect.width = max(120, surface.get_width() - INSPECTOR_WIDTH)

    previous_clip = surface.get_clip()
    surface.set_clip(map_rect)
    scaled_tiles: dict[str, pygame.Surface] = {}

    if grid is not None:
        for y in range(grid.height):
            for x in range(grid.width):
                kind = grid.tile_at(x, y)
                tile_name = TERRAIN_TILE.get(kind, "grass")
                tile = scaled_tiles.get(tile_name)
                if tile is None:
                    tile = pygame.transform.scale(assets.surfaces[tile_name], (ts, ts))
                    scaled_tiles[tile_name] = tile
                sx, sy = camera.tile_top_left_to_screen(x, y, (ox, oy), base_ts)
                surface.blit(tile, (sx, sy))
                if kind == "water":
                    tint = pygame.Surface((ts, ts), pygame.SRCALPHA)
                    tint.fill(WATER_TINT)
                    surface.blit(tint, (sx, sy))

    for node in state.resource_nodes:
        _draw_node(surface, node, assets, camera, ox, oy, base_ts)

    for site in sorted(state.construction_sites.values(), key=lambda s: (s.y, s.x, s.id)):
        _draw_construction_site(surface, site, assets, font, camera, ox, oy, base_ts)

    for building in sorted(state.buildings.values(), key=lambda b: (b.y, b.x, b.id)):
        _draw_building(surface, building, assets, font, camera, ox, oy, base_ts)

    pawn_keys = sorted(assets.pawns_scaled)
    for pawn in state.pawns.values():
        _draw_pawn(
            surface,
            pawn,
            assets,
            pawn_keys,
            camera,
            ox,
            oy,
            base_ts,
            selected=pawn.id == selected_pawn_id,
            hovered=pawn.id == hovered_pawn_id,
            idle_badge="idle" in _pawn_readability_markers(
                state,
                pawn,
                selected=pawn.id == selected_pawn_id,
                hovered=pawn.id == hovered_pawn_id,
            ),
        )

    surface.set_clip(previous_clip)
    _draw_civ_stats(surface, font, state, (map_rect.x + MARGIN, map_rect.y + MARGIN))
    _draw_exception_stack(surface, font, exception_stack_items(state), map_rect)
    _draw_governor_card(
        surface,
        font,
        governor_summary or governor_card_summary(state),
        map_rect,
    )
    _draw_pawn_roster(surface, state, assets, font, selected_pawn_id, map_rect.width)
    if inspector_rect is not None:
        _draw_inspector(surface, state, font, selected_pawn_id, inspector_rect)
    if show_work_grid:
        _draw_work_grid(surface, state, font, selected_pawn_id, map_rect)
    if show_history:
        _draw_history_panel(surface, font, events or [], map_rect)
    _draw_hud(
        surface,
        state,
        font,
        status_line,
        work_grid_open=show_work_grid,
        history_open=show_history,
        alert=alert,
    )


def _scale_for_camera(sprite: pygame.Surface, camera: Camera) -> pygame.Surface:
    if abs(camera.zoom - 1.0) < 0.01:
        return sprite
    return pygame.transform.scale(
        sprite,
        (
            max(1, round(sprite.get_width() * camera.zoom)),
            max(1, round(sprite.get_height() * camera.zoom)),
        ),
    )


def _draw_node(surface, node, assets: CivilizationAssets, camera: Camera, ox: int, oy: int, base_ts: int) -> None:
    ts = camera.scaled_tile_size(base_ts)
    cx, cy = camera.tile_center_to_screen(node.x, node.y, (ox, oy), base_ts)
    _left, bottom = camera.tile_top_left_to_screen(node.x, node.y + 1, (ox, oy), base_ts)
    prop = NODE_PROP.get(node.kind)
    if prop is not None:
        sprite = _scale_for_camera(assets.surfaces[prop], camera)
        surface.blit(sprite, (cx - sprite.get_width() // 2, bottom - sprite.get_height()))
        return
    color = NODE_MARKER_COLOR.get(node.kind, (180, 180, 180))
    pygame.draw.circle(surface, color, (cx, cy), max(4, ts // 3))


def _construction_progress(site: ConstructionSite) -> float:
    """0..1 visible construction progress: materials first, then build work."""
    required_total = sum(max(0, amount) for amount in site.required.values())
    if required_total:
        delivered_total = sum(
            min(max(0, site.delivered.get(good, 0)), amount)
            for good, amount in site.required.items()
        )
        material_fraction = delivered_total / required_total
    else:
        material_fraction = 1.0
    material_fraction = max(0.0, min(1.0, material_fraction))
    if material_fraction < 1.0:
        return material_fraction * 0.5

    total_work = max(0.0, buildings.building_def(site.building_kind).build_work)
    if total_work <= 0:
        work_fraction = 1.0
    else:
        work_fraction = 1.0 - min(max(site.work_remaining, 0.0), total_work) / total_work
    return 0.5 + max(0.0, min(1.0, work_fraction)) * 0.5


def _draw_construction_site(
    surface,
    site: ConstructionSite,
    assets: CivilizationAssets,
    font,
    camera: Camera,
    ox: int,
    oy: int,
    base_ts: int,
) -> None:
    sprite = _scale_for_camera(
        assets.buildings_scaled[BUILDING_SPRITE.get(site.building_kind, DEFAULT_BUILDING_SPRITE)],
        camera,
    ).copy()
    sprite.set_alpha(92)
    cx, _cy = camera.tile_center_to_screen(site.x, site.y, (ox, oy), base_ts)
    tile_left, bottom = camera.tile_top_left_to_screen(site.x, site.y + 1, (ox, oy), base_ts)
    ts = camera.scaled_tile_size(base_ts)
    footprint = pygame.Rect(tile_left, bottom - ts, ts * BUILDING_TILE_WIDTH, ts)
    pygame.draw.rect(surface, (10, 12, 12), footprint, 1)
    pygame.draw.rect(surface, (115, 216, 255), footprint.inflate(-2, -2), 1)
    surface.blit(sprite, (cx - sprite.get_width() // 2, bottom - sprite.get_height()))

    progress = _construction_progress(site)
    bar_w = max(24, round(ts * BUILDING_TILE_WIDTH * 0.86))
    bar_h = max(4, round(4 * camera.zoom))
    bar = pygame.Rect(cx - bar_w // 2, bottom - sprite.get_height() - 8, bar_w, bar_h)
    pygame.draw.rect(surface, (8, 10, 10), bar)
    pygame.draw.rect(surface, (115, 216, 255), (bar.x, bar.y, round(bar.width * progress), bar.height))
    pygame.draw.rect(surface, (236, 244, 242), bar, 1)
    if camera.zoom >= 0.85:
        _draw_label(surface, font, f"{site.building_kind} {round(progress * 100)}%", cx, bar.y - 2)


def _draw_building(surface, building, assets: CivilizationAssets, font, camera: Camera, ox: int, oy: int, base_ts: int) -> None:
    sprite = _scale_for_camera(
        assets.buildings_scaled[BUILDING_SPRITE.get(building.kind, DEFAULT_BUILDING_SPRITE)],
        camera,
    )
    cx, _cy = camera.tile_center_to_screen(building.x, building.y, (ox, oy), base_ts)
    _left, bottom = camera.tile_top_left_to_screen(building.x, building.y + 1, (ox, oy), base_ts)
    surface.blit(sprite, (cx - sprite.get_width() // 2, bottom - sprite.get_height()))

    if camera.zoom >= 0.85:
        staffed = len(building.staffed_by)
        label = f"{building.kind} {staffed}/{building.job_slots}"
        _draw_label(surface, font, label, cx, bottom - sprite.get_height() - 2)


def _pawn_sprite_key(pawn, keys: list[str]) -> str:
    """Stable per-pawn sprite pick so a pawn keeps the same look across frames."""
    digits = "".join(ch for ch in pawn.id if ch.isdigit())
    index = int(digits) if digits else sum(map(ord, pawn.id))
    return keys[index % len(keys)]


def _pawn_readability_markers(
    state: FactionState,
    pawn,
    *,
    selected: bool = False,
    hovered: bool = False,
) -> tuple[str, ...]:
    """World-space readability markers in draw-priority order."""
    markers: list[str] = []
    decision = state.work_decisions.get(pawn.id)
    if decision is not None and decision.lane == work.LANE_IDLE:
        markers.append("idle")
    if hovered and not selected:
        markers.append("hover")
    if selected:
        markers.append("selection")
    if pawn.state in (STATE_WANDERING, STATE_SLACKING):
        markers.append("danger")
    return tuple(markers)


def _draw_pawn(
    surface,
    pawn,
    assets: CivilizationAssets,
    pawn_keys: list[str],
    camera: Camera,
    ox: int,
    oy: int,
    base_ts: int,
    *,
    selected: bool = False,
    hovered: bool = False,
    idle_badge: bool = False,
) -> None:
    ts = camera.scaled_tile_size(base_ts)
    sprite = _scale_for_camera(assets.pawns_scaled[_pawn_sprite_key(pawn, pawn_keys)], camera)
    cx, cy = camera.tile_center_to_screen(pawn.x, pawn.y, (ox, oy), base_ts)
    top = cy + 5 - sprite.get_height()
    if hovered and not selected:
        pygame.draw.circle(surface, HOVER, (cx, cy + 1), max(9, ts // 2), 1)
    if selected:
        pygame.draw.circle(surface, SELECTION_OUTER, (cx, cy + 1), max(12, ts // 2 + 2), 2)
        pygame.draw.circle(surface, SELECTION, (cx, cy + 1), max(9, ts // 2 - 1), 1)
    if pawn.state in (STATE_WANDERING, STATE_SLACKING):
        pygame.draw.circle(surface, DANGER, (cx, cy + 2), max(12, ts // 2 + 1), 2)
    surface.blit(sprite, (cx - sprite.get_width() // 2, top))
    if idle_badge:
        _draw_idle_badge(surface, cx, top, camera)
    # Mood dot above the head keeps mood readable at a glance.
    dot_y = top - 3
    pygame.draw.circle(surface, (20, 24, 20), (cx, dot_y), 4)
    pygame.draw.circle(surface, _mood_color(pawn.mood / 100), (cx, dot_y), 3)


def _draw_idle_badge(surface: pygame.Surface, center_x: int, pawn_top: int, camera: Camera) -> None:
    radius = max(7, round(8 * camera.zoom))
    cx = center_x + radius + 2
    cy = pawn_top - radius + 2
    pygame.draw.circle(surface, IDLE_BADGE_BG, (cx, cy), radius)
    pygame.draw.circle(surface, IDLE_BADGE_ICON, (cx, cy), radius - 2, 2)
    top = cy - max(4, round(5 * camera.zoom))
    bottom = cy + max(1, round(2 * camera.zoom))
    pygame.draw.line(surface, IDLE_BADGE_ICON, (cx, top), (cx, bottom), max(1, round(2 * camera.zoom)))
    pygame.draw.circle(surface, IDLE_BADGE_ICON, (cx, cy + radius - 4), max(1, round(2 * camera.zoom)))


def find_pawn_at_screen(
    state: FactionState,
    pos: tuple[int, int],
    origin: tuple[int, int],
    base_tile: int,
    camera: Camera,
) -> str | None:
    """Return the nearest pawn under ``pos`` in screen space."""
    hit_radius = max(10, round(14 * camera.zoom))
    best_id: str | None = None
    best_distance = hit_radius * hit_radius
    for pawn_id, pawn in sorted(state.pawns.items()):
        cx, cy = camera.tile_center_to_screen(pawn.x, pawn.y, origin, base_tile)
        distance = (pos[0] - cx) ** 2 + (pos[1] - cy) ** 2
        if distance <= best_distance:
            best_id = pawn_id
            best_distance = distance
    return best_id


def _draw_label(surface, font, text: str, center_x: int, bottom_y: int) -> None:
    glyph = font.render(text, True, LABEL_TEXT)
    pad = 3
    box = pygame.Surface((glyph.get_width() + pad * 2, glyph.get_height() + pad), pygame.SRCALPHA)
    box.fill(LABEL_BG)
    box.blit(glyph, (pad, 0))
    surface.blit(box, (center_x - box.get_width() // 2, bottom_y - box.get_height()))


def _draw_text(
    surface: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    color: tuple[int, int, int],
    pos: tuple[int, int],
    max_width: int | None = None,
) -> None:
    """Render one line, trimming only when the panel is too narrow."""
    display = text
    if max_width is not None and font.size(display)[0] > max_width:
        while display and font.size(display + "...")[0] > max_width:
            display = display[:-1]
        display = display + "..." if display else "..."
    surface.blit(font.render(display, True, color), pos)


def _draw_value_bar(
    surface: pygame.Surface,
    font: pygame.font.Font,
    label: str,
    value: float,
    rect: pygame.Rect,
    *,
    color: tuple[int, int, int] | None = None,
) -> None:
    value = max(0.0, min(1.0, value))
    color = color or _need_bar_color(value)
    label_w = 86
    _draw_text(surface, font, label, INSPECTOR_TEXT, (rect.x, rect.y + 1), label_w - 8)
    bar = pygame.Rect(rect.x + label_w, rect.y + 4, rect.width - label_w - 40, 12)
    pygame.draw.rect(surface, (5, 7, 8), bar)
    fill = pygame.Rect(bar.x, bar.y, round(bar.width * value), bar.height)
    pygame.draw.rect(surface, color, fill)
    for tick in range(1, 5):
        tx = bar.x + round(bar.width * tick / 5)
        pygame.draw.line(surface, (23, 28, 30), (tx, bar.y), (tx, bar.bottom), 1)
    pygame.draw.rect(surface, PANEL_BORDER, bar, 1)
    _draw_text(surface, font, f"{round(value * 100)}%", INSPECTOR_MUTED, (bar.right + 7, rect.y + 1), 34)


def _draw_civ_stats(
    surface: pygame.Surface,
    font: pygame.font.Font,
    state: FactionState,
    topleft: tuple[int, int],
) -> pygame.Rect:
    """Draw the top-left Civ stats panel: Civ-wide Mood and need readouts."""
    bar_h = 22
    rows = 1 + len(CIV_STATS_NEEDS)  # mood + need readouts
    width = CIV_STATS_WIDTH
    height = 30 + rows * bar_h + 6
    x0, y0 = topleft

    panel = pygame.Surface((width, height), pygame.SRCALPHA)
    panel.fill((14, 18, 20, 210))
    surface.blit(panel, (x0, y0))
    pygame.draw.rect(surface, PANEL_BORDER, (x0, y0, width, height), 1)

    x = x0 + 10
    y = y0 + 8
    _draw_text(surface, font, "Civilization", SELECTION, (x, y), width - 20)
    y += 22
    bar_rect = lambda: pygame.Rect(x, y, width - 20, 18)

    avg_mood = economy.average_mood(state) / 100
    _draw_value_bar(surface, font, "Mood", avg_mood, bar_rect(), color=_mood_color(avg_mood))
    y += bar_h
    for label, need in CIV_STATS_NEEDS:
        _draw_value_bar(surface, font, label, economy.average_need(state, need), bar_rect())
        y += bar_h
    return pygame.Rect(x0, y0, width, height)


def _draw_thoughts(
    surface: pygame.Surface,
    font: pygame.font.Font,
    pawn,
    x: int,
    y: int,
    width: int,
) -> int:
    """Render the pawn's RimWorld-style mood thought ledger; return the new y."""
    thoughts = sorted(mood.current_thoughts(pawn), key=lambda t: (t.value * t.stack, t.label))
    y += 8
    _draw_text(surface, font, "Thoughts", SELECTION, (x, y), width)
    y += 22
    if not thoughts:
        _draw_text(surface, font, "Content", INSPECTOR_MUTED, (x, y), width)
        return y + 20
    for thought in thoughts:
        total = thought.value * thought.stack
        label = thought.label if thought.stack == 1 else f"{thought.label} x{thought.stack}"
        color = (110, 175, 120) if total >= 0 else (205, 110, 92)
        _draw_text(surface, font, label, INSPECTOR_TEXT, (x, y), width - 52)
        _draw_text(surface, font, f"{total:+.0f}", color, (x + width - 46, y), 46)
        y += 19
    return y


def _draw_work_trace(
    surface: pygame.Surface,
    font: pygame.font.Font,
    state: FactionState,
    pawn,
    x: int,
    y: int,
    width: int,
) -> int:
    """Explain the arbiter's choice for this pawn: lane, why, and top rejection."""
    decision = work.explain(state, pawn.id)
    _draw_text(surface, font, "Why this job", SELECTION, (x, y), width)
    y += 20
    if decision is None:
        _draw_text(surface, font, "Lane  (deciding...)", INSPECTOR_MUTED, (x, y), width)
        return y + 20
    label, color = LANE_LABEL.get(decision.lane, (decision.lane, INSPECTOR_TEXT))
    _draw_text(surface, font, f"Lane  {label}", color, (x, y), width)
    y += 19
    if decision.reason:
        _draw_text(surface, font, decision.reason, INSPECTOR_MUTED, (x, y), width)
        y += 19
    if decision.rejected:
        top = decision.rejected[0]
        building = state.buildings.get(top.building_id)
        name = building.kind if building else top.building_id
        _draw_text(surface, font, f"Passed over {name}: {top.reason}", INSPECTOR_MUTED, (x, y), width)
        y += 19
    return y


def _draw_chip(
    surface: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    pos: tuple[int, int],
    *,
    color: tuple[int, int, int] = PANEL_BG_3,
) -> pygame.Rect:
    glyph = font.render(text, True, INSPECTOR_TEXT)
    rect = pygame.Rect(pos[0], pos[1], glyph.get_width() + 12, glyph.get_height() + 6)
    pygame.draw.rect(surface, color, rect, border_radius=2)
    pygame.draw.rect(surface, (55, 62, 65), rect, 1, border_radius=2)
    surface.blit(glyph, (rect.x + 6, rect.y + 3))
    return rect


def _draw_tab_strip(surface: pygame.Surface, font: pygame.font.Font, rect: pygame.Rect) -> None:
    tabs = ("Log", "Gear", "Social", "Bio", "Needs", "Health")
    tab_w = rect.width // len(tabs)
    for index, tab in enumerate(tabs):
        tab_rect = pygame.Rect(rect.x + index * tab_w, rect.y, tab_w, rect.height)
        fill = (101, 75, 43) if tab == "Needs" else (70, 56, 38)
        pygame.draw.rect(surface, fill, tab_rect)
        pygame.draw.rect(surface, PANEL_HILITE, tab_rect, 1)
        glyph = font.render(tab, True, (238, 230, 210))
        surface.blit(
            glyph,
            (
                tab_rect.centerx - glyph.get_width() // 2,
                tab_rect.centery - glyph.get_height() // 2,
            ),
        )


def _draw_pawn_roster(
    surface: pygame.Surface,
    state: FactionState,
    assets: CivilizationAssets,
    font: pygame.font.Font,
    selected_pawn_id: str | None,
    width: int,
) -> None:
    rect = pygame.Rect(0, 0, width, PAWN_ROSTER_HEIGHT)
    pygame.draw.rect(surface, PANEL_BG, rect)
    pygame.draw.line(surface, PANEL_BORDER, rect.bottomleft, rect.bottomright, 1)

    pawn_keys = sorted(assets.pawns_scaled)
    if not pawn_keys:
        return

    card_w = 58
    gap = 8
    x = MARGIN
    y = 7
    for pawn in state.pawns.values():
        if x + card_w > width - MARGIN:
            break
        selected = pawn.id == selected_pawn_id
        card = pygame.Rect(x, y, card_w, PAWN_ROSTER_HEIGHT - 14)
        pygame.draw.rect(surface, PANEL_BG_2, card, border_radius=3)
        pygame.draw.rect(surface, SELECTION if selected else PANEL_BORDER, card, 2 if selected else 1, border_radius=3)

        sprite = assets.pawns_scaled[_pawn_sprite_key(pawn, pawn_keys)]
        portrait_h = 30
        scale = portrait_h / sprite.get_height()
        portrait = pygame.transform.scale(sprite, (max(1, round(sprite.get_width() * scale)), portrait_h))
        px = card.centerx - portrait.get_width() // 2
        surface.blit(portrait, (px, card.y + 5))
        pygame.draw.circle(surface, (7, 9, 9), (card.right - 8, card.y + 9), 5)
        pygame.draw.circle(surface, _mood_color(pawn.mood / 100), (card.right - 8, card.y + 9), 4)

        short_name = pawn.name.split()[0]
        _draw_text(surface, font, short_name, INSPECTOR_TEXT, (card.x + 4, card.bottom - 15), card.width - 8)
        x += card_w + gap


def _draw_inspector(
    surface: pygame.Surface,
    state: FactionState,
    font: pygame.font.Font,
    selected_pawn_id: str | None,
    rect: pygame.Rect,
) -> None:
    pygame.draw.rect(surface, INSPECTOR_BG, rect)
    pygame.draw.line(surface, INSPECTOR_BORDER, rect.topleft, rect.bottomleft, 1)

    x = rect.x + 14
    y = rect.y + 14

    def line(text: str, color: tuple[int, int, int] = INSPECTOR_TEXT, gap: int = 21, *, max_width: int | None = None) -> None:
        nonlocal y
        _draw_text(surface, font, text, color, (x, y), max_width or rect.width - 28)
        y += gap

    pawn = state.pawns.get(selected_pawn_id or "")
    if pawn is None:
        line("Inspector", gap=25)
        line("No pawn selected", INSPECTOR_MUTED, gap=26)
        line(f"Mood {round(economy.average_mood(state))}", INSPECTOR_MUTED)
        line(f"Coin {state.coin}", INSPECTOR_MUTED)
        return

    status = _pawn_status_label(pawn)
    line(pawn.name, INSPECTOR_TEXT, gap=25)
    _draw_chip(surface, font, status, (x, y), color=(62, 78, 66) if status == "Healthy" else (94, 56, 46))
    _draw_chip(surface, font, pawn.schedule, (x + 94, y), color=PANEL_BG_3)
    y += 32

    line(f"State  {pawn.state}", INSPECTOR_MUTED)
    if pawn.assignment is None:
        line("Job    none", INSPECTOR_MUTED)
    else:
        building = state.buildings.get(pawn.assignment.building_id)
        building_name = building.kind if building else pawn.assignment.building_id
        line(f"Job    {building_name}", INSPECTOR_MUTED)

    y = _draw_work_trace(surface, font, state, pawn, x, y + 4, rect.width - 28) + 2

    tab_rect = pygame.Rect(rect.x, y + 5, rect.width, 28)
    _draw_tab_strip(surface, font, tab_rect)
    y = tab_rect.bottom + 14

    line("Needs", SELECTION, gap=24)
    _draw_value_bar(
        surface, font, "Mood", pawn.mood / 100, pygame.Rect(x, y, rect.width - 28, 22), color=_mood_color(pawn.mood / 100)
    )
    y += 24
    for need, value in sorted(pawn.needs.items()):
        _draw_value_bar(surface, font, need.title(), value, pygame.Rect(x, y, rect.width - 28, 22))
        y += 24

    y = _draw_thoughts(surface, font, pawn, x, y, rect.width - 28)

    y += 8
    line("Skills", SELECTION, gap=23)
    skill_x = x + 98
    max_score = 20
    for skill, score in _top_skills(pawn, limit=8):
        _draw_text(surface, font, skill.title(), INSPECTOR_TEXT, (x, y), 90)
        bar = pygame.Rect(skill_x, y + 4, rect.width - 140, 12)
        pygame.draw.rect(surface, PANEL_BG_3, bar)
        pygame.draw.rect(surface, (86, 91, 97), (bar.x, bar.y, round(bar.width * min(score, max_score) / max_score), bar.height))
        pygame.draw.rect(surface, (50, 57, 60), bar, 1)
        _draw_text(surface, font, str(score), INSPECTOR_TEXT, (bar.right + 8, y), 24)
        y += 22

    y += 8
    line("Traits", SELECTION, gap=22)
    chip_x = x
    chip_y = y
    for trait in pawn.traits:
        chip = _draw_chip(surface, font, trait.replace("_", " ").title(), (chip_x, chip_y))
        chip_x = chip.right + 6
        if chip_x > rect.right - 78:
            chip_x = x
            chip_y += chip.height + 6


def hud_button_rects(width: int, height: int) -> dict[str, pygame.Rect]:
    """Bottom-strip command-button rects, so draw and click hit-test agree."""
    button_y = height - HUD_BUTTON_H
    return {
        label: pygame.Rect(index * (HUD_BUTTON_W + 2), button_y, HUD_BUTTON_W, HUD_BUTTON_H)
        for index, label in enumerate(HUD_BUTTONS)
    }


def idle_pawn_count(state: FactionState) -> int:
    """Pawns with no work assignment that are not mid-break (the arbiter left idle)."""
    return sum(
        1
        for pawn in state.pawns.values()
        if pawn.assignment is None and pawn.state not in (STATE_WANDERING, STATE_SLACKING)
    )


# --- Work-priority grid (RimWorld Work tab) ---------------------------------

WORK_GRID_NAME_W = 132
WORK_GRID_CELL_W = 58
WORK_GRID_ROW_H = 24
WORK_GRID_HEADER_H = 26
WORK_GRID_TITLE_H = 30
WORK_GRID_PAD = 10
# Left-click cycles a cell forward through this ladder (then wraps to disabled).
_PRIORITY_CYCLE = {0: 1, 1: 2, 2: 3, 3: 4, 4: 0}


@dataclass
class WorkGridLayout:
    """Geometry for the Work grid, shared by the renderer and the click hit-test."""

    panel: pygame.Rect
    headers: list[tuple[pygame.Rect, str]] = field(default_factory=list)
    rows: list[tuple[str, pygame.Rect]] = field(default_factory=list)
    cells: list[tuple[pygame.Rect, str, str]] = field(default_factory=list)


def work_grid_layout(map_rect: pygame.Rect, pawn_ids: list[str]) -> WorkGridLayout:
    """Compute the Work-grid panel and its header/row/cell rects, centred in the map."""
    cols = WORK_GRID_TYPES
    grid_w = WORK_GRID_NAME_W + WORK_GRID_CELL_W * len(cols)
    panel_w = grid_w + WORK_GRID_PAD * 2
    body_room = map_rect.height - 2 * MARGIN - WORK_GRID_TITLE_H - WORK_GRID_HEADER_H - WORK_GRID_PAD * 2
    max_rows = max(1, body_room // WORK_GRID_ROW_H)
    rows = pawn_ids[:max_rows]
    panel_h = WORK_GRID_TITLE_H + WORK_GRID_HEADER_H + WORK_GRID_ROW_H * len(rows) + WORK_GRID_PAD * 2
    panel = pygame.Rect(0, 0, panel_w, min(panel_h, map_rect.height - 2 * MARGIN))
    panel.center = map_rect.center

    cols_x = panel.x + WORK_GRID_PAD + WORK_GRID_NAME_W
    header_y = panel.y + WORK_GRID_PAD + WORK_GRID_TITLE_H
    headers = [
        (pygame.Rect(cols_x + i * WORK_GRID_CELL_W, header_y, WORK_GRID_CELL_W, WORK_GRID_HEADER_H), wt)
        for i, wt in enumerate(cols)
    ]
    layout = WorkGridLayout(panel=panel, headers=headers)
    body_y = header_y + WORK_GRID_HEADER_H
    for r, pid in enumerate(rows):
        row_y = body_y + r * WORK_GRID_ROW_H
        layout.rows.append((pid, pygame.Rect(panel.x + WORK_GRID_PAD, row_y, grid_w, WORK_GRID_ROW_H)))
        for i, wt in enumerate(cols):
            layout.cells.append(
                (pygame.Rect(cols_x + i * WORK_GRID_CELL_W, row_y, WORK_GRID_CELL_W, WORK_GRID_ROW_H), pid, wt)
            )
    return layout


def work_grid_cell_at(map_rect: pygame.Rect, pawn_ids: list[str], pos: tuple[int, int]) -> tuple[str, str] | None:
    """The (pawn_id, work_type) cell under ``pos``, or None."""
    for rect, pid, wt in work_grid_layout(map_rect, pawn_ids).cells:
        if rect.collidepoint(pos):
            return (pid, wt)
    return None


def cycle_work_priority(state: FactionState, pawn_id: str, work_type: str) -> None:
    """Advance one pawn's priority for a work type to the next rung on a click."""
    pawn = state.pawns.get(pawn_id)
    if pawn is None:
        return
    current = work.default_priority(pawn, work_type)
    work.set_priority(pawn, work_type, _PRIORITY_CYCLE.get(current, 1))


def _draw_work_grid(
    surface: pygame.Surface,
    state: FactionState,
    font: pygame.font.Font,
    selected_pawn_id: str | None,
    map_rect: pygame.Rect,
) -> None:
    pawn_ids = sorted(state.pawns)
    layout = work_grid_layout(map_rect, pawn_ids)
    panel = layout.panel

    backdrop = pygame.Surface((map_rect.width, map_rect.height), pygame.SRCALPHA)
    backdrop.fill((6, 8, 9, 150))
    surface.blit(backdrop, map_rect.topleft)
    pygame.draw.rect(surface, PANEL_BG, panel)
    pygame.draw.rect(surface, PANEL_BORDER, panel, 1)

    _draw_text(
        surface,
        font,
        "Work priorities - click to cycle  (1 top .. 4 low, blank off)",
        SELECTION,
        (panel.x + WORK_GRID_PAD, panel.y + 8),
        panel.width - WORK_GRID_PAD * 2,
    )

    for rect, wt in layout.headers:
        glyph = font.render(WORK_TYPE_LABEL.get(wt, wt[:4].title()), True, INSPECTOR_TEXT)
        surface.blit(glyph, (rect.centerx - glyph.get_width() // 2, rect.y + 6))

    selected_rows = {pid for pid, _ in layout.rows if pid == selected_pawn_id}
    for pid, row_rect in layout.rows:
        if pid in selected_rows:
            pygame.draw.rect(surface, PANEL_BG_3, row_rect)
        pawn = state.pawns[pid]
        _draw_text(
            surface,
            font,
            pawn.name.split()[0],
            INSPECTOR_TEXT,
            (row_rect.x + 4, row_rect.y + 4),
            WORK_GRID_NAME_W - 8,
        )

    for rect, pid, wt in layout.cells:
        pygame.draw.rect(surface, (12, 15, 16), rect, 1)
        level = work.default_priority(state.pawns[pid], wt)
        if level <= 0:
            continue
        pygame.draw.rect(surface, WORK_PRIORITY_COLOR.get(level, PANEL_BG_3), rect.inflate(-8, -6))
        glyph = font.render(str(level), True, (12, 15, 16))
        surface.blit(glyph, (rect.centerx - glyph.get_width() // 2, rect.centery - glyph.get_height() // 2))


# --- History / event feed (run-log monitoring) ------------------------------

SEVERITY_COLOR = {
    health.INFO: (150, 170, 158),
    health.WARN: NEED_WARN,
    health.CRITICAL: NEED_BAD,
}


def _draw_translucent_panel(surface: pygame.Surface, rect: pygame.Rect, *, alpha: int = 220) -> None:
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    panel.fill((*PANEL_BG, alpha))
    surface.blit(panel, rect.topleft)
    pygame.draw.rect(surface, PANEL_BORDER, rect, 1)


def _draw_exception_stack(
    surface: pygame.Surface,
    font: pygame.font.Font,
    items: list[ExceptionStackItem],
    map_rect: pygame.Rect,
) -> pygame.Rect | None:
    """Right-edge active-problem stack, sorted by severity and actionability."""
    width = min(EXCEPTION_STACK_WIDTH, map_rect.width - MARGIN * 2)
    if width < 220:
        return None
    rows = items[:EXCEPTION_STACK_MAX]
    height = 58 if not rows else 34 + len(rows) * 42 + (20 if len(items) > len(rows) else 8)
    rect = pygame.Rect(map_rect.right - MARGIN - width, map_rect.y + MARGIN, width, height)

    _draw_translucent_panel(surface, rect)
    x = rect.x + 10
    y = rect.y + 8
    _draw_text(surface, font, "Exceptions", SELECTION, (x, y), width - 96)
    count_text = "clear" if not items else str(len(items))
    count_color = NEED_GOOD if not items else SEVERITY_COLOR.get(rows[0].severity, NEED_WARN)
    _draw_text(surface, font, count_text, count_color, (rect.right - 62, y), 52)
    y += 24

    if not rows:
        pygame.draw.circle(surface, NEED_GOOD, (x + 5, y + 8), 4)
        _draw_text(surface, font, "No active governor exceptions", INSPECTOR_MUTED, (x + 16, y), width - 28)
        return rect

    for item in rows:
        color = SEVERITY_COLOR.get(item.severity, INSPECTOR_TEXT)
        pygame.draw.circle(surface, color, (x + 5, y + 7), 4)
        _draw_text(surface, font, item.title, INSPECTOR_TEXT, (x + 16, y - 1), width - 28)
        _draw_text(surface, font, item.cause, INSPECTOR_MUTED, (x + 16, y + 18), width - 28)
        y += 42
    remaining = len(items) - len(rows)
    if remaining > 0:
        _draw_text(surface, font, f"+{remaining} more", INSPECTOR_MUTED, (x + 16, y), width - 28)
    return rect


def _draw_governor_card(
    surface: pygame.Surface,
    font: pygame.font.Font,
    summary: GovernorCardSummary,
    map_rect: pygame.Rect,
) -> pygame.Rect | None:
    """Bottom-left situation card: plan, bottleneck, confidence, recent policy."""
    width = min(GOVERNOR_CARD_WIDTH, map_rect.width - MARGIN * 2)
    if width < 240:
        return None
    height = min(GOVERNOR_CARD_HEIGHT, map_rect.height - MARGIN * 2)
    rect = pygame.Rect(map_rect.x + MARGIN, map_rect.bottom - MARGIN - height, width, height)
    if rect.y < map_rect.y + MARGIN:
        rect.y = map_rect.y + MARGIN

    _draw_translucent_panel(surface, rect)
    x = rect.x + 10
    y = rect.y + 8
    confidence_color = NEED_GOOD if summary.confidence >= 80 else NEED_WARN if summary.confidence >= 65 else NEED_BAD
    _draw_text(surface, font, "Governor", SELECTION, (x, y), width - 88)
    _draw_text(surface, font, f"{summary.confidence}%", confidence_color, (rect.right - 52, y), 44)
    y += 22

    rows = (
        ("Plan", summary.plan),
        ("Phase", summary.phase),
        ("Bottleneck", summary.bottleneck),
        ("Last", summary.last_reallocation),
    )
    for label, value in rows:
        _draw_text(surface, font, label, INSPECTOR_MUTED, (x, y), 76)
        _draw_text(surface, font, value, INSPECTOR_TEXT, (x + 78, y), width - 88)
        y += 20

    top = summary.top_exception.title if summary.top_exception is not None else "clear"
    color = (
        SEVERITY_COLOR.get(summary.top_exception.severity, INSPECTOR_TEXT)
        if summary.top_exception is not None
        else NEED_GOOD
    )
    _draw_text(surface, font, "Top", INSPECTOR_MUTED, (x, y), 76)
    _draw_text(surface, font, top, color, (x + 78, y), width - 88)
    if summary.exception_count > 1:
        _draw_text(surface, font, f"{summary.exception_count} active", INSPECTOR_MUTED, (x + 78, y + 18), width - 88)
    return rect


def _draw_history_panel(
    surface: pygame.Surface,
    font: pygame.font.Font,
    events: list[dict],
    map_rect: pygame.Rect,
) -> None:
    """Scrolling feed of recent run-log events (newest first), severity-coloured."""
    width = min(560, map_rect.width - 2 * MARGIN)
    height = min(map_rect.height - 2 * MARGIN, 30 + 19 * 18 + 12)
    panel = pygame.Rect(0, 0, width, height)
    panel.center = map_rect.center

    backdrop = pygame.Surface((map_rect.width, map_rect.height), pygame.SRCALPHA)
    backdrop.fill((6, 8, 9, 150))
    surface.blit(backdrop, map_rect.topleft)
    pygame.draw.rect(surface, PANEL_BG, panel)
    pygame.draw.rect(surface, PANEL_BORDER, panel, 1)

    _draw_text(surface, font, "History - recent events (newest first)", SELECTION,
               (panel.x + WORK_GRID_PAD, panel.y + 8), panel.width - WORK_GRID_PAD * 2)
    y = panel.y + 32
    rows = max(1, (panel.bottom - 10 - y) // 18)
    recent = list(events)[-rows:][::-1]
    if not recent:
        _draw_text(surface, font, "No events yet - the town is running clean.", INSPECTOR_MUTED,
                   (panel.x + WORK_GRID_PAD, y), panel.width - WORK_GRID_PAD * 2)
        return
    for event in recent:
        color = SEVERITY_COLOR.get(event.get("severity"), INSPECTOR_TEXT)
        stamp = f"d{event.get('day', 0)} {event.get('hour', 0):>2}:00"
        pygame.draw.circle(surface, color, (panel.x + WORK_GRID_PAD + 4, y + 7), 4)
        text = f"{stamp}  {event.get('text', event.get('kind', ''))}"
        _draw_text(surface, font, text, color, (panel.x + WORK_GRID_PAD + 14, y), panel.width - WORK_GRID_PAD * 2 - 14)
        y += 18


def _draw_hud(
    surface: pygame.Surface,
    state: FactionState,
    font: pygame.font.Font,
    status_line: tuple[str, tuple[int, int, int]] | None = None,
    *,
    work_grid_open: bool = False,
    history_open: bool = False,
    alert: tuple[str, int] | None = None,
) -> None:
    width = surface.get_width()
    top = surface.get_height() - HUD_HEIGHT
    pygame.draw.rect(surface, HUD_BG, (0, top, width, HUD_HEIGHT))
    pygame.draw.line(surface, PANEL_BORDER, (0, top), (width, top), 1)

    population = len(state.pawns)
    avg_mood = economy.average_mood(state)
    sites = len(state.construction_sites)
    stat_items = (
        f"Day {state.day}",
        f"{state.time_of_day:02d}:00",
        f"Pop {population}",
        f"Mood {round(avg_mood)}",
        f"Coin {state.coin}",
        f"Idle {idle_pawn_count(state)}",
        f"Sites {sites}",
    )

    text, color = status_line or ("Governor: fallback (autopilot)   pawns coloured by mood", HUD_MUTED)
    x = MARGIN
    for item in stat_items:
        glyph = font.render(item, True, HUD_TEXT)
        box = pygame.Rect(x, top + 10, glyph.get_width() + 16, 24)
        pygame.draw.rect(surface, PANEL_BG_2, box, border_radius=2)
        pygame.draw.rect(surface, (58, 67, 69), box, 1, border_radius=2)
        surface.blit(glyph, (box.x + 8, box.y + 5))
        x = box.right + 8

    x = MARGIN
    for label, good in HUD_GOODS:
        amount = state.stockpile.counts.get(good, 0)
        text_chip = f"{label} {amount}"
        glyph = font.render(text_chip, True, HUD_TEXT)
        box = pygame.Rect(x, top + 41, glyph.get_width() + 16, 24)
        pygame.draw.rect(surface, (31, 36, 34), box, border_radius=2)
        pygame.draw.rect(surface, (56, 64, 58), box, 1, border_radius=2)
        surface.blit(glyph, (box.x + 8, box.y + 5))
        x = box.right + 8

    alert_severity, alert_count = alert if alert else (None, 0)
    alert_color = SEVERITY_COLOR.get(alert_severity)

    status_width = width - MARGIN * 2
    if alert_color is not None:
        status_width -= 128
    _draw_text(surface, font, text, color, (MARGIN, top + 72), status_width)

    # Alert chip: lights amber/red and shows the unacknowledged event count when
    # the latest hours produced warn/critical events.
    if alert_color is not None:
        chip = pygame.Rect(width - MARGIN - 116, top + 68, 116, 24)
        pygame.draw.rect(surface, (35, 30, 28), chip, border_radius=2)
        pygame.draw.rect(surface, alert_color, chip, 1, border_radius=2)
        pygame.draw.circle(surface, alert_color, (chip.x + 13, chip.centery), 5)
        label = f"{alert_count} alert" + ("s" if alert_count != 1 else "")
        _draw_text(surface, font, label, HUD_TEXT, (chip.x + 26, chip.y + 5), chip.width - 32)

    open_map = {"Work": work_grid_open, "History": history_open}
    for label, button in hud_button_rects(width, surface.get_height()).items():
        active = open_map.get(label, False)
        # A closed History button glows in the alert colour when something is wrong.
        alerting = label == "History" and not active and alert_color is not None
        fill = (101, 75, 43) if active else (31, 42, 45)
        border = SELECTION if active else (alert_color if alerting else PANEL_BORDER)
        pygame.draw.rect(surface, fill, button)
        pygame.draw.rect(surface, border, button, 2 if alerting else 1)
        glyph = font.render(label, True, HUD_TEXT)
        surface.blit(glyph, (button.centerx - glyph.get_width() // 2, button.centery - glyph.get_height() // 2))


class CivilizationViewer:
    """Steps the engine under a governor and renders the civilization.

    By default the live viewer drives the civilization with a
    :class:`CivilizationDecisionScheduler`, so a local LLM governs on autopilot
    without blocking the render loop, with the deterministic fallback covering
    every gap. Smoke-test runs use the bare fallback so they stay deterministic
    and touch no network. Press ``L`` to toggle the LLM on and off at runtime.
    """

    def __init__(
        self,
        state: FactionState | None = None,
        *,
        smoke_test: bool = False,
        governor: Governor | None = None,
    ) -> None:
        pygame.init()
        pygame.font.init()
        self.smoke_test = smoke_test
        self.state = state if state is not None else create_default_civilization()
        if governor is None:
            governor = FallbackGovernor() if smoke_test else CivilizationDecisionScheduler.from_env()
        self.governor = governor
        self.camera = Camera()
        self.selected_pawn_id = next(iter(self.state.pawns), None)
        self.hovered_pawn_id: str | None = None
        self.show_work_grid = False
        self.show_history = False
        # Latched alert: worst severity and count of warn/critical events since
        # History was last opened, so a one-hour critical does not flash by unseen.
        self._alert_severity: str | None = None
        self._alert_count = 0
        # Run-log telemetry: an events ring backs the live History feed, and (in a
        # real run) a JSONL file backs offline analysis. A pass-through wrapper
        # around the governor captures what it proposed each hour. Logging is a
        # pure observer - it never changes the simulation.
        self.event_ring = telemetry.RingBufferSink(maxlen=200, types={"event"})
        log_sinks: list = [self.event_ring]
        self.log_path = None
        if not smoke_test:
            self.log_path = telemetry.default_run_log_path()
            log_sinks.append(telemetry.JsonlFileSink(self.log_path))
        self.logger = telemetry.RunLogger(telemetry.MultiSink(log_sinks))
        self._step_governor = telemetry.TelemetryGovernor(self.governor)
        self.logger.log_run_start(self.state, self._step_governor, source="viewer")
        self.assets = None  # set after the display mode exists

        grid = self.state.grid
        ts = load_civilization_manifest().tile_size
        width = (grid.width * ts if grid else 600) + 2 * MARGIN + INSPECTOR_WIDTH
        height = (grid.height * ts if grid else 400) + 2 * MARGIN + HUD_HEIGHT + PAWN_ROSTER_HEIGHT
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Local Agent Town - Civilization")

        self.assets = load_civilization_assets()
        self._clamp_camera()
        self.font = _load_font()
        self.clock = pygame.time.Clock()
        self.running = True
        self._accum = 0.0

    def run(self) -> None:
        frames = 0
        try:
            while self.running:
                dt = self.clock.tick(60) / 1000.0
                self._handle_events()
                self._advance(dt)
                self._draw()
                frames += 1
                if self.smoke_test and frames >= SMOKE_FRAMES:
                    self.running = False
        finally:
            self._shutdown_governor()

    def _handle_events(self) -> None:
        if self.smoke_test:
            return
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_q:
                self.running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if self.show_work_grid or self.show_history:
                    self.show_work_grid = False
                    self.show_history = False
                else:
                    self.running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_l:
                self._toggle_governor()
            elif event.type == pygame.KEYDOWN:
                self._handle_camera_key(event.key)
            elif event.type == pygame.MOUSEMOTION:
                self._update_hover(event.pos)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_click(event.pos)
            elif event.type == pygame.MOUSEWHEEL:
                factor = ZOOM_STEP if event.y > 0 else 1.0 / ZOOM_STEP
                self._zoom_camera(factor, pygame.mouse.get_pos())

    def _handle_camera_key(self, key: int) -> None:
        if key in (pygame.K_RIGHT, pygame.K_d):
            self._pan_camera(CAMERA_PAN_PX, 0)
        elif key in (pygame.K_LEFT, pygame.K_a):
            self._pan_camera(-CAMERA_PAN_PX, 0)
        elif key in (pygame.K_DOWN, pygame.K_s):
            self._pan_camera(0, CAMERA_PAN_PX)
        elif key in (pygame.K_UP, pygame.K_w):
            self._pan_camera(0, -CAMERA_PAN_PX)
        elif key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
            self._zoom_camera(ZOOM_STEP)
        elif key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self._zoom_camera(1.0 / ZOOM_STEP)
        elif key == pygame.K_TAB:
            self._select_next_pawn()

    def _map_rect(self) -> pygame.Rect:
        return pygame.Rect(
            0,
            PAWN_ROSTER_HEIGHT,
            self.screen.get_width() - INSPECTOR_WIDTH,
            self.screen.get_height() - HUD_HEIGHT - PAWN_ROSTER_HEIGHT,
        )

    def _map_origin(self) -> tuple[int, int]:
        return (MARGIN, PAWN_ROSTER_HEIGHT + MARGIN)

    def _pan_camera(self, screen_dx: float, screen_dy: float) -> None:
        self.camera.pan(screen_dx, screen_dy)
        self._clamp_camera()

    def _zoom_camera(self, factor: float, anchor: tuple[int, int] | None = None) -> None:
        if anchor is None:
            anchor = self._map_rect().center
        self.camera.zoom_by(factor, anchor, self._map_origin())
        self._clamp_camera()

    def _clamp_camera(self) -> None:
        grid = self.state.grid
        if grid is None:
            return
        tile_size = load_civilization_manifest().tile_size
        world_size = (grid.width * tile_size, grid.height * tile_size)
        self.camera.clamp_to_world(world_size, self._map_rect().size)

    def _handle_click(self, pos: tuple[int, int]) -> None:
        # The bottom-strip Work / History buttons toggle their panels from
        # anywhere; the two panels are mutually exclusive (both overlay the map).
        buttons = hud_button_rects(self.screen.get_width(), self.screen.get_height())
        if buttons["Work"].collidepoint(pos):
            self.show_work_grid = not self.show_work_grid
            self.show_history = False
            return
        if buttons["History"].collidepoint(pos):
            self.show_history = not self.show_history
            self.show_work_grid = False
            if self.show_history:
                self._alert_severity = None  # opening the feed acknowledges alerts
                self._alert_count = 0
            return
        # While the grid is open it is modal over the map: a cell click cycles a
        # priority and the pawn re-routes on the next engine step; other clicks
        # are swallowed so they do not also reselect a pawn underneath.
        if self.show_work_grid:
            cell = work_grid_cell_at(self._map_rect(), sorted(self.state.pawns), pos)
            if cell is not None:
                cycle_work_priority(self.state, cell[0], cell[1])
            return
        if self.show_history:
            return  # the feed is read-only; swallow clicks over it
        self._select_pawn_at(pos)

    def _update_hover(self, pos: tuple[int, int]) -> None:
        if self.show_work_grid or self.show_history or not self._map_rect().collidepoint(pos) or self.assets is None:
            self.hovered_pawn_id = None
            return
        self.hovered_pawn_id = find_pawn_at_screen(
            self.state,
            pos,
            self._map_origin(),
            self.assets.tile_size,
            self.camera,
        )

    def _select_pawn_at(self, pos: tuple[int, int]) -> None:
        if not self._map_rect().collidepoint(pos) or self.assets is None:
            return
        pawn_id = find_pawn_at_screen(self.state, pos, self._map_origin(), self.assets.tile_size, self.camera)
        if pawn_id is not None:
            self.selected_pawn_id = pawn_id

    def _select_next_pawn(self) -> None:
        pawn_ids = sorted(self.state.pawns)
        if not pawn_ids:
            self.selected_pawn_id = None
            return
        if self.selected_pawn_id not in pawn_ids:
            self.selected_pawn_id = pawn_ids[0]
            return
        index = pawn_ids.index(self.selected_pawn_id)
        self.selected_pawn_id = pawn_ids[(index + 1) % len(pawn_ids)]

    def _toggle_governor(self) -> None:
        toggle = getattr(self.governor, "toggle", None)
        if callable(toggle):
            toggle()

    def _shutdown_governor(self) -> None:
        try:
            self.logger.log_run_end(self.state)
            self.logger.close()
        except Exception:
            pass
        shutdown = getattr(self.governor, "shutdown", None)
        if callable(shutdown):
            shutdown(wait=False)

    def _advance(self, dt: float) -> None:
        if self.smoke_test:
            self._step_and_log()
            return
        self._accum += dt
        while self._accum >= STEP_INTERVAL:
            self._step_and_log()
            self._accum -= STEP_INTERVAL

    def _step_and_log(self) -> None:
        result = engine.step_hour(self.state, self._step_governor)
        _snap, _decision, events = self.logger.log_hour(self.state, result, self._step_governor)
        # Latch the worst severity and tally unacknowledged warn/critical events
        # so the HUD alert persists until the History feed is opened.
        new_alerts = sum(1 for e in events if e.get("severity") in (health.WARN, health.CRITICAL))
        if new_alerts:
            self._alert_count += new_alerts
            self._alert_severity = health.max_severity(
                [{"severity": s} for s in (self._alert_severity, self.logger.last_severity) if s]
            )

    def _draw(self) -> None:
        alert = (self._alert_severity, self._alert_count) if self._alert_severity and not self.show_history else None
        render_civilization(
            self.screen,
            self.state,
            self.assets,
            self.font,
            self._map_origin(),
            status_line=governor_status_line(self.governor),
            camera=self.camera,
            selected_pawn_id=self.selected_pawn_id,
            hovered_pawn_id=self.hovered_pawn_id,
            show_inspector=True,
            show_work_grid=self.show_work_grid,
            show_history=self.show_history,
            events=list(self.event_ring.records),
            alert=alert,
            governor_summary=governor_card_summary(
                self.state,
                self._step_governor,
                last_actions=self._step_governor.last_actions,
            ),
        )
        pygame.display.flip()


def _load_font() -> pygame.font.Font:
    try:
        font = pygame.font.SysFont("consolas,dejavusansmono,monospace", 14)
        if font is not None:
            return font
    except Exception:
        pass
    return pygame.font.Font(None, 18)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Local Agent Town civilization viewer.")
    parser.add_argument("--smoke-test", action="store_true", help="Open briefly, draw a few frames, then exit.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.smoke_test:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    CivilizationViewer(smoke_test=args.smoke_test).run()


if __name__ == "__main__":
    main()
