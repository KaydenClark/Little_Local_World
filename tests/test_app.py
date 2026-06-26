import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from agent_town.app import EMOTE_TO_ATLAS_NAME, App, Camera, load_sprite_assets, parse_args
from agent_town.core import create_default_simulation


class CameraTests(unittest.TestCase):
    def test_world_to_screen_and_back_round_trips(self):
        camera = Camera(x=400, y=250, zoom=1.3)

        screen = camera.world_to_screen(123, 456)
        world = camera.screen_to_world(*screen)

        self.assertAlmostEqual(world[0], 123, delta=1)
        self.assertAlmostEqual(world[1], 456, delta=1)

    def test_clamp_keeps_camera_within_world_bounds_margin(self):
        camera = Camera(x=999999, y=-999999, zoom=1.0)

        camera.clamp()

        self.assertLess(camera.x, 999999)
        self.assertGreater(camera.y, -999999)


class SpriteAssetLoadingTests(unittest.TestCase):
    def test_load_sprite_assets_loads_all_three_sheets(self):
        assets = load_sprite_assets()

        self.assertIsNotNone(assets.characters)
        self.assertIsNotNone(assets.tiles)
        self.assertIsNotNone(assets.emotes)
        self.assertTrue(assets.emote_rects)

    def test_every_emote_used_by_the_app_exists_in_the_loaded_atlas(self):
        assets = load_sprite_assets()

        for emote_key, atlas_name in EMOTE_TO_ATLAS_NAME.items():
            with self.subTest(emote=emote_key):
                self.assertIn(atlas_name, assets.emote_rects)


class ParseArgsTests(unittest.TestCase):
    def test_smoke_test_flag_defaults_to_false(self):
        args = parse_args([])
        self.assertFalse(args.smoke_test)

    def test_smoke_test_flag_can_be_enabled(self):
        args = parse_args(["--smoke-test"])
        self.assertTrue(args.smoke_test)


class AppSmokeTests(unittest.TestCase):
    def test_app_draws_all_agents_and_buildings_for_a_few_frames_without_crashing(self):
        app = App(create_default_simulation(), smoke_test=True)
        try:
            app.run()
        finally:
            app.llm_scheduler.shutdown(wait=True)

        self.assertFalse(app.running)

    def test_selecting_next_agent_cycles_through_every_agent(self):
        app = App(create_default_simulation(), smoke_test=True)
        try:
            seen = {app.selected_id}
            for _ in range(len(app.sim.agents)):
                app._select_next_agent()
                seen.add(app.selected_id)
            self.assertEqual(seen, set(app.sim.agents))
        finally:
            app.llm_scheduler.shutdown(wait=True)


if __name__ == "__main__":
    unittest.main()
