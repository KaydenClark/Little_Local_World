import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from agent_town.app import EMOTE_TO_ATLAS_NAME, PANEL_WIDTH, SCREEN_WIDTH, App, Camera, load_sprite_assets, parse_args
from agent_town.core import create_default_simulation
from agent_town.llm import LLMRuntimeStatus


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

    def test_llm_toggle_connects_when_disabled_and_disconnects_when_enabled(self):
        app = App(create_default_simulation(), smoke_test=True)
        calls = []
        try:
            app.llm_scheduler.status = LLMRuntimeStatus(enabled=False, state="disabled")
            app.llm_scheduler.connect_from_env = lambda: calls.append("connect") or True

            app._toggle_llm()

            app.llm_scheduler.status = LLMRuntimeStatus(enabled=True, state="idle", model="gemma")
            app.llm_scheduler.disable = lambda reason="": calls.append(f"disable:{reason}")

            app._toggle_llm()
        finally:
            app.llm_scheduler.shutdown(wait=True)

        self.assertEqual(calls, ["connect", "disable:Disconnected in game."])

    def test_llm_status_text_explains_runtime_toggle(self):
        app = App(create_default_simulation(), smoke_test=True)
        try:
            self.assertIn("Press L to connect", app._llm_status_text())

            app.llm_scheduler.status = LLMRuntimeStatus(enabled=True, state="idle", model="gemma")

            self.assertIn("Press L to disconnect", app._llm_status_text())
        finally:
            app.llm_scheduler.shutdown(wait=True)

    def test_llm_toggle_labels_make_connection_state_obvious(self):
        app = App(create_default_simulation(), smoke_test=True)
        try:
            disconnected = app._llm_toggle_labels()
            self.assertEqual(disconnected[0], "LM Studio disconnected")
            self.assertIn("Click or press L to connect", disconnected[1])

            app.llm_scheduler.status = LLMRuntimeStatus(enabled=True, state="thinking", model="gemma")

            connected = app._llm_toggle_labels()
            self.assertEqual(connected[0], "LM Studio connected")
            self.assertIn("click or press L to disconnect", connected[1])
        finally:
            app.llm_scheduler.shutdown(wait=True)

    def test_clicking_llm_panel_control_toggles_local_model(self):
        app = App(create_default_simulation(), smoke_test=True)
        calls = []
        try:
            app.llm_button_rect = pygame.Rect(SCREEN_WIDTH - PANEL_WIDTH + 24, 20, 282, 54)
            app.llm_scheduler.status = LLMRuntimeStatus(enabled=False, state="disabled")
            app.llm_scheduler.connect_from_env = lambda: calls.append("connect") or True

            event = pygame.event.Event(
                pygame.MOUSEBUTTONDOWN,
                {"button": 1, "pos": app.llm_button_rect.center},
            )
            app._handle_mouse(event)
        finally:
            app.llm_scheduler.shutdown(wait=True)

        self.assertEqual(calls, ["connect"])


if __name__ == "__main__":
    unittest.main()
