import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from agent_town import civilization, engine, work
from agent_town.civilization_view import (
    BUILDING_SPRITE,
    INSPECTOR_WIDTH,
    PAWN_ROSTER_HEIGHT,
    WORK_GRID_TYPES,
    Camera,
    CivilizationViewer,
    _need_bar_color,
    _mood_color,
    _pawn_status_label,
    _top_skills,
    cycle_work_priority,
    find_pawn_at_screen,
    governor_status_line,
    hud_button_rects,
    idle_pawn_count,
    load_civilization_assets,
    parse_args,
    render_civilization,
    work_grid_cell_at,
    work_grid_layout,
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

    def test_render_with_work_grid_and_decision_trace_does_not_crash(self):
        assets = load_civilization_assets()
        font = pygame.font.Font(None, 16)
        state = civilization.create_default_civilization()
        engine.step_hour(state)  # populate work_decisions so the inspector trace draws

        surface = pygame.Surface((state.grid.width * 25 + 24 + INSPECTOR_WIDTH, state.grid.height * 25 + 200))
        render_civilization(
            surface,
            state,
            assets,
            font,
            (12, 12),
            selected_pawn_id="pawn00",
            show_inspector=True,
            show_work_grid=True,
        )


class WorkGridTests(unittest.TestCase):
    def _map_rect(self):
        return pygame.Rect(0, PAWN_ROSTER_HEIGHT, 700, 500)

    def test_layout_covers_every_pawn_and_work_type(self):
        state = civilization.create_default_civilization()
        pawn_ids = sorted(state.pawns)
        layout = work_grid_layout(self._map_rect(), pawn_ids)

        self.assertEqual(len(layout.headers), len(WORK_GRID_TYPES))
        self.assertEqual(len(layout.rows), len(pawn_ids))  # all 12 fit
        self.assertEqual(len(layout.cells), len(pawn_ids) * len(WORK_GRID_TYPES))

    def test_cell_hit_test_round_trips(self):
        state = civilization.create_default_civilization()
        pawn_ids = sorted(state.pawns)
        rect, pid, wt = work_grid_layout(self._map_rect(), pawn_ids).cells[0]

        self.assertEqual(work_grid_cell_at(self._map_rect(), pawn_ids, rect.center), (pid, wt))

    def test_clicking_a_cell_cycles_that_priority(self):
        state = civilization.create_default_civilization()
        pawn = state.pawns["pawn00"]
        work_type = WORK_GRID_TYPES[0]
        before = work.default_priority(pawn, work_type)
        expected = {0: 1, 1: 2, 2: 3, 3: 4, 4: 0}[before]

        cycle_work_priority(state, "pawn00", work_type)

        self.assertEqual(pawn.work_priorities[work_type], expected)

    def test_work_button_rect_exists_for_toggle(self):
        rects = hud_button_rects(900, 600)
        self.assertIn("Work", rects)

    def test_idle_pawn_count_after_arbiter_runs(self):
        state = civilization.create_default_civilization()
        engine.step_hour(state)
        # The default civ has 12 pawns for 11 slots, so exactly one stays idle.
        self.assertEqual(idle_pawn_count(state), 1)


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


class HistoryFeedTests(unittest.TestCase):
    def _surface(self):
        return pygame.Surface((900, 700))

    def test_render_with_history_panel_and_alert_does_not_crash(self):
        state = civilization.create_default_civilization()
        assets = load_civilization_assets()
        font = pygame.font.Font(None, 16)
        events = [
            {"type": "event", "day": 0, "hour": 8, "severity": "warn", "kind": "good_low", "text": "Bread low"},
            {"type": "event", "day": 0, "hour": 9, "severity": "critical", "kind": "good_depleted", "text": "Bread depleted"},
        ]
        render_civilization(
            self._surface(), state, assets, font, (12, 12),
            show_inspector=True, show_history=True, events=events, alert=("critical", 2),
        )

    def test_smoke_viewer_logs_events_to_ring(self):
        viewer = CivilizationViewer(smoke_test=True)
        viewer.run()
        # The events ring is event-only and never holds snapshots/decisions.
        self.assertTrue(all(r.get("type") == "event" for r in viewer.event_ring.records))

    def test_opening_history_acknowledges_alert(self):
        viewer = CivilizationViewer(smoke_test=True)
        viewer._alert_severity = "critical"
        viewer._alert_count = 3
        buttons = hud_button_rects(viewer.screen.get_width(), viewer.screen.get_height())
        viewer._handle_click(buttons["History"].center)
        self.assertTrue(viewer.show_history)
        self.assertIsNone(viewer._alert_severity)
        self.assertEqual(viewer._alert_count, 0)


if __name__ == "__main__":
    unittest.main()
