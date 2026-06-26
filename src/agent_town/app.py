from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from math import floor
import xml.etree.ElementTree as ET

import pygame

from .assets import load_kenney_manifest
from .core import Agent, Location, Simulation, WORLD_HEIGHT, WORLD_WIDTH, create_default_simulation
from .llm import LLMDecisionScheduler, LocalLLMClient


SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 800
PANEL_WIDTH = 330
MIN_ZOOM = 0.35
MAX_ZOOM = 2.25
BACKGROUND = (10, 10, 10)
WORLD_BG = (25, 25, 25)
GRID = (71, 71, 71)
PANEL_BG = (25, 25, 25)
TEXT = (247, 247, 247)
MUTED = (168, 174, 180)
ACCENT = (58, 124, 165)

EMOTE_TO_ATLAS_NAME = {
    "dots": "emote_dots3.png",
    "happy": "emote_faceHappy.png",
    "heart": "emote_heart.png",
    "idea": "emote_idea.png",
    "question": "emote_question.png",
    "sleep": "emote_sleep.png",
}

LOCATION_TILE_INDEX = {
    "home": 48,
    "food": 92,
    "social": 121,
    "knowledge": 184,
    "work": 148,
    "quiet": 213,
}


@dataclass
class Camera:
    x: float = 760
    y: float = 500
    zoom: float = 0.72

    def world_to_screen(self, x: float, y: float) -> tuple[int, int]:
        return (
            int((x - self.x) * self.zoom + (SCREEN_WIDTH - PANEL_WIDTH) / 2),
            int((y - self.y) * self.zoom + SCREEN_HEIGHT / 2),
        )

    def screen_to_world(self, x: float, y: float) -> tuple[float, float]:
        return (
            (x - (SCREEN_WIDTH - PANEL_WIDTH) / 2) / self.zoom + self.x,
            (y - SCREEN_HEIGHT / 2) / self.zoom + self.y,
        )

    def clamp(self) -> None:
        viewport_width = (SCREEN_WIDTH - PANEL_WIDTH) / self.zoom
        viewport_height = SCREEN_HEIGHT / self.zoom
        margin_x = viewport_width * 0.35
        margin_y = viewport_height * 0.35
        self.x = max(-margin_x, min(WORLD_WIDTH + margin_x, self.x))
        self.y = max(-margin_y, min(WORLD_HEIGHT + margin_y, self.y))


@dataclass
class SpriteAssets:
    tile_size: int
    margin: int
    characters: pygame.Surface | None = None
    tiles: pygame.Surface | None = None
    emotes: pygame.Surface | None = None
    emote_rects: dict[str, pygame.Rect] | None = None
    scaled_cache: dict[tuple[str, int, int], pygame.Surface] | None = None


@dataclass(frozen=True)
class TileStamp:
    dx: int
    dy: int
    index: int
    role: str


@dataclass(frozen=True)
class LocationFootprint:
    tiles: tuple[TileStamp, ...]
    label_offset_y: int


TERRAIN_TILE_INDEXES = {
    "grass": (5, 62, 5, 62),
    "field": (7, 7, 64, 64),
    "water": (0, 1, 57, 58, 114, 115, 171, 172),
    "stone": (120, 177, 704, 705),
    "path": (7, 64, 7, 64),
}


