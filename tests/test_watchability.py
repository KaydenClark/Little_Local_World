"""Watchability refresh (Fable review Slice E): the town-level story on screen.

Pins the four visibility fixes: the macro strip shows civ mood and per-good
production flow (P-3, P-2: bread must not appear from nothing), exception rows
carry a persistence age so a five-day-old warning reads chronic instead of
urgent (P-1), the governor summary leads with who-is-driving so truncation
cannot hide attribution (P-6), buildings with active problems carry a truthful
map badge (P-7), and the Menu speed buttons no longer paint over another row's
text (F1.6).
"""

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from agent_town import civilization, engine, telemetry, world
from agent_town.core import Good, ResourceNode
from agent_town.civilization_view import (
    ExceptionAgeTracker,
    GoodsFlowTracker,
    MARGIN,
    building_exception_badges,
    building_sublabel,
    exception_age_text,
    exception_stack_items,
    exception_signature,
    governor_card_summary,
    governor_macro_text,
    load_civilization_assets,
    macro_strip_chips,
    menu_speed_button_rects,
    node_visual,
    pawn_state_label,
    render_civilization,
    storehouse_stock_lines,
)
from agent_town.governor import FallbackGovernor, build_exception_queue


class MacroStripChipTests(unittest.TestCase):
    def test_mood_chip_present(self):
        state = civilization.create_default_civilization()
        chips = macro_strip_chips(state)
        self.assertTrue(any(chip.startswith("Mood ") for chip in chips), chips)

    def test_goods_chips_show_flow_when_producing(self):
        state = civilization.create_default_civilization()
        chips = macro_strip_chips(state, flows_today={Good.BREAD: 12, Good.GRAIN: 38})
        self.assertIn(f"Bread {state.stockpile.counts.get(Good.BREAD, 0)} +12", chips)
        # The P-2 case: zero standing grain stock still shows the chain flowing.
        self.assertIn("Grain 0 +38", chips)

    def test_goods_chips_plain_when_no_flow(self):
        state = civilization.create_default_civilization()
        chips = macro_strip_chips(state, flows_today={})
        self.assertIn(f"Bread {state.stockpile.counts.get(Good.BREAD, 0)}", chips)
        self.assertFalse(any("+" in chip and chip.startswith("Bread") for chip in chips))

    def test_flow_tracker_reports_last_day_production(self):
        state = civilization.create_default_civilization()
        tracker = GoodsFlowTracker()
        tracker.observe(state)
        for _ in range(24):
            engine.step_hour(state)
        flows = tracker.observe(state)
        self.assertGreater(sum(flows.values()), 0, "a day of the default civ must show flow")

    def test_flow_tracker_window_slides(self):
        state = civilization.create_default_civilization()
        tracker = GoodsFlowTracker(window=2)
        tracker.observe(state)
        state.stockpile.add(Good.STONE, 5)
        tracker.observe(state)
        self.assertEqual(tracker.observe(state).get(Good.STONE, 0), 5)
        # Two more quiet hours push the +5 out of the 2-hour window.
        tracker.observe(state)
        self.assertEqual(tracker.observe(state).get(Good.STONE, 0), 0)


class ExceptionAgeTests(unittest.TestCase):
    def _blocked_state(self):
        """One engine hour staffs the bakeries; with no flour they raise
        missing_inputs exceptions."""
        state = civilization.create_default_civilization()
        engine.step_hour(state)
        self.assertTrue(build_exception_queue(state), "expected active exceptions")
        return state

    def test_ages_accumulate_per_signature(self):
        state = self._blocked_state()
        tracker = ExceptionAgeTracker()
        tracker.observe(state)
        ages = tracker.observe(state)
        self.assertTrue(ages)
        self.assertTrue(all(age == 2 for age in ages.values()), ages)

    def test_age_resets_when_exception_clears(self):
        state = self._blocked_state()
        tracker = ExceptionAgeTracker()
        tracker.observe(state)
        # Pick a problem the fresh civ below does NOT share (a fresh civ now
        # carries field_growing narration from day 0, so any of those
        # signatures would keep aging straight through the "cleared" hour).
        sig = next(s for s in sorted(tracker.ages) if s.startswith("missing_inputs"))
        # The problem disappears for an hour...
        tracker.ages.pop(sig)
        empty_state = civilization.create_default_civilization()  # no exceptions pre-step
        tracker.observe(empty_state)
        # ...and returns: it re-ages from 1, not from its old streak.
        ages = tracker.observe(state)
        self.assertEqual(ages[sig], 1)

    def test_stack_items_carry_age(self):
        state = self._blocked_state()
        tracker = ExceptionAgeTracker()
        for _ in range(30):
            tracker.observe(state)
        items = exception_stack_items(state, tracker.ages)
        self.assertTrue(all(item.age_hours == 30 for item in items), items)

    def test_age_text_bands(self):
        self.assertEqual(exception_age_text(0), "")
        self.assertEqual(exception_age_text(1), "")
        self.assertEqual(exception_age_text(6), "6h")
        self.assertEqual(exception_age_text(24), "1d")
        self.assertEqual(exception_age_text(52), "2d 4h")


class GovernorAttributionTests(unittest.TestCase):
    def test_attribution_leads_the_macro_text(self):
        state = civilization.create_default_civilization()
        summary = governor_card_summary(state)
        text = governor_macro_text(summary, None)
        self.assertTrue(
            text.startswith("Governor: Fallback autopilot"),
            f"who-is-driving must lead so truncation cannot hide it: {text}",
        )
        self.assertIn(summary.plan, text)


