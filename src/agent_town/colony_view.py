"""Colony viewer (integration milestone I3).

Renders the build-1 colony ``FactionState`` - terrain tiles, resource nodes,
buildings, pawns, and a HUD - and steps the engine so the colony visibly runs.
The live viewer governs via a non-blocking :class:`ColonyDecisionScheduler` (a
local LLM on autopilot, with the deterministic fallback covering every gap);
press ``L`` to toggle the LLM on and off. Uses the authored colony sprite set
(``assets/colony``), falling back to simple shapes only where no sprite exists
(e.g. grain/stone nodes, pawns).

This replaces the legacy social-sim as the default ``python -m agent_town``
view. The legacy ``app.py`` stays importable until it is fully retired.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field

import pygame

from . import economy, engine
from .assets import ColonyAssetManifest, load_colony_manifest
from .core import FactionState, Good
from .colony import create_default_colony
from .governor import (
    GOV_DISABLED,
    GOV_IDLE,
    GOV_INVALID,
    GOV_OFFLINE,
    GOV_THINKING,
    ColonyDecisionScheduler,
    FallbackGovernor,
    Governor,
)
from .pawns import STATE_WANDERING, STATE_SLACKING

MARGIN = 12
HUD_HEIGHT = 92
STEP_INTERVAL = 0.6  # real seconds per simulated hour at normal speed
SMOKE_FRAMES = 8
BUILDING_TILE_WIDTH = 2  # buildings are scaled to this many tiles wide
PAWN_RENDER_HEIGHT = 26  # pawn sprites are scaled to this height (aspect kept)

BACKGROUND = (38, 44, 38)
HUD_BG = (18, 20, 18)
HUD_TEXT = (226, 230, 220)
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
    """A one-line HUD summary of how the colony is being governed right now.

    A plain governor (no ``status``) reads as fallback autopilot; a
    :class:`ColonyDecisionScheduler` reports its live LLM connection state and
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
class ColonyAssets:
    """Loaded colony sprites: raw surfaces plus pre-scaled building sprites."""

    tile_size: int
    surfaces: dict[str, pygame.Surface] = field(default_factory=dict)
    buildings_scaled: dict[str, pygame.Surface] = field(default_factory=dict)
    pawns_scaled: dict[str, pygame.Surface] = field(default_factory=dict)


def load_colony_assets(manifest: ColonyAssetManifest | None = None) -> ColonyAssets:
    """Load every colony sprite and pre-scale building + pawn sprites."""
    manifest = manifest or load_colony_manifest()
    assets = ColonyAssets(tile_size=manifest.tile_size)
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


def render_colony(
    surface: pygame.Surface,
    state: FactionState,
    assets: ColonyAssets,
    font: pygame.font.Font,
    origin: tuple[int, int],
    *,
    status_line: tuple[str, tuple[int, int, int]] | None = None,
) -> None:
    """Draw the whole colony (tiles, nodes, buildings, pawns, HUD) onto ``surface``."""
    surface.fill(BACKGROUND)
    grid = state.grid
    ts = assets.tile_size
    ox, oy = origin

    if grid is not None:
        for y in range(grid.height):
            for x in range(grid.width):
                kind = grid.tile_at(x, y)
                surface.blit(assets.surfaces[TERRAIN_TILE.get(kind, "grass")], (ox + x * ts, oy + y * ts))
                if kind == "water":
                    tint = pygame.Surface((ts, ts), pygame.SRCALPHA)
                    tint.fill(WATER_TINT)
                    surface.blit(tint, (ox + x * ts, oy + y * ts))

    for node in state.resource_nodes:
        _draw_node(surface, node, assets, ox, oy, ts)

    for building in sorted(state.buildings.values(), key=lambda b: (b.y, b.x, b.id)):
        _draw_building(surface, building, assets, font, ox, oy, ts)

    pawn_keys = sorted(assets.pawns_scaled)
    for pawn in state.pawns.values():
        _draw_pawn(surface, pawn, assets, pawn_keys, ox, oy, ts)

    _draw_hud(surface, state, font, status_line)


