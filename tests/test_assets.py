import unittest
import zipfile
from pathlib import Path

from agent_town.assets import load_kenney_manifest
from agent_town.app import LOCATION_FOOTPRINTS, SCENERY_STAMPS, TERRAIN_TILE_INDEXES


PROJECT_ROOT = Path(__file__).resolve().parents[1]
# Source asset zips live alongside the bundled sprites under the package.
ASSETS_DIR = PROJECT_ROOT / "src" / "agent_town" / "assets"


SOURCE_ASSETS = {
    "characters_path": ("kenney_roguelike-characters.zip", "Spritesheet/roguelikeChar_transparent.png"),
    "tiles_path": ("kenney_roguelike-rpg-pack.zip", "Spritesheet/roguelikeSheet_transparent.png"),
    "emotes_path": ("kenney_emotes-pack.zip", "Spritesheets/pixel_style1.png"),
    "emotes_xml_path": ("kenney_emotes-pack.zip", "Spritesheets/pixel_style1.xml"),
}


class KenneyAssetTests(unittest.TestCase):
    def test_manifest_points_to_selected_kenney_spritesheets(self):
        manifest = load_kenney_manifest()

        self.assertEqual(manifest.tile_size, 16)
        self.assertEqual(manifest.margin, 1)
        self.assertTrue(manifest.characters_path.is_file())
        self.assertTrue(manifest.tiles_path.is_file())
        self.assertTrue(manifest.emotes_path.is_file())
        self.assertTrue(manifest.emotes_xml_path.is_file())

    def test_selected_assets_match_source_zip_entries(self):
        manifest = load_kenney_manifest()

        for manifest_attr, (zip_name, entry_name) in SOURCE_ASSETS.items():
            with self.subTest(asset=manifest_attr):
                asset_path = getattr(manifest, manifest_attr)
                with zipfile.ZipFile(ASSETS_DIR / zip_name) as archive:
                    expected = archive.read(entry_name)

                self.assertEqual(asset_path.read_bytes(), expected)

    def test_asset_prepare_script_exists(self):
        self.assertTrue((PROJECT_ROOT / "scripts" / "prepare-kenney-assets.ps1").is_file())

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
