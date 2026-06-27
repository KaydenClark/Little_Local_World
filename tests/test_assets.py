import unittest

from agent_town.assets import load_kenney_manifest
from agent_town.app import LOCATION_FOOTPRINTS, SCENERY_STAMPS, TERRAIN_TILE_INDEXES


class KenneyAssetTests(unittest.TestCase):
    def test_manifest_points_to_selected_kenney_spritesheets(self):
        manifest = load_kenney_manifest()

        self.assertEqual(manifest.tile_size, 16)
        self.assertEqual(manifest.margin, 1)
        self.assertTrue(manifest.characters_path.is_file())
        self.assertTrue(manifest.tiles_path.is_file())
        self.assertTrue(manifest.emotes_path.is_file())

    def test_location_visuals_use_tile_clusters(self):
        expected_kinds = {"home", "food", "social", "knowledge", "work", "quiet"}

        self.assertEqual(set(LOCATION_FOOTPRINTS), expected_kinds)
        for kind, footprint in LOCATION_FOOTPRINTS.items():
            with self.subTest(kind=kind):
                self.assertGreaterEqual(len(footprint.tiles), 9)
                self.assertGreaterEqual(len({tile.index for tile in footprint.tiles}), 3)
                self.assertTrue(any(tile.role == "floor" for tile in footprint.tiles))
                self.assertTrue(any(tile.role == "prop" for tile in footprint.tiles))
                self.assertGreater(footprint.label_offset_y, 0)

    def test_terrain_palette_uses_multiple_tile_types(self):
        self.assertGreaterEqual(len(TERRAIN_TILE_INDEXES["grass"]), 4)
        self.assertGreaterEqual(len(TERRAIN_TILE_INDEXES["field"]), 4)
        self.assertGreaterEqual(len(TERRAIN_TILE_INDEXES["water"]), 4)

    def test_visual_language_has_roofs_and_environment_resources(self):
        for kind in ("home", "food", "knowledge", "work"):
            with self.subTest(kind=kind):
                roles = {tile.role for tile in LOCATION_FOOTPRINTS[kind].tiles}
                self.assertIn("roof", roles)
                self.assertIn("wall", roles)

        scenery_roles = {stamp.role for stamp in SCENERY_STAMPS}
        self.assertGreaterEqual(len(SCENERY_STAMPS), 20)
        self.assertTrue({"tree", "rock", "resource", "farm"}.issubset(scenery_roles))


if __name__ == "__main__":
    unittest.main()
