import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from agent_town import civilization
from agent_town.civilization_view import (
    BUILDING_SPRITE,
    INSPECTOR_WIDTH,
    PAWN_ROSTER_HEIGHT,
    Camera,
    CivilizationViewer,
    _need_bar_color,
    _mood_color,
    _pawn_status_label,
    _top_skills,
    find_pawn_at_screen,
    governor_status_line,
    load_civilization_assets,
    parse_args,
    render_civilization,
)
from agent_town.pawns import STATE_SLACKING
from agent_town.governor import CivilizationDecisionScheduler, FallbackGovernor
from agent_town.llm import LocalLLMClient


class CivilizationAssetTests(unittest.TestCase):
    def setUp(self):
        pygame.display.init()
        pygame.font.init()
        pygame.display.set_mode((64, 64))

    def test_load_civilization_assets_loads_tiles_and_buildings(self):
        assets = load_civilization_assets()

        self.assertEqual(assets.tile_size, 25)
        for name in ("grass", "dirt", "pavement", "tree", "house", "house2", "house3"):
            self.assertIn(name, assets.surfaces)
        for name in ("house", "house2", "house3"):
            self.assertIn(name, assets.buildings_scaled)
            self.assertEqual(assets.buildings_scaled[name].get_width(), 2 * assets.tile_size)
        # Pawn sprites (CC0 Tiny Characters Set) are discovered by glob and
        # pre-scaled to a uniform render height with at least one per colonist.
        self.assertGreaterEqual(len(assets.pawns_scaled), 12)
        for sprite in assets.pawns_scaled.values():
            self.assertEqual(sprite.get_height(), 26)

    def test_every_build1_building_kind_has_a_sprite(self):
        state = civilization.create_default_civilization()
        for building in state.buildings.values():
            with self.subTest(kind=building.kind):
                self.assertIn(building.kind, BUILDING_SPRITE)

    def test_render_civilization_draws_a_frame_without_crashing(self):
        assets = load_civilization_assets()
        font = pygame.font.Font(None, 16)
        state = civilization.create_default_civilization()
        surface = pygame.Surface((state.grid.width * 25 + 24, state.grid.height * 25 + 120))

        render_civilization(surface, state, assets, font, (12, 12))


class MoodColorTests(unittest.TestCase):
    def test_mood_color_runs_red_to_green(self):
        low = _mood_color(0.0)
        high = _mood_color(1.0)
        self.assertGreater(low[0], low[1])  # red-dominant when sad
        self.assertGreater(high[1], high[0])  # green-dominant when happy

    def test_need_bar_color_flags_low_needs(self):
        low = _need_bar_color(0.19)
        full = _need_bar_color(0.95)

        self.assertGreater(low[0], low[1])
        self.assertGreater(full[1], full[0])


class PawnInspectorModelTests(unittest.TestCase):
    def test_top_skills_sorts_by_score_then_name(self):
        state = civilization.create_default_civilization()
        pawn = state.pawns["pawn00"]
        pawn.skills = {"mining": 12, "farming": 16, "baking": 16}

        self.assertEqual(_top_skills(pawn), [("baking", 16), ("farming", 16), ("mining", 12)])

    def test_pawn_status_label_prioritizes_break_states(self):
        state = civilization.create_default_civilization()
        pawn = state.pawns["pawn00"]
        pawn.state = STATE_SLACKING

        self.assertEqual(_pawn_status_label(pawn), "Stressed")

    def test_viewer_reserves_roster_and_wider_inspector(self):
        self.assertGreaterEqual(PAWN_ROSTER_HEIGHT, 58)
        self.assertGreaterEqual(INSPECTOR_WIDTH, 280)


class GovernorStatusLineTests(unittest.TestCase):
    def test_plain_governor_reads_as_fallback_autopilot(self):
        text, _color = governor_status_line(FallbackGovernor())
        self.assertIn("fallback", text.lower())

    def test_disabled_scheduler_prompts_to_connect(self):
        sched = CivilizationDecisionScheduler(LocalLLMClient(model=None))
        text, _color = governor_status_line(sched)
        self.assertIn("press L", text)
        sched.shutdown(wait=True)


class CameraTests(unittest.TestCase):
    def test_screen_to_tile_accounts_for_pan_and_zoom(self):
        camera = Camera(offset_x=25.0, offset_y=50.0, zoom=2.0)

        self.assertEqual(camera.screen_to_tile((62, 112), (12, 12), 25), (2, 4))

    def test_camera_clamps_to_world_bounds(self):
        camera = Camera(offset_x=999.0, offset_y=-50.0, zoom=2.0)

        camera.clamp_to_world(world_size=(600, 400), viewport_size=(300, 200))

        self.assertEqual(camera.offset_x, 450.0)
        self.assertEqual(camera.offset_y, 0.0)


class PawnSelectionTests(unittest.TestCase):
    def test_find_pawn_at_screen_uses_camera_transform(self):
        state = civilization.create_default_civilization()
        camera = Camera(offset_x=25.0, offset_y=0.0, zoom=2.0)
        pawn = state.pawns["pawn00"]

        center = camera.tile_center_to_screen(pawn.x, pawn.y, (12, 12), 25)

        self.assertEqual(find_pawn_at_screen(state, center, (12, 12), 25, camera), "pawn00")


class _RecordingGovernor:
    """A governor that just counts decide() calls for wiring tests."""

    def __init__(self):
        self.calls = 0

    def decide(self, context):
        self.calls += 1
        return []


class CivilizationViewerSmokeTests(unittest.TestCase):
    def test_viewer_runs_a_few_frames_and_exits(self):
        viewer = CivilizationViewer(smoke_test=True)
        viewer.run()
        self.assertFalse(viewer.running)
        # The engine advanced the civilization while rendering.
        self.assertGreater(viewer.state.time_of_day + viewer.state.day * 24, 0)

    def test_smoke_viewer_defaults_to_deterministic_fallback(self):
        viewer = CivilizationViewer(smoke_test=True)
        self.assertIsInstance(viewer.governor, FallbackGovernor)

    def test_viewer_steps_through_injected_governor(self):
        gov = _RecordingGovernor()
        viewer = CivilizationViewer(smoke_test=True, governor=gov)
        viewer.run()
        self.assertGreater(gov.calls, 0)

    def test_parse_args_smoke_flag(self):
        self.assertFalse(parse_args([]).smoke_test)
        self.assertTrue(parse_args(["--smoke-test"]).smoke_test)


if __name__ == "__main__":
    unittest.main()
