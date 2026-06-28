import unittest

from agent_town.assets import load_civilization_manifest


class CivilizationAssetManifestTests(unittest.TestCase):
    def test_manifest_points_to_civilization_runtime_sprites(self):
        manifest = load_civilization_manifest()

        self.assertEqual(manifest.tile_size, 25)
        self.assertTrue(manifest.directory.is_dir())
        for name in ("grass", "dirt", "pavement", "tree", "house", "house2", "house3"):
            with self.subTest(sprite=name):
                self.assertTrue(manifest.path(name).is_file())

    def test_civilization_pawn_sprite_set_has_enough_variety_for_seed_civilization(self):
        manifest = load_civilization_manifest()

        self.assertGreaterEqual(len(list(manifest.directory.glob("pawn_*.png"))), 12)

    def test_civilization_asset_notes_record_provenance_and_suspect_assets(self):
        readme = (load_civilization_manifest().directory / "README.md").read_text(encoding="utf-8")

        self.assertIn("Tiny Characters Set", readme)
        self.assertIn("CC0", readme)
        self.assertIn("do **not** ship", readme)


if __name__ == "__main__":
    unittest.main()
