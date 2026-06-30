"""Reachability-region helpers for scale foundations (Paper 7)."""

import unittest

from agent_town import world
from agent_town.core import GridMap


class ReachabilityRegionTests(unittest.TestCase):
    def test_water_splits_walkable_regions(self):
        grid = GridMap(
            3,
            3,
            (
                ("grass", world.TILE_WATER, "grass"),
                ("grass", world.TILE_WATER, "grass"),
                ("grass", world.TILE_WATER, "grass"),
            ),
        )

        regions = world.reachability_regions(grid)

        self.assertIsNotNone(regions[0][0])
        self.assertIsNone(regions[0][1])
        self.assertEqual(regions[0][0], regions[2][0])
        self.assertEqual(regions[0][2], regions[2][2])
        self.assertNotEqual(regions[0][0], regions[0][2])
        self.assertTrue(world.same_reachability_region(grid, 0, 0, 0, 2, regions=regions))
        self.assertFalse(world.same_reachability_region(grid, 0, 0, 2, 0, regions=regions))


if __name__ == "__main__":
    unittest.main()
