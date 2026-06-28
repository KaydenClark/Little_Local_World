import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from agent_town import colony
from agent_town.colony_view import (
    BUILDING_SPRITE,
    ColonyViewer,
    _mood_color,
    governor_status_line,
    load_colony_assets,
    parse_args,
    render_colony,
)
from agent_town.governor import ColonyDecisionScheduler, FallbackGovernor
from agent_town.llm import LocalLLMClient


class ColonyAssetTests(unittest.TestCase):
    def setUp(self):
        pygame.display.init()
        pygame.font.init()
        pygame.display.set_mode((64, 64))

    def test_load_colony_assets_loads_tiles_and_buildings(self):
        assets = load_colony_assets()

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
        state = colony.create_default_colony()
        for building in state.buildings.values():
            with self.subTest(kind=building.kind):
                self.assertIn(building.kind, BUILDING_SPRITE)

    def test_render_colony_draws_a_frame_without_crashing(self):
        assets = load_colony_assets()
        font = pygame.font.Font(None, 16)
        state = colony.create_default_colony()
        surface = pygame.Surface((state.grid.width * 25 + 24, state.grid.height * 25 + 120))

        render_colony(surface, state, assets, font, (12, 12))


class MoodColorTests(unittest.TestCase):
    def test_mood_color_runs_red_to_green(self):
        low = _mood_color(0.0)
        high = _mood_color(1.0)
        self.assertGreater(low[0], low[1])  # red-dominant when sad
        self.assertGreater(high[1], high[0])  # green-dominant when happy


class GovernorStatusLineTests(unittest.TestCase):
    def test_plain_governor_reads_as_fallback_autopilot(self):
        text, _color = governor_status_line(FallbackGovernor())
        self.assertIn("fallback", text.lower())

    def test_disabled_scheduler_prompts_to_connect(self):
        sched = ColonyDecisionScheduler(LocalLLMClient(model=None))
        text, _color = governor_status_line(sched)
        self.assertIn("press L", text)
        sched.shutdown(wait=True)


class _RecordingGovernor:
    """A governor that just counts decide() calls for wiring tests."""

    def __init__(self):
        self.calls = 0

    def decide(self, context):
        self.calls += 1
        return []


class ColonyViewerSmokeTests(unittest.TestCase):
    def test_viewer_runs_a_few_frames_and_exits(self):
        viewer = ColonyViewer(smoke_test=True)
        viewer.run()
        self.assertFalse(viewer.running)
        # The engine advanced the colony while rendering.
        self.assertGreater(viewer.state.time_of_day + viewer.state.day * 24, 0)

    def test_smoke_viewer_defaults_to_deterministic_fallback(self):
        viewer = ColonyViewer(smoke_test=True)
        self.assertIsInstance(viewer.governor, FallbackGovernor)

    def test_viewer_steps_through_injected_governor(self):
        gov = _RecordingGovernor()
        viewer = ColonyViewer(smoke_test=True, governor=gov)
        viewer.run()
        self.assertGreater(gov.calls, 0)

    def test_parse_args_smoke_flag(self):
        self.assertFalse(parse_args([]).smoke_test)
        self.assertTrue(parse_args(["--smoke-test"]).smoke_test)


if __name__ == "__main__":
    unittest.main()