class BuildingBadgeTests(unittest.TestCase):
    def test_blocked_buildings_get_badges(self):
        state = civilization.create_default_civilization()
        engine.step_hour(state)  # staff buildings; bakeries/mills lack inputs
        badges = building_exception_badges(state)
        blocked = {
            exc.building_id
            for exc in build_exception_queue(state)
            if exc.kind in ("missing_inputs", "unstaffed_building") and exc.building_id in state.buildings
        }
        self.assertTrue(blocked, "expected blocked buildings after hour 1")
        for building_id in blocked:
            self.assertIn(building_id, badges)

    def test_healthy_building_has_no_badge(self):
        state = civilization.create_default_civilization()
        badges = building_exception_badges(state)
        # Pre-step, nothing is staffed-and-blocked with a building_id exception
        # except unstaffed ones; badge map must only ever reference real buildings.
        for building_id in badges:
            self.assertIn(building_id, state.buildings)


class MenuLayoutTests(unittest.TestCase):
    def test_speed_buttons_do_not_cover_other_rows(self):
        rect = pygame.Rect(0, 560, 1280, 320)
        panel = rect.inflate(-MARGIN * 2, -MARGIN * 2)
        buttons = menu_speed_button_rects(rect)
        rows_top = panel.y + 36  # first row y in _draw_panel_lines
        speed_row_top = rows_top + 2 * 20
        keyboard_row_top = rows_top + 4 * 20  # Speed row + spacer row
        for button in buttons.values():
            self.assertGreaterEqual(button.top, speed_row_top - 4)
            self.assertLessEqual(button.bottom, keyboard_row_top)


class RenderSmokeTests(unittest.TestCase):
    def setUp(self):
        pygame.display.init()
        pygame.font.init()
        pygame.display.set_mode((64, 64))

    def test_render_with_flows_ages_and_badges(self):
        assets = load_civilization_assets()
        font = pygame.font.Font(None, 16)
        state = civilization.create_default_civilization()
        engine.step_hour(state)
        tracker = ExceptionAgeTracker()
        for _ in range(48):
            tracker.observe(state)
        surface = pygame.Surface((1280, 900))
        render_civilization(
            surface, state, assets, font, (12, 12),
            flows_today={Good.BREAD: 9, Good.GRAIN: 20},
            exception_ages=tracker.ages,
        )


class AttentionLabelTests(unittest.TestCase):
    """Review P-8: the card shows a derived situation label, never a fake %."""

    def test_crisis_when_a_critical_exception_exists(self):
        state = civilization.create_default_civilization()
        state.pawns["pawn00"].state = "wandering"
        summary = governor_card_summary(state)
        self.assertTrue(summary.attention.startswith("crisis"), summary.attention)

    def test_attention_appears_in_macro_text_instead_of_a_percentage(self):
        state = civilization.create_default_civilization()
        summary = governor_card_summary(state)
        text = governor_macro_text(summary, None)
        self.assertIn(summary.attention, text)
        self.assertNotRegex(text, r"\d+%")


class PawnStateLabelTests(unittest.TestCase):
    """Review P-9: the sheet's state and the Idle chip share one definition."""

    def test_employed_pawn_between_blocks_reads_off_shift(self):
        state = civilization.create_default_civilization()
        engine.step_hour(state)
        employed = next(p for p in state.pawns.values() if p.assignment is not None)
        employed.state = "idle"
        self.assertEqual(pawn_state_label(employed), "off shift")

    def test_jobless_pawn_reads_idle_no_job(self):
        state = civilization.create_default_civilization()
        pawn = next(iter(state.pawns.values()))
        pawn.assignment = None
        pawn.state = "idle"
        self.assertEqual(pawn_state_label(pawn), "idle (no job)")


class DecisionPressureTests(unittest.TestCase):
    """Review P-5: the audit's context section is derived from the record."""

    def test_decision_records_carry_active_pressures(self):
        state = civilization.create_default_civilization()
        gov = FallbackGovernor()
        result = engine.step_hour(state, gov)
        record = telemetry.build_decision(state, gov, result)
        self.assertIn("pressures", record)
        live_kinds = {exc.kind for exc in build_exception_queue(state)}
        for pressure in record["pressures"]:
            self.assertIn(pressure.split(" x")[0], live_kinds)


class SourcingVisibilityTests(unittest.TestCase):
    """Physical sourcing must be readable from the map itself."""

    def test_node_visuals_cover_the_field_lifecycle(self):
        state = civilization.create_default_civilization()
        farms = sorted(
            (b for b in state.buildings.values() if b.kind == "Farm"), key=lambda b: b.id
        )
        visuals = {node_visual(world.farm_field(state, farm))[0] for farm in farms}
        self.assertIn("field_ripe", visuals)
        self.assertIn("field_growing", visuals)

    def test_depleted_stand_reads_depleted(self):
        node = ResourceNode(Good.LOGS, 0, 1, 1, max_amount=10, state="empty")
        self.assertEqual(node_visual(node), ("depleted", 0.0))

    def test_farm_sublabel_explains_the_field(self):
        state = civilization.create_default_civilization()
        farms = sorted(
            (b for b in state.buildings.values() if b.kind == "Farm"), key=lambda b: b.id
        )
        labels = [building_sublabel(state, farm) for farm in farms]
        self.assertIn("ripe", labels)
        self.assertTrue(any(label.startswith("growing") for label in labels), labels)

    def test_storehouse_lines_show_real_held_stock(self):
        state = civilization.create_default_civilization()
        lines = storehouse_stock_lines(state)
        self.assertTrue(lines)
        self.assertTrue(lines[0].startswith("Bread"), lines)

    def test_seed_chip_present_in_macro_strip(self):
        state = civilization.create_default_civilization()
        chips = macro_strip_chips(state)
        self.assertIn(f"Seed {state.seed_grain}", chips)


if __name__ == "__main__":
    unittest.main()
