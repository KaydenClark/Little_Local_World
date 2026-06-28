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

from . import economy, engine
from .assets import CivilizationAssetManifest, load_civilization_manifest
from .core import FactionState, Good
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
}
DEFAULT_BUILDING_SPRITE = "house"

# Resource-node Good -> prop sprite name (None draws a coloured marker).
NODE_PROP = {Good.LOGS: "tree"}
NODE_MARKER_COLOR = {Good.GRAIN: (214, 188, 84), Good.STONE: (150, 150, 158)}

HUD_GOODS = (
    ("Bread", Good.BREAD),
    ("Grain", Good.GRAIN),
    ("Flour", Good.FLOUR),
    ("Logs", Good.LOGS),
    ("Planks", Good.PLANKS),
    ("Stone", Good.STONE),
)

HUD_MUTED = (150, 156, 148)
GOVERNOR_STATUS_COLOR = {
    GOV_IDLE: (140, 200, 150),
    GOV_THINKING: (220, 200, 120),
    GOV_OFFLINE: (224, 130, 110),
    GOV_INVALID: (224, 130, 110),
    GOV_DISABLED: HUD_MUTED,
}


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
    if pawn.mood < 0.35:
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
    show_inspector: bool = False,
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
        )

    surface.set_clip(previous_clip)
    _draw_pawn_roster(surface, state, assets, font, selected_pawn_id, map_rect.width)
    if inspector_rect is not None:
        _draw_inspector(surface, state, font, selected_pawn_id, inspector_rect)
    _draw_hud(surface, state, font, status_line)


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
) -> None:
    ts = camera.scaled_tile_size(base_ts)
    sprite = _scale_for_camera(assets.pawns_scaled[_pawn_sprite_key(pawn, pawn_keys)], camera)
    cx, cy = camera.tile_center_to_screen(pawn.x, pawn.y, (ox, oy), base_ts)
    top = cy + 5 - sprite.get_height()
    if pawn.state in (STATE_WANDERING, STATE_SLACKING):
        pygame.draw.circle(surface, (235, 80, 70), (cx, cy + 2), 12, 2)
    if selected:
        pygame.draw.circle(surface, SELECTION, (cx, cy + 1), max(10, ts // 2), 2)
    surface.blit(sprite, (cx - sprite.get_width() // 2, top))
    # Mood dot above the head keeps mood readable at a glance.
    dot_y = top - 3
    pygame.draw.circle(surface, (20, 24, 20), (cx, dot_y), 4)
    pygame.draw.circle(surface, _mood_color(pawn.mood), (cx, dot_y), 3)


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
        pygame.draw.circle(surface, _mood_color(pawn.mood), (card.right - 8, card.y + 9), 4)

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
        line(f"Mood {round(economy.average_mood(state) * 100)}%", INSPECTOR_MUTED)
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

    tab_rect = pygame.Rect(rect.x, y + 5, rect.width, 28)
    _draw_tab_strip(surface, font, tab_rect)
    y = tab_rect.bottom + 14

    line("Needs", SELECTION, gap=24)
    _draw_value_bar(surface, font, "Mood", pawn.mood, pygame.Rect(x, y, rect.width - 28, 22), color=_mood_color(pawn.mood))
    y += 24
    for need, value in sorted(pawn.needs.items()):
        _draw_value_bar(surface, font, need.title(), value, pygame.Rect(x, y, rect.width - 28, 22))
        y += 24

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


def _draw_hud(
    surface: pygame.Surface,
    state: FactionState,
    font: pygame.font.Font,
    status_line: tuple[str, tuple[int, int, int]] | None = None,
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
        f"Mood {round(avg_mood * 100)}%",
        f"Coin {state.coin}",
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

    _draw_text(surface, font, text, color, (MARGIN, top + 72), width - MARGIN * 2)

    buttons = ("Architect", "Work", "Assign", "Research", "History", "Menu")
    button_y = top + HUD_HEIGHT - 28
    button_w = 104
    for index, label in enumerate(buttons):
        button = pygame.Rect(index * (button_w + 2), button_y, button_w, 28)
        pygame.draw.rect(surface, (31, 42, 45), button)
        pygame.draw.rect(surface, PANEL_BORDER, button, 1)
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
            elif event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_q):
                self.running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_l:
                self._toggle_governor()
            elif event.type == pygame.KEYDOWN:
                self._handle_camera_key(event.key)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._select_pawn_at(event.pos)
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
        shutdown = getattr(self.governor, "shutdown", None)
        if callable(shutdown):
            shutdown(wait=False)

    def _advance(self, dt: float) -> None:
        if self.smoke_test:
            engine.step_hour(self.state, self.governor)
            return
        self._accum += dt
        while self._accum >= STEP_INTERVAL:
            engine.step_hour(self.state, self.governor)
            self._accum -= STEP_INTERVAL

    def _draw(self) -> None:
        render_civilization(
            self.screen,
            self.state,
            self.assets,
            self.font,
            self._map_origin(),
            status_line=governor_status_line(self.governor),
            camera=self.camera,
            selected_pawn_id=self.selected_pawn_id,
            show_inspector=True,
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
