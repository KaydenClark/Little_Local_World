import unittest

from agent_town.assets import load_kenney_manifest


class KenneyAssetTests(unittest.TestCase):
    def test_manifest_points_to_selected_kenney_spritesheets(self):
        manifest = load_kenney_manifest()

        self.assertEqual(manifest.tile_size, 16)
        self.assertEqual(manifest.margin, 1)
        self.assertTrue(manifest.characters_path.is_file())
        self.assertTrue(manifest.tiles_path.is_file())
        self.assertTrue(manifest.emotes_path.is_file())


if __name__ == "__main__":
    unittest.main()
