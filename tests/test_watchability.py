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

from agent_town import civilization, engine
from agent_town.core import Good
from agent_town.civilization_view import (
    ExceptionAgeTracker,
    GoodsFlowTracker,
    MARGIN,
    building_exception_badges,
    exception_age_text,
    exception_stack_items,
    exception_signature,
    governor_card_summary,
    governor_macro_text,
    load_civilization_assets,
    macro_strip_chips,
    menu_speed_button_rects,
    render_civilization,
)
from agent_town.governor import build_exception_queue


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


if __name__ == "__main__":
    unittest.main()