def _draw_node(surface, node, assets: ColonyAssets, ox: int, oy: int, ts: int) -> None:
    cx = ox + node.x * ts + ts // 2
    bottom = oy + node.y * ts + ts
    prop = NODE_PROP.get(node.kind)
    if prop is not None:
        sprite = assets.surfaces[prop]
        surface.blit(sprite, (cx - sprite.get_width() // 2, bottom - sprite.get_height()))
        return
    color = NODE_MARKER_COLOR.get(node.kind, (180, 180, 180))
    pygame.draw.circle(surface, color, (cx, oy + node.y * ts + ts // 2), max(4, ts // 3))


def _draw_building(surface, building, assets: ColonyAssets, font, ox: int, oy: int, ts: int) -> None:
    sprite = assets.buildings_scaled[BUILDING_SPRITE.get(building.kind, DEFAULT_BUILDING_SPRITE)]
    cx = ox + building.x * ts + ts // 2
    bottom = oy + building.y * ts + ts
    surface.blit(sprite, (cx - sprite.get_width() // 2, bottom - sprite.get_height()))

    staffed = len(building.staffed_by)
    label = f"{building.kind} {staffed}/{building.job_slots}"
    _draw_label(surface, font, label, cx, bottom - sprite.get_height() - 2)


def _pawn_sprite_key(pawn, keys: list[str]) -> str:
    """Stable per-pawn sprite pick so a pawn keeps the same look across frames."""
    digits = "".join(ch for ch in pawn.id if ch.isdigit())
    index = int(digits) if digits else sum(map(ord, pawn.id))
    return keys[index % len(keys)]


def _draw_pawn(surface, pawn, assets: ColonyAssets, pawn_keys: list[str], ox: int, oy: int, ts: int) -> None:
    sprite = assets.pawns_scaled[_pawn_sprite_key(pawn, pawn_keys)]
    cx = ox + pawn.x * ts + ts // 2
    cy = oy + pawn.y * ts + ts // 2
    top = cy + 5 - sprite.get_height()
    if pawn.state in (STATE_WANDERING, STATE_SLACKING):
        pygame.draw.circle(surface, (235, 80, 70), (cx, cy + 2), 12, 2)
    surface.blit(sprite, (cx - sprite.get_width() // 2, top))
    # Mood dot above the head keeps mood readable at a glance.
    dot_y = top - 3
    pygame.draw.circle(surface, (20, 24, 20), (cx, dot_y), 4)
    pygame.draw.circle(surface, _mood_color(pawn.mood), (cx, dot_y), 3)


def _draw_label(surface, font, text: str, center_x: int, bottom_y: int) -> None:
    glyph = font.render(text, True, LABEL_TEXT)
    pad = 3
    box = pygame.Surface((glyph.get_width() + pad * 2, glyph.get_height() + pad), pygame.SRCALPHA)
    box.fill(LABEL_BG)
    box.blit(glyph, (pad, 0))
    surface.blit(box, (center_x - box.get_width() // 2, bottom_y - box.get_height()))


def _draw_hud(
    surface: pygame.Surface,
    state: FactionState,
    font: pygame.font.Font,
    status_line: tuple[str, tuple[int, int, int]] | None = None,
) -> None:
    width = surface.get_width()
    top = surface.get_height() - HUD_HEIGHT
    pygame.draw.rect(surface, HUD_BG, (0, top, width, HUD_HEIGHT))

    population = len(state.pawns)
    avg_mood = economy.average_mood(state)
    sites = len(state.construction_sites)
    line1 = (
        f"Day {state.day}   {state.time_of_day:02d}:00   "
        f"Pop {population}   Mood {round(avg_mood * 100)}%   "
        f"Coin {state.coin}   Sites {sites}"
    )
    goods = "   ".join(f"{label} {state.stockpile.counts.get(good, 0)}" for label, good in HUD_GOODS)

    text, color = status_line or ("Governor: fallback (autopilot)   pawns coloured by mood", HUD_MUTED)
    surface.blit(font.render(line1, True, HUD_TEXT), (MARGIN, top + 14))
    surface.blit(font.render(goods, True, HUD_TEXT), (MARGIN, top + 44))
    surface.blit(font.render(text, True, color), (MARGIN, top + 68))


class ColonyViewer:
    """Steps the engine under a governor and renders the colony.

    By default the live viewer drives the colony with a
    :class:`ColonyDecisionScheduler`, so a local LLM governs on autopilot
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
        self.state = state if state is not None else create_default_colony()
        if governor is None:
            governor = FallbackGovernor() if smoke_test else ColonyDecisionScheduler.from_env()
        self.governor = governor
        self.assets = None  # set after the display mode exists

        grid = self.state.grid
        ts = load_colony_manifest().tile_size
        width = (grid.width * ts if grid else 600) + 2 * MARGIN
        height = (grid.height * ts if grid else 400) + 2 * MARGIN + HUD_HEIGHT
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Local Agent Town - Colony")

        self.assets = load_colony_assets()
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
        render_colony(
            self.screen,
            self.state,
            self.assets,
            self.font,
            (MARGIN, MARGIN),
            status_line=governor_status_line(self.governor),
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
    parser = argparse.ArgumentParser(description="Run the Local Agent Town colony viewer.")
    parser.add_argument("--smoke-test", action="store_true", help="Open briefly, draw a few frames, then exit.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.smoke_test:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    ColonyViewer(smoke_test=args.smoke_test).run()


if __name__ == "__main__":
    main()
