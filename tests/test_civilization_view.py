import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from agent_town import civilization, engine, work
from agent_town.core import ConstructionSite, Good, GovernorAction
from agent_town.civilization_view import (
    BUILDING_SPRITE,
    COMMAND_PANEL_HEIGHT,
    COMMAND_STRIP_HEIGHT,
    INSPECTOR_WIDTH,
    INSPECTOR_TABS,
    MACRO_STRIP_HEIGHT,
    PAWN_ROSTER_HEIGHT,
    PANEL_BY_BUTTON,
    RIGHT_COLUMN_WIDTH,
    WORK_GRID_TYPES,
    Camera,
    CivilizationViewer,
    assign_panel_target_at,
    assign_panel_targets,
    active_panel_from_button,
    _construction_progress,
    _need_bar_color,
    _mood_color,
    _pawn_readability_markers,
    _pawn_status_label,
    _top_skills,
    cycle_work_priority,
    exception_stack_items,
    find_pawn_at_screen,
    governor_card_summary,
    governor_status_line,
    hud_button_rects,
    history_panel_record_at,
    history_panel_row_rects,
    inspector_tab_rects,
    idle_pawn_count,
    load_civilization_assets,
    menu_speed_button_rects,
    parse_args,
    render_civilization,
    right_column_regions,
    viewer_layout,
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

    def test_render_each_command_panel_does_not_crash(self):
        assets = load_civilization_assets()
        font = pygame.font.Font(None, 16)
        state = civilization.create_default_civilization()
        engine.step_hour(state)
        events = [
            {"type": "event", "day": 0, "hour": 9, "severity": "warn", "kind": "missing_inputs", "text": "Flour low"},
        ]

        for panel in PANEL_BY_BUTTON.values():
            with self.subTest(panel=panel):
                surface = pygame.Surface((960, 720))
                render_civilization(
                    surface,
                    state,
                    assets,
                    font,
                    (12, 12),
                    selected_pawn_id="pawn00",
                    active_panel=panel,
                    events=events,
                )

    def test_render_each_inspector_tab_does_not_crash(self):
        assets = load_civilization_assets()
        font = pygame.font.Font(None, 16)
        state = civilization.create_default_civilization()
        engine.step_hour(state)

        for tab in (tab.lower() for tab in INSPECTOR_TABS):
            with self.subTest(tab=tab):
                surface = pygame.Surface((960, 720))
                render_civilization(
                    surface,
                    state,
                    assets,
                    font,
                    (12, 12),
                    selected_pawn_id="pawn00",
                    inspector_tab=tab,
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
        state.buildings.pop("waterwell1")
        engine.step_hour(state)
        # Removing the well leaves 12 pawns for 11 legal slots, so one stays idle.
        self.assertEqual(idle_pawn_count(state), 1)


class ViewerLayoutTests(unittest.TestCase):
    def test_default_layout_regions_do_not_overlap(self):
        layout = viewer_layout(900, 700)

        self.assertEqual(layout.macro.height, MACRO_STRIP_HEIGHT)
        self.assertEqual(layout.roster.height, PAWN_ROSTER_HEIGHT)
        self.assertEqual(layout.command_strip.height, COMMAND_STRIP_HEIGHT)
        self.assertEqual(layout.right.width, RIGHT_COLUMN_WIDTH)
        self.assertIsNone(layout.command_panel)

        fixed_regions = [layout.macro, layout.roster, layout.map, layout.right, layout.command_strip]
        for index, rect in enumerate(fixed_regions):
            with self.subTest(region=index):
                self.assertGreater(rect.width, 0)
                self.assertGreater(rect.height, 0)
        for a_index, a in enumerate(fixed_regions):
            for b_index, b in enumerate(fixed_regions):
                if a_index >= b_index:
                    continue
                self.assertFalse(a.colliderect(b), f"{a} overlaps {b}")

    def test_wide_layout_with_panel_reserves_panel_without_overlap(self):
        layout = viewer_layout(1280, 800, active_panel="architect")

        self.assertIsNotNone(layout.command_panel)
        self.assertEqual(layout.command_panel.height, COMMAND_PANEL_HEIGHT)
        fixed_regions = [layout.macro, layout.roster, layout.map, layout.right, layout.command_panel, layout.command_strip]
        for a_index, a in enumerate(fixed_regions):
            for b_index, b in enumerate(fixed_regions):
                if a_index >= b_index:
                    continue
                self.assertFalse(a.colliderect(b), f"{a} overlaps {b}")

    def test_all_bottom_buttons_map_to_panel_ids(self):
        rects = hud_button_rects(900, 700)

        self.assertEqual(set(rects), set(PANEL_BY_BUTTON))
        for label in PANEL_BY_BUTTON:
            self.assertEqual(active_panel_from_button(label), PANEL_BY_BUTTON[label])


class MapReadabilityTests(unittest.TestCase):
    def test_construction_progress_counts_materials_before_work(self):
        site = ConstructionSite(
            id="site1",
            building_kind="Sawmill",
            x=3,
            y=4,
            required={Good.PLANKS: 4, Good.STONE: 2},
            delivered={Good.PLANKS: 2},
            work_remaining=999.0,
        )

        self.assertAlmostEqual(_construction_progress(site), 1 / 6, places=2)

        site.delivered = {Good.PLANKS: 4, Good.STONE: 2}
        self.assertAlmostEqual(_construction_progress(site), 0.5)

        site.work_remaining = 0.0
        self.assertEqual(_construction_progress(site), 1.0)

    def test_pawn_readability_markers_distinguish_hover_selection_idle_and_danger(self):
        state = civilization.create_default_civilization()
        state.buildings.pop("waterwell1")
        engine.step_hour(state)
        idle_pawn = next(
            pawn
            for pawn in state.pawns.values()
            if state.work_decisions[pawn.id].lane == work.LANE_IDLE
        )

        self.assertIn(
            "idle",
            _pawn_readability_markers(state, idle_pawn, selected=False, hovered=False),
        )
        self.assertIn(
            "hover",
            _pawn_readability_markers(state, idle_pawn, selected=False, hovered=True),
        )

        idle_pawn.state = STATE_SLACKING
        markers = _pawn_readability_markers(state, idle_pawn, selected=True, hovered=True)

        self.assertIn("selection", markers)
        self.assertNotIn("hover", markers)
        self.assertEqual(markers[-1], "danger")

    def test_render_with_hovered_pawn_and_construction_site_does_not_crash(self):
        assets = load_civilization_assets()
        font = pygame.font.Font(None, 16)
        state = civilization.create_default_civilization()
        state.construction_sites["site1"] = ConstructionSite(
            id="site1",
            building_kind="Sawmill",
            x=4,
            y=5,
            required={Good.PLANKS: 4},
            delivered={Good.PLANKS: 2},
            work_remaining=10.0,
        )
        surface = pygame.Surface((state.grid.width * 25 + 24 + INSPECTOR_WIDTH, state.grid.height * 25 + 200))

        render_civilization(
            surface,
            state,
            assets,
            font,
            (12, 12),
            selected_pawn_id="pawn00",
            hovered_pawn_id="pawn01",
            show_inspector=True,
        )


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


class GovernorObserverModelTests(unittest.TestCase):
    def setUp(self):
        pygame.display.init()
        pygame.font.init()
        pygame.display.set_mode((64, 64))

    def test_exception_stack_prioritizes_breaks_over_supply_warnings(self):
        state = civilization.create_default_civilization()
        state.stockpile.counts[Good.WATER] = 0
        state.pawns["pawn00"].state = "wandering"

        items = exception_stack_items(state)

        self.assertGreaterEqual(len(items), 2)
        self.assertEqual(items[0].kind, "pawn_break")
        self.assertEqual(items[0].severity, "critical")
        self.assertIn("mental break", items[0].cause.lower())
        self.assertIn("low_water", [item.kind for item in items])

    def test_governor_card_surfaces_low_water_bottleneck(self):
        state = civilization.create_default_civilization()
        state.stockpile.counts[Good.WATER] = 0

        summary = governor_card_summary(state, FallbackGovernor())

        self.assertIn("water", summary.plan.lower())
        self.assertIn("water", summary.bottleneck.lower())
        self.assertEqual(summary.top_exception.kind, "low_water")
        self.assertLess(summary.confidence, 80)

    def test_governor_card_describes_last_reallocation_actions(self):
        state = civilization.create_default_civilization()

        summary = governor_card_summary(
            state,
            FallbackGovernor(),
            last_actions=[GovernorAction.set_work_priority("all", "water", 1)],
        )

        self.assertIn("work priorities", summary.last_reallocation.lower())

    def test_render_with_governor_observer_overlays_does_not_crash(self):
        assets = load_civilization_assets()
        font = pygame.font.Font(None, 16)
        state = civilization.create_default_civilization()
        state.stockpile.counts[Good.WATER] = 0

        surface = pygame.Surface((state.grid.width * 25 + 24 + INSPECTOR_WIDTH, state.grid.height * 25 + 220))
        render_civilization(surface, state, assets, font, (12, 12), show_inspector=True)


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

    def test_bottom_buttons_set_one_active_panel(self):
        viewer = CivilizationViewer(smoke_test=True)
        buttons = hud_button_rects(viewer.screen.get_width(), viewer.screen.get_height())

        viewer._handle_click(buttons["Architect"].center)
        self.assertEqual(viewer.active_panel, "architect")
        viewer._handle_click(buttons["Work"].center)
        self.assertEqual(viewer.active_panel, "work")
        viewer._handle_click(buttons["Work"].center)
        self.assertIsNone(viewer.active_panel)

    def test_escape_closes_panel_before_quit(self):
        viewer = CivilizationViewer(smoke_test=True)
        viewer.active_panel = "menu"

        viewer._handle_escape()

        self.assertIsNone(viewer.active_panel)
        self.assertTrue(viewer.running)

    def test_work_panel_cell_click_cycles_priority(self):
        viewer = CivilizationViewer(smoke_test=True)
        buttons = hud_button_rects(viewer.screen.get_width(), viewer.screen.get_height())
        viewer._handle_click(buttons["Work"].center)
        layout = viewer_layout(viewer.screen.get_width(), viewer.screen.get_height(), active_panel="work")
        rect, pawn_id, work_type = work_grid_layout(layout.command_panel, sorted(viewer.state.pawns)).cells[0]
        pawn = viewer.state.pawns[pawn_id]
        before = work.default_priority(pawn, work_type)

        viewer._handle_click(rect.center)

        self.assertEqual(pawn.work_priorities[work_type], {0: 1, 1: 2, 2: 3, 3: 4, 4: 0}[before])

    def test_inspector_tab_click_changes_active_tab(self):
        viewer = CivilizationViewer(smoke_test=True)
        engine.step_hour(viewer.state)
        layout = viewer_layout(viewer.screen.get_width(), viewer.screen.get_height())
        _exceptions, inspector = right_column_regions(layout.right)
        tabs = inspector_tab_rects(viewer.state, viewer.selected_pawn_id, inspector)

        viewer._handle_click(tabs["bio"].center)

        self.assertEqual(viewer.inspector_tab, "bio")

    def test_assign_panel_click_forces_open_job_slot(self):
        viewer = CivilizationViewer(smoke_test=True)
        viewer.active_panel = "assign"
        viewer.selected_pawn_id = "pawn00"
        pawn = viewer.state.pawns["pawn00"]
        building = next(b for b in viewer.state.buildings.values() if b.built and b.recipe is not None)
        building.staffed_by.clear()
        for other in viewer.state.buildings.values():
            if "pawn00" in other.staffed_by:
                other.staffed_by = [pid for pid in other.staffed_by if pid != "pawn00"]
        pawn.assignment = None
        pawn.forced_assignment = None

        layout = viewer_layout(viewer.screen.get_width(), viewer.screen.get_height(), active_panel="assign")
        target = next(t for t in assign_panel_targets(viewer.state, viewer.selected_pawn_id, layout.command_panel) if t.building_id == building.id)
        self.assertEqual(
            assign_panel_target_at(viewer.state, viewer.selected_pawn_id, layout.command_panel, target.rect.center),
            target,
        )

        viewer._handle_click(target.rect.center)

        self.assertEqual(pawn.forced_assignment.building_id, building.id)
        self.assertIn("pawn00", building.staffed_by)
        self.assertEqual(viewer.inspector_tab, "log")

    def test_assign_panel_occupied_job_selects_worker(self):
        viewer = CivilizationViewer(smoke_test=True)
        viewer.active_panel = "assign"
        viewer.selected_pawn_id = "pawn00"
        building = next(b for b in viewer.state.buildings.values() if b.built and b.recipe is not None)
        building.staffed_by = ["pawn01"]
        building.job_slots = 1
        viewer.state.pawns["pawn01"].assignment = None

        layout = viewer_layout(viewer.screen.get_width(), viewer.screen.get_height(), active_panel="assign")
        target = next(t for t in assign_panel_targets(viewer.state, viewer.selected_pawn_id, layout.command_panel) if t.building_id == building.id)

        viewer._handle_click(target.rect.center)

        self.assertEqual(viewer.selected_pawn_id, "pawn01")
        self.assertEqual(viewer.inspector_tab, "log")


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

    def test_render_with_selected_governor_decision_detail_does_not_crash(self):
        state = civilization.create_default_civilization()
        assets = load_civilization_assets()
        font = pygame.font.Font(None, 16)
        decision = {
            "type": "decision",
            "day": 0,
            "hour": 9,
            "governor_kind": "FallbackGovernor",
            "llm_source": "fallback",
            "proposed": ["set_work_priority", "place_building"],
            "applied": ["set_work_priority"],
            "rejected": ["place_building"],
            "proposed_actions": [
                {"kind": "set_work_priority", "group": "all", "work_type": "farming", "level": 1},
                {"kind": "place_building", "building_kind": "Farm", "x": 4, "y": 4},
            ],
            "applied_actions": [
                {"kind": "set_work_priority", "group": "all", "work_type": "farming", "level": 1},
            ],
            "rejected_actions": [
                {"kind": "place_building", "building_kind": "Farm", "x": 4, "y": 4},
            ],
            "state_after": {
                "stockpile": {"bread": 12, "water": 8, "grain": 0, "flour": 0},
                "needs": {"food": 0.4, "water": 0.7, "rest": 0.8, "recreation": 0.5},
            },
            "decide_ms": 2.0,
            "llm_latency": 0.0,
        }

        render_civilization(
            self._surface(), state, assets, font, (12, 12),
            show_inspector=True, show_history=True, events=[decision], selected_history_record=decision,
        )

    def test_history_panel_hit_test_returns_decision_row(self):
        panel = pygame.Rect(0, 360, 900, 300)
        records = [
            {"type": "event", "day": 0, "hour": 8, "severity": "warn", "kind": "good_low", "text": "Bread low"},
            {"type": "decision", "day": 0, "hour": 9, "applied": ["set_work_priority"]},
        ]
        rows = history_panel_row_rects(records, panel)

        self.assertEqual(history_panel_record_at(records, panel, rows[0][0].center), records[1])

    def test_smoke_viewer_logs_events_to_ring(self):
        viewer = CivilizationViewer(smoke_test=True)
        viewer.run()
        # The events ring is event-only and never holds snapshots/decisions.
        self.assertTrue(all(r.get("type") == "event" for r in viewer.event_ring.records))
        self.assertTrue(any(r.get("type") == "decision" for r in viewer.history_ring.records))

    def test_opening_history_acknowledges_alert(self):
        viewer = CivilizationViewer(smoke_test=True)
        viewer._alert_severity = "critical"
        viewer._alert_count = 3
        buttons = hud_button_rects(viewer.screen.get_width(), viewer.screen.get_height())
        viewer._handle_click(buttons["History"].center)
        self.assertEqual(viewer.active_panel, "history")
        self.assertIsNone(viewer._alert_severity)
        self.assertEqual(viewer._alert_count, 0)

    def test_history_panel_click_selects_decision(self):
        viewer = CivilizationViewer(smoke_test=True)
        viewer.active_panel = "history"
        decision = {"type": "decision", "day": 0, "hour": 9, "applied": ["set_work_priority"]}
        viewer.history_ring.write(decision)
        layout = viewer_layout(viewer.screen.get_width(), viewer.screen.get_height(), active_panel="history")
        rows = history_panel_row_rects(list(viewer.history_ring.records), layout.command_panel)

        viewer._handle_click(rows[0][0].center)

        self.assertEqual(viewer.selected_history_record, decision)

    def test_menu_speed_click_sets_watch_speed(self):
        viewer = CivilizationViewer(smoke_test=True)
        viewer.active_panel = "menu"
        layout = viewer_layout(viewer.screen.get_width(), viewer.screen.get_height(), active_panel="menu")
        buttons = menu_speed_button_rects(layout.command_panel)

        viewer._handle_click(buttons[20].center)

        self.assertEqual(viewer.speed_multiplier, 20)

    def test_twenty_x_speed_advances_twenty_hours_per_normal_interval(self):
        viewer = CivilizationViewer(smoke_test=False, governor=FallbackGovernor())
        try:
            viewer.speed_multiplier = 20
            before = viewer.state.day * 24 + viewer.state.time_of_day

            viewer._advance(0.6)

            after = viewer.state.day * 24 + viewer.state.time_of_day
            self.assertEqual(after - before, 20)
        finally:
            viewer._shutdown_governor()


if __name__ == "__main__":
    unittest.main()