def _room_footprint(
    *,
    floor: int,
    wall: int,
    prop: int,
    door: int,
    width: int = 4,
    height: int = 3,
    extra_props: tuple[tuple[int, int, int], ...] = (),
) -> LocationFootprint:
    tiles: list[TileStamp] = []
    left = -(width // 2)
    top = -(height // 2)
    for row in range(height):
        for column in range(width):
            dx = left + column
            dy = top + row
            edge = row in (0, height - 1) or column in (0, width - 1)
            role = "wall" if edge else "floor"
            tiles.append(TileStamp(dx, dy, wall if edge else floor, role))
    tiles.append(TileStamp(0, top + height - 1, door, "prop"))
    tiles.append(TileStamp(left + width - 2, top + 1, prop, "prop"))
    for dx, dy, index in extra_props:
        tiles.append(TileStamp(dx, dy, index, "prop"))
    return LocationFootprint(tuple(tiles), label_offset_y=(height + 1) * 18)


LOCATION_FOOTPRINTS = {
    "home": _room_footprint(floor=694, wall=751, prop=79, door=80),
    "food": _room_footprint(floor=779, wall=723, prop=317, door=80, extra_props=((-1, 0, 376),)),
    "social": LocationFootprint(
        (
            TileStamp(-2, -1, 570, "floor"),
            TileStamp(-1, -1, 571, "floor"),
            TileStamp(0, -1, 572, "floor"),
            TileStamp(1, -1, 627, "floor"),
            TileStamp(-2, 0, 628, "floor"),
            TileStamp(-1, 0, 527, "prop"),
            TileStamp(0, 0, 528, "prop"),
            TileStamp(1, 0, 629, "floor"),
            TileStamp(-2, 1, 798, "floor"),
            TileStamp(-1, 1, 799, "floor"),
            TileStamp(0, 1, 480, "prop"),
            TileStamp(1, 1, 570, "floor"),
        ),
        label_offset_y=72,
    ),
    "knowledge": _room_footprint(floor=753, wall=695, prop=20, door=80, extra_props=((-1, 0, 77),)),
    "work": _room_footprint(floor=779, wall=723, prop=148, door=80, extra_props=((-1, 0, 149),)),
    "quiet": LocationFootprint(
        (
            TileStamp(-2, -1, 570, "floor"),
            TileStamp(-1, -1, 571, "floor"),
            TileStamp(0, -1, 572, "floor"),
            TileStamp(1, -1, 627, "floor"),
            TileStamp(-2, 0, 628, "floor"),
            TileStamp(-1, 0, 595, "prop"),
            TileStamp(0, 0, 596, "prop"),
            TileStamp(1, 0, 629, "floor"),
            TileStamp(-2, 1, 798, "floor"),
            TileStamp(-1, 1, 799, "floor"),
            TileStamp(0, 1, 536, "prop"),
            TileStamp(1, 1, 570, "floor"),
        ),
        label_offset_y=72,
    ),
}

VISUAL_TILE_WORLD_SIZE = 54
PATH_TILE_WORLD_SIZE = 42


def load_sprite_assets() -> SpriteAssets:
    manifest = load_kenney_manifest()
    assets = SpriteAssets(tile_size=manifest.tile_size, margin=manifest.margin, emote_rects={}, scaled_cache={})
    try:
        assets.characters = pygame.image.load(str(manifest.characters_path)).convert_alpha()
        assets.tiles = pygame.image.load(str(manifest.tiles_path)).convert_alpha()
        assets.emotes = pygame.image.load(str(manifest.emotes_path)).convert_alpha()
        assets.emote_rects = _load_emote_rects(str(manifest.emotes_xml_path))
    except (OSError, pygame.error, ET.ParseError):
        return SpriteAssets(tile_size=manifest.tile_size, margin=manifest.margin, emote_rects={})
    return assets


def _load_emote_rects(path: str) -> dict[str, pygame.Rect]:
    tree = ET.parse(path)
    rects: dict[str, pygame.Rect] = {}
    for node in tree.getroot().iter("SubTexture"):
        name = node.attrib["name"]
        rects[name] = pygame.Rect(
            int(node.attrib["x"]),
            int(node.attrib["y"]),
            int(node.attrib["width"]),
            int(node.attrib["height"]),
        )
    return rects


class App:
    def __init__(self, sim: Simulation, *, smoke_test: bool = False) -> None:
        self.sim = sim
        self.smoke_test = smoke_test
        pygame.init()
        pygame.display.set_caption("Local Agent Town")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.assets = load_sprite_assets()
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Segoe UI", 18)
        self.small_font = pygame.font.SysFont("Segoe UI", 15)
        self.title_font = pygame.font.SysFont("Segoe UI Semibold", 24)
        self.camera = Camera()
        self.running = True
        self.paused = False
        self.speed = 1.0
        self.selected_id = next(iter(sim.agents))
        self.input_active = False
        self.input_text = ""
        llm_client = LocalLLMClient(model=None) if smoke_test else LocalLLMClient.from_env()
        self.llm_scheduler = LLMDecisionScheduler(llm_client)

    def run(self) -> None:
        frames = 0
        try:
            while self.running:
                dt = self.clock.tick(60) / 1000.0
                self._handle_events()
                self._handle_camera_keys(dt)
                if not self.paused:
                    self.sim.step(min(dt * self.speed, 0.25))
                self.llm_scheduler.update(self.sim)
                self._draw()
                frames += 1
                if self.smoke_test and frames >= 8:
                    self.running = False
        finally:
            self.llm_scheduler.shutdown(wait=False)
            pygame.quit()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self._handle_mouse(event)
            elif event.type == pygame.KEYDOWN:
                self._handle_key(event)

    def _handle_mouse(self, event: pygame.event.Event) -> None:
        if event.button == 4:
            self._zoom_at(event.pos, 1.12)
        elif event.button == 5:
            self._zoom_at(event.pos, 1 / 1.12)
        elif event.button == 1 and event.pos[0] < SCREEN_WIDTH - PANEL_WIDTH:
            clicked = self._agent_at_screen(event.pos)
            if clicked is not None:
                self.selected_id = clicked.id

    def _handle_key(self, event: pygame.event.Event) -> None:
        if self.input_active:
            if event.key == pygame.K_ESCAPE:
                self.input_active = False
                self.input_text = ""
            elif event.key == pygame.K_RETURN:
                if self.input_text.strip():
                    self.sim.suggest(self.selected_id, self.input_text)
                self.input_text = ""
                self.input_active = False
            elif event.key == pygame.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
            elif event.unicode and len(self.input_text) < 160:
                self.input_text += event.unicode
            return

        if event.key == pygame.K_ESCAPE:
            self.running = False
        elif event.key == pygame.K_p:
            self.paused = not self.paused
        elif event.key == pygame.K_TAB:
            self._select_next_agent()
        elif event.key == pygame.K_SLASH:
            self.input_active = True
            self.input_text = ""
        elif event.key in (pygame.K_EQUALS, pygame.K_PLUS):
            self.speed = min(8.0, self.speed * 1.35)
        elif event.key == pygame.K_MINUS:
            self.speed = max(0.25, self.speed / 1.35)

    def _handle_camera_keys(self, dt: float) -> None:
        keys = pygame.key.get_pressed()
        pan = 620 * dt / self.camera.zoom
        if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
            pan *= 1.8
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            self.camera.x -= pan
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            self.camera.x += pan
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            self.camera.y -= pan
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            self.camera.y += pan
        self.camera.clamp()

    def _zoom_at(self, pos: tuple[int, int], factor: float) -> None:
        before = self.camera.screen_to_world(*pos)
        self.camera.zoom = max(MIN_ZOOM, min(MAX_ZOOM, self.camera.zoom * factor))
        after = self.camera.screen_to_world(*pos)
        self.camera.x += before[0] - after[0]
        self.camera.y += before[1] - after[1]
        self.camera.clamp()

    def _agent_at_screen(self, pos: tuple[int, int]) -> Agent | None:
        for agent in self.sim.agents.values():
            sx, sy = self.camera.world_to_screen(agent.x, agent.y)
            if (sx - pos[0]) ** 2 + (sy - pos[1]) ** 2 <= 18**2:
                return agent
        return None

    def _select_next_agent(self) -> None:
        ids = list(self.sim.agents)
        index = ids.index(self.selected_id)
        self.selected_id = ids[(index + 1) % len(ids)]

    def _draw(self) -> None:
        self.screen.fill(BACKGROUND)
        self._draw_world()
        self._draw_locations()
        self._draw_agents()
        self._draw_panel()
        pygame.display.flip()

    def _draw_world(self) -> None:
        top_left = self.camera.world_to_screen(0, 0)
        size = (int(WORLD_WIDTH * self.camera.zoom), int(WORLD_HEIGHT * self.camera.zoom))
        pygame.draw.rect(self.screen, WORLD_BG, (*top_left, *size), border_radius=4)
        pygame.draw.rect(self.screen, (83, 97, 88), (*top_left, *size), width=2, border_radius=4)
        self._draw_terrain_tiles()

        grid_step = 216
        for x in range(0, WORLD_WIDTH + 1, grid_step):
            start = self.camera.world_to_screen(x, 0)
            end = self.camera.world_to_screen(x, WORLD_HEIGHT)
            pygame.draw.line(self.screen, (45, 52, 47), start, end, 1)
        for y in range(0, WORLD_HEIGHT + 1, grid_step):
            start = self.camera.world_to_screen(0, y)
            end = self.camera.world_to_screen(WORLD_WIDTH, y)
            pygame.draw.line(self.screen, (45, 52, 47), start, end, 1)

        self._draw_paths()

    def _draw_terrain_tiles(self) -> None:
        if self.assets.tiles is None:
            return

        tile_size = max(10, int(VISUAL_TILE_WORLD_SIZE * self.camera.zoom) + 1)
        visible_left, visible_top = self.camera.screen_to_world(0, 0)
        visible_right, visible_bottom = self.camera.screen_to_world(SCREEN_WIDTH - PANEL_WIDTH, SCREEN_HEIGHT)
        start_x = max(0, floor(visible_left / VISUAL_TILE_WORLD_SIZE) - 1)
        end_x = min(WORLD_WIDTH // VISUAL_TILE_WORLD_SIZE + 1, floor(visible_right / VISUAL_TILE_WORLD_SIZE) + 2)
        start_y = max(0, floor(visible_top / VISUAL_TILE_WORLD_SIZE) - 1)
        end_y = min(WORLD_HEIGHT // VISUAL_TILE_WORLD_SIZE + 1, floor(visible_bottom / VISUAL_TILE_WORLD_SIZE) + 2)

        for gy in range(start_y, end_y):
            for gx in range(start_x, end_x):
                wx = gx * VISUAL_TILE_WORLD_SIZE
                wy = gy * VISUAL_TILE_WORLD_SIZE
                palette = self._terrain_palette_for(wx, wy)
                index = palette[(gx * 3 + gy * 5) % len(palette)]
                self._draw_tile_at(index, wx, wy, tile_size)

    def _terrain_palette_for(self, wx: int, wy: int) -> tuple[int, ...]:
        if wx < 230 and wy < 680:
            return TERRAIN_TILE_INDEXES["water"]
        if 560 <= wx <= 940 and 980 <= wy <= 1420:
            return TERRAIN_TILE_INDEXES["field"]
        if 1010 <= wx <= 1400 and 620 <= wy <= 940:
            return TERRAIN_TILE_INDEXES["stone"]
        return TERRAIN_TILE_INDEXES["grass"]

    def _draw_paths(self) -> None:
        paths = [
            ("Town Square", "North Apartments"),
            ("Town Square", "South Row Homes"),
            ("Town Square", "Greenhouse Cafe"),
            ("Town Square", "Archive Library"),
            ("Town Square", "Maker Hall"),
            ("Town Square", "Riverside Park"),
            ("Riverside Park", "Clinic Garden"),
        ]
        for start_name, end_name in paths:
            start = self.sim.locations[start_name]
            end = self.sim.locations[end_name]
            pygame.draw.line(
                self.screen,
                (64, 54, 42),
                self.camera.world_to_screen(start.x, start.y),
                self.camera.world_to_screen(end.x, end.y),
                max(3, int(18 * self.camera.zoom)),
            )
            pygame.draw.line(
                self.screen,
                (124, 104, 72),
                self.camera.world_to_screen(start.x, start.y),
                self.camera.world_to_screen(end.x, end.y),
                max(2, int(10 * self.camera.zoom)),
            )
            self._draw_path_tiles(start.x, start.y, end.x, end.y)

    def _draw_path_tiles(self, start_x: float, start_y: float, end_x: float, end_y: float) -> None:
        steps = max(1, int(max(abs(end_x - start_x), abs(end_y - start_y)) / PATH_TILE_WORLD_SIZE))
        tile_size = max(12, int(PATH_TILE_WORLD_SIZE * self.camera.zoom))
        palette = TERRAIN_TILE_INDEXES["path"]
        for step in range(steps + 1):
            t = step / steps
            wx = start_x + (end_x - start_x) * t - PATH_TILE_WORLD_SIZE / 2
            wy = start_y + (end_y - start_y) * t - PATH_TILE_WORLD_SIZE / 2
            index = palette[step % len(palette)]
            self._draw_tile_at(index, int(wx), int(wy), tile_size)

    def _draw_locations(self) -> None:
        for location in self.sim.locations.values():
            sx, sy = self.camera.world_to_screen(location.x, location.y)
            footprint = LOCATION_FOOTPRINTS.get(location.kind)
            if footprint is None:
                self._draw_tile_sprite(
                    self.assets.tiles,
                    "tiles",
                    LOCATION_TILE_INDEX.get(location.kind, 4),
                    sx,
                    sy,
                    max(22, int(38 * self.camera.zoom)),
                )
                self._draw_text(location.name, sx - 34, sy + 40, self.small_font, MUTED)
                continue

            tile_size = max(18, int(44 * self.camera.zoom))
            shadow_tiles = footprint.tiles
            if shadow_tiles:
                min_dx = min(tile.dx for tile in shadow_tiles)
                max_dx = max(tile.dx for tile in shadow_tiles)
                min_dy = min(tile.dy for tile in shadow_tiles)
                max_dy = max(tile.dy for tile in shadow_tiles)
                shadow_rect = pygame.Rect(
                    sx + min_dx * tile_size - 4,
                    sy + min_dy * tile_size + 6,
                    (max_dx - min_dx + 1) * tile_size + 8,
                    (max_dy - min_dy + 1) * tile_size + 8,
                )
                pygame.draw.rect(self.screen, (11, 15, 13), shadow_rect, border_radius=3)

            for tile in sorted(footprint.tiles, key=lambda stamp: (stamp.role == "prop", stamp.dy, stamp.dx)):
                self._draw_tile_sprite(
                    self.assets.tiles,
                    "tiles",
                    tile.index,
                    sx + tile.dx * tile_size,
                    sy + tile.dy * tile_size,
                    tile_size,
                )
            label_y = sy + int(footprint.label_offset_y * self.camera.zoom)
            self._draw_label(location.name, sx, label_y)

    def _draw_agents(self) -> None:
        for agent in self.sim.agents.values():
            sx, sy = self.camera.world_to_screen(agent.x, agent.y)
            selected = agent.id == self.selected_id
            if selected:
                destination = self.sim.locations[agent.destination]
                pygame.draw.line(
                    self.screen,
                    ACCENT,
                    (sx, sy),
                    self.camera.world_to_screen(destination.x, destination.y),
                    2,
                )
                pygame.draw.rect(self.screen, ACCENT, (sx - 18, sy - 20, 36, 36), width=2, border_radius=3)
            pygame.draw.ellipse(self.screen, (8, 11, 10), (sx - 13, sy + 8, 26, 8))
            drew_sprite = self._draw_tile_sprite(
                self.assets.characters,
                "characters",
                agent.sprite_index,
                sx,
                sy,
                max(24, int(30 * self.camera.zoom)),
            )
            if not drew_sprite:
                pygame.draw.circle(self.screen, agent.color, (sx, sy), 12)
                pygame.draw.circle(self.screen, (13, 18, 22), (sx, sy), 12, width=2)
            self._draw_text(agent.name, sx - 16, sy - 34, self.small_font, TEXT)
            self._draw_agent_emote(agent, sx, sy)

    def _draw_panel(self) -> None:
        panel_x = SCREEN_WIDTH - PANEL_WIDTH
        pygame.draw.rect(self.screen, PANEL_BG, (panel_x, 0, PANEL_WIDTH, SCREEN_HEIGHT))
        pygame.draw.line(self.screen, (66, 74, 83), (panel_x, 0), (panel_x, SCREEN_HEIGHT), 2)

        agent = self.sim.agents[self.selected_id]
        footer_y = SCREEN_HEIGHT - 106
        y = 24
        y = self._panel_text(agent.name, y, self.title_font, TEXT)
        y = self._panel_text(f"{self.sim.agent_location_name(agent)}", y, self.font, ACCENT)
        y += 10
        y = self._panel_text(f"Goal: {agent.goal}", y, self.small_font, TEXT, wrap=True)
        y = self._panel_text(f"Activity: {agent.activity}", y, self.small_font, TEXT, wrap=True)
        if agent.last_speech:
            y = self._panel_text(f"Said: {agent.last_speech}", y, self.small_font, MUTED, wrap=True)
        y += 12
        y = self._bar("Energy", agent.energy, y)
        y = self._bar("Hunger", agent.hunger, y)
        y = self._bar("Social need", agent.social, y)
        y = self._bar("Curiosity", agent.curiosity, y)
        y += 14
        y = self._panel_text("Traits", y, self.font, TEXT)
        y = self._panel_text(", ".join(agent.traits) or "none", y, self.small_font, MUTED, wrap=True)
        y += 12
        y = self._panel_text("Local Model", y, self.font, TEXT)
        y = self._panel_text(self._llm_status_text(), y, self.small_font, MUTED, wrap=True)
        y += 12
        y = self._panel_text("Recent Memory", y, self.font, TEXT)
        for memory in reversed(agent.memories[-3:]):
            y = self._panel_text(f"- {memory.text}", y, self.small_font, MUTED, wrap=True)
        if not agent.memories:
            y = self._panel_text("No memories yet.", y, self.small_font, MUTED)
        y += 12
        if y < footer_y - 120:
            y = self._panel_text("Town Feed", y, self.font, TEXT)
            for event in reversed(self.sim.events[-4:]):
                y = self._panel_text(f"- {event.text}", y, self.small_font, MUTED, wrap=True)
        if y < footer_y - 72:
            y += 12
            y = self._panel_text("Pending Suggestions", y, self.font, TEXT)
            if agent.suggestions:
                for suggestion in agent.suggestions[-2:]:
                    y = self._panel_text(f"- {suggestion}", y, self.small_font, MUTED, wrap=True)
            else:
                y = self._panel_text("None.", y, self.small_font, MUTED)

        pygame.draw.rect(self.screen, (36, 41, 48), (panel_x + 18, footer_y, PANEL_WIDTH - 36, 72), border_radius=6)
        prompt = self.input_text if self.input_active else "Press / to suggest an idea"
        color = TEXT if self.input_active else MUTED
        self._draw_text(prompt, panel_x + 30, footer_y + 16, self.small_font, color, max_width=PANEL_WIDTH - 60)
        status = "Paused" if self.paused else f"{self.speed:.2f}x"
        self._draw_text(f"P pause  Tab select  Wheel zoom  Speed {status}", panel_x + 30, footer_y + 46, self.small_font, MUTED)

    def _panel_text(
        self,
        text: str,
        y: int,
        font: pygame.font.Font,
        color: tuple[int, int, int],
        *,
        wrap: bool = False,
    ) -> int:
        x = SCREEN_WIDTH - PANEL_WIDTH + 24
        if wrap:
            lines = self._wrap_text(text, font, PANEL_WIDTH - 48)
        else:
            lines = [text]
        for line in lines:
            self._draw_text(line, x, y, font, color)
            y += font.get_height() + 4
        return y

    def _bar(self, label: str, value: float, y: int) -> int:
        x = SCREEN_WIDTH - PANEL_WIDTH + 24
        width = PANEL_WIDTH - 48
        self._draw_text(label, x, y, self.small_font, MUTED)
        y += 22
        pygame.draw.rect(self.screen, (50, 58, 67), (x, y, width, 9), border_radius=4)
        pygame.draw.rect(self.screen, ACCENT, (x, y, int(width * value), 9), border_radius=4)
        return y + 20

    def _draw_tile_sprite(
        self,
        sheet: pygame.Surface | None,
        sheet_key: str,
        index: int,
        center_x: int,
        center_y: int,
        size: int,
    ) -> bool:
        sprite = self._scaled_sprite(sheet, sheet_key, index, size)
        if sprite is None:
            return False
        self.screen.blit(sprite, (center_x - size // 2, center_y - size // 2))
        return True

    def _draw_tile_at(self, index: int, world_x: int, world_y: int, size: int) -> bool:
        sprite = self._scaled_sprite(self.assets.tiles, "tiles", index, size)
        if sprite is None:
            return False
        sx, sy = self.camera.world_to_screen(world_x, world_y)
        self.screen.blit(sprite, (sx, sy))
        return True

    def _scaled_sprite(
        self,
        sheet: pygame.Surface | None,
        sheet_key: str,
        index: int,
        size: int,
    ) -> pygame.Surface | None:
        if sheet is None:
            return None
        cache = self.assets.scaled_cache
        cache_key = (sheet_key, index, size)
        if cache is not None and cache_key in cache:
            return cache[cache_key]
        step = self.assets.tile_size + self.assets.margin
        columns = max(1, (sheet.get_width() + self.assets.margin) // step)
        source_x = (index % columns) * step
        source_y = (index // columns) * step
        rect = pygame.Rect(source_x, source_y, self.assets.tile_size, self.assets.tile_size)
        if rect.right > sheet.get_width() or rect.bottom > sheet.get_height():
            return None
        sprite = sheet.subsurface(rect)
        scaled = pygame.transform.scale(sprite, (size, size))
        if cache is not None:
            cache[cache_key] = scaled
        return scaled

    def _draw_agent_emote(self, agent: Agent, sx: int, sy: int) -> None:
        if not agent.emote or self.assets.emotes is None or self.assets.emote_rects is None:
            return
        atlas_name = EMOTE_TO_ATLAS_NAME.get(agent.emote)
        if not atlas_name:
            return
        rect = self.assets.emote_rects.get(atlas_name)
        if rect is None:
            return
        size = max(18, int(22 * self.camera.zoom))
        sprite = self.assets.emotes.subsurface(rect)
        scaled = pygame.transform.scale(sprite, (size, size))
        self.screen.blit(scaled, (sx + 10, sy - size - 12))

    def _draw_label(self, text: str, center_x: int, y: int) -> None:
        surface = self.small_font.render(text, True, TEXT)
        padding_x = 7
        padding_y = 3
        rect = pygame.Rect(
            center_x - surface.get_width() // 2 - padding_x,
            y,
            surface.get_width() + padding_x * 2,
            surface.get_height() + padding_y * 2,
        )
        pygame.draw.rect(self.screen, (18, 22, 20), rect, border_radius=3)
        pygame.draw.rect(self.screen, (73, 82, 72), rect, width=1, border_radius=3)
        self.screen.blit(surface, (rect.x + padding_x, rect.y + padding_y))

    def _llm_status_text(self) -> str:
        status = self.llm_scheduler.status
        if not status.enabled:
            return "Disabled. Set AGENT_TOWN_LLM_MODEL to use LM Studio or Ollama."
        if status.state == "thinking":
            agent_name = self.sim.agents.get(status.in_flight_agent_id).name if status.in_flight_agent_id in self.sim.agents else "agent"
            return f"Thinking for {agent_name} with {status.model}."
        if status.state == "offline":
            return f"Offline: {status.last_error}"
        if status.state == "invalid":
            return f"Invalid model reply: {status.last_error}"
        if status.last_latency:
            return f"Idle. Last thought {status.last_latency:.2f}s for {status.last_agent_id}."
        return f"Idle. Model: {status.model}."

    def _draw_text(
        self,
        text: str,
        x: int,
        y: int,
        font: pygame.font.Font,
        color: tuple[int, int, int],
        *,
        max_width: int | None = None,
    ) -> None:
        lines = self._wrap_text(text, font, max_width) if max_width else [text]
        for index, line in enumerate(lines):
            surface = font.render(line, True, color)
            self.screen.blit(surface, (x, y + index * (font.get_height() + 4)))

    def _wrap_text(self, text: str, font: pygame.font.Font, max_width: int | None) -> list[str]:
        if max_width is None:
            return [text]

        words = text.split()
        if not words:
            return [""]

        lines: list[str] = []
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if font.size(candidate)[0] <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines

    @staticmethod
    def _location_color(location: Location) -> tuple[int, int, int]:
        return {
            "home": (91, 119, 153),
            "food": (139, 122, 72),
            "social": (92, 129, 105),
            "knowledge": (95, 92, 143),
            "work": (129, 95, 83),
            "quiet": (80, 115, 116),
        }.get(location.kind, (95, 105, 99))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Local Agent Town desktop simulation.")
    parser.add_argument("--smoke-test", action="store_true", help="Open briefly, draw a few frames, then exit.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.smoke_test:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    app = App(create_default_simulation(), smoke_test=args.smoke_test)
    app.run()


if __name__ == "__main__":
    main()
