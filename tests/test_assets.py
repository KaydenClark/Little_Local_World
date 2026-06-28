import unittest

from agent_town.assets import load_colony_manifest


class ColonyAssetManifestTests(unittest.TestCase):
    def test_manifest_points_to_colony_runtime_sprites(self):
        manifest = load_colony_manifest()

        self.assertEqual(manifest.tile_size, 25)
        self.assertTrue(manifest.directory.is_dir())
        for name in ("grass", "dirt", "pavement", "tree", "house", "house2", "house3"):
            with self.subTest(sprite=name):
                self.assertTrue(manifest.path(name).is_file())

    def test_colony_pawn_sprite_set_has_enough_variety_for_seed_colony(self):
        manifest = load_colony_manifest()

        self.assertGreaterEqual(len(list(manifest.directory.glob("pawn_*.png"))), 12)

    def test_colony_asset_notes_record_provenance_and_suspect_assets(self):
        readme = (load_colony_manifest().directory / "README.md").read_text(encoding="utf-8")

        self.assertIn("Tiny Characters Set", readme)
        self.assertIn("CC0", readme)
        self.assertIn("do **not** ship", readme)


if __name__ == "__main__":
    unittest.main()
