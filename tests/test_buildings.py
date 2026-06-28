import unittest

from agent_town import buildings, civilization
from agent_town.civilization_view import BUILDING_SPRITE


EXPECTED_BUILDINGS = {
    "Forester": 1,
    "Sawmill": 1,
    "Quarry": 1,
    "Farm": 3,
    "Mill": 2,
    "Bakery": 2,
}


class DefaultBuildingTests(unittest.TestCase):
    def test_default_civilization_has_expected_build1_buildings(self):
        state = civilization.create_default_civilization()
        counts: dict[str, int] = {}
        for building in state.buildings.values():
            counts[building.kind] = counts.get(building.kind, 0) + 1

        self.assertEqual(counts, EXPECTED_BUILDINGS)

    def test_each_build1_building_has_definition_and_viewer_sprite(self):
        for kind in EXPECTED_BUILDINGS:
            with self.subTest(kind=kind):
                definition = buildings.building_def(kind)

                self.assertEqual(definition.kind, kind)
                self.assertIn(kind, BUILDING_SPRITE)

    def test_default_buildings_are_inside_grid(self):
        state = civilization.create_default_civilization()
        self.assertIsNotNone(state.grid)

        for building in state.buildings.values():
            with self.subTest(building=building.id):
                self.assertTrue(state.grid.in_bounds(building.x, building.y))


if __name__ == "__main__":
    unittest.main()
