import unittest

from agent_town.core import Good, GridMap, Stockpile
from agent_town.world import create_grid_map, place_resource_nodes


class StockpileTests(unittest.TestCase):
    def test_add_remove_and_has_goods(self):
        stockpile = Stockpile()

        stockpile.add(Good.LOGS, 5)
        stockpile.add(Good.STONE, 2)
        stockpile.remove(Good.LOGS, 3)

        self.assertEqual(stockpile.counts[Good.LOGS], 2)
        self.assertEqual(stockpile.counts[Good.STONE], 2)
        self.assertTrue(stockpile.has({Good.LOGS: 2, Good.STONE: 1}))
        self.assertFalse(stockpile.has({Good.PLANKS: 1}))

    def test_remove_rejects_insufficient_goods_without_mutating(self):
        stockpile = Stockpile({Good.LOGS: 2})

        with self.assertRaisesRegex(ValueError, "Insufficient logs"):
            stockpile.remove(Good.LOGS, 3)

        self.assertEqual(stockpile.counts[Good.LOGS], 2)

    def test_stockpile_rejects_invalid_amounts(self):
        stockpile = Stockpile()

        with self.assertRaisesRegex(ValueError, "positive"):
            stockpile.add(Good.LOGS, 0)
        with self.assertRaisesRegex(ValueError, "positive"):
            stockpile.remove(Good.LOGS, -1)
        with self.assertRaisesRegex(ValueError, "non-negative"):
            stockpile.has({Good.LOGS: -1})


class GridMapTests(unittest.TestCase):
    def test_create_grid_map_fills_expected_tile_count(self):
        grid = create_grid_map(4, 3)

        self.assertEqual(grid, GridMap(width=4, height=3, tiles=("grass",) * 12))

    def test_grid_map_validates_dimensions_and_tile_count(self):
        with self.assertRaisesRegex(ValueError, "positive"):
            create_grid_map(0, 3)

        with self.assertRaisesRegex(ValueError, "width \\* height"):
            GridMap(width=2, height=2, tiles=("grass",))

    def test_resource_nodes_are_deterministic_and_in_bounds(self):
        grid = create_grid_map(8, 6)

        first = place_resource_nodes(grid, seed=17)
        second = place_resource_nodes(grid, seed=17)

        self.assertEqual(first, second)
        self.assertEqual({node.kind for node in first}, {Good.LOGS, Good.GRAIN, Good.STONE})
        for node in first:
            self.assertGreater(node.amount, 0)
            self.assertGreaterEqual(node.x, 0)
            self.assertLess(node.x, grid.width)
            self.assertGreaterEqual(node.y, 0)
            self.assertLess(node.y, grid.height)


if __name__ == "__main__":
    unittest.main()
