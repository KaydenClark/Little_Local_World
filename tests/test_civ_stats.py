"""Step 3 coverage: Civ-wide need averages and the Civ stats panel render."""

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from agent_town import civilization, economy
from agent_town.core import FactionState, NEED_FOOD, NEED_RECREATION, NEED_REST, NEED_WATER, Pawn
from agent_town.civilization_view import CIV_STATS_WIDTH, _draw_civ_stats, load_civilization_assets


def _pawn(pid, food, rest, water, rec):
    return Pawn(id=pid, name=pid, needs={NEED_FOOD: food, NEED_REST: rest, NEED_WATER: water, NEED_RECREATION: rec})


class AverageNeedTests(unittest.TestCase):
    def test_average_need_is_the_mean_across_pawns(self):
        state = FactionState()
        state.pawns["a"] = _pawn("a", food=0.2, rest=1.0, water=0.3, rec=0.5)
        state.pawns["b"] = _pawn("b", food=0.4, rest=0.0, water=0.7, rec=0.5)

        self.assertAlmostEqual(economy.average_need(state, NEED_FOOD), 0.3)
        self.assertAlmostEqual(economy.average_need(state, NEED_REST), 0.5)
        self.assertAlmostEqual(economy.average_need(state, NEED_WATER), 0.5)
        self.assertAlmostEqual(economy.average_need(state, NEED_RECREATION), 0.5)

    def test_empty_civilization_reads_zero(self):
        self.assertEqual(economy.average_need(FactionState(), NEED_FOOD), 0.0)

    def test_missing_need_counts_as_satisfied(self):
        state = FactionState()
        state.pawns["a"] = Pawn(id="a", name="a", needs={})  # no needs set
        self.assertEqual(economy.average_need(state, NEED_FOOD), 1.0)

    def test_unknown_need_is_rejected(self):
        with self.assertRaises(ValueError):
            economy.average_need(FactionState(), "comfort")


class CivStatsPanelTests(unittest.TestCase):
    def setUp(self):
        pygame.display.init()
        pygame.font.init()
        pygame.display.set_mode((64, 64))

    def test_draw_civ_stats_renders_without_crashing(self):
        load_civilization_assets()  # ensures font/display are ready like the viewer
        font = pygame.font.Font(None, 16)
        state = civilization.create_default_civilization()
        surface = pygame.Surface((600, 400))

        rect = _draw_civ_stats(surface, font, state, (12, 80))

        self.assertEqual(rect.width, CIV_STATS_WIDTH)
        self.assertEqual(rect.topleft, (12, 80))


if __name__ == "__main__":
    unittest.main()
