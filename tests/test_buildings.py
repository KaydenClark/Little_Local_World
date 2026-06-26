import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from agent_town.app import LOCATION_TILE_INDEX, App
from agent_town.assets import load_kenney_manifest
from agent_town.core import create_default_simulation

EXPECTED_LOCATIONS = {
    "Town Square": "social",
    "North Apartments": "home",
    "South Row Homes": "home",
    "Greenhouse Cafe": "food",
    "Archive Library": "knowledge",
    "Maker Hall": "work",
    "Riverside Park": "social",
    "Clinic Garden": "quiet",
}

PATH_ENDPOINTS = [
    ("Town Square", "North Apartments"),
    ("Town Square", "South Row Homes"),
    ("Town Square", "Greenhouse Cafe"),
    ("Town Square", "Archive Library"),
    ("Town Square", "Maker Hall"),
    ("Town Square", "Riverside Park"),
    ("Riverside Park", "Clinic Garden"),
]


def _tile_nonblank(sheet: pygame.Surface, index: int, tile_size: int, margin: int) -> bool:
    step = tile_size + margin
    columns = max(1, (sheet.get_width() + margin) // step)
    x = (index % columns) * step
    y = (index // columns) * step
    rect = pygame.Rect(x, y, tile_size, tile_size)
    if rect.right > sheet.get_width() or rect.bottom > sheet.get_height():
        return False
    sub = sheet.subsurface(rect)
    for px in range(tile_size):
        for py in range(tile_size):
            if sub.get_at((px, py))[3] > 0:
                return True
    return False


class DefaultBuildingTests(unittest.TestCase):
    def setUp(self):
        self.sim = create_default_simulation()

    def test_default_town_has_exactly_the_eight_named_buildings(self):
        self.assertEqual(set(self.sim.locations), set(EXPECTED_LOCATIONS))

    def test_each_building_has_the_expected_kind(self):
        for name, kind in EXPECTED_LOCATIONS.items():
            with self.subTest(building=name):
                self.assertEqual(self.sim.locations[name].kind, kind)

    def test_each_building_has_a_positive_radius_inside_the_world(self):
        for name, location in self.sim.locations.items():
            with self.subTest(building=name):
                self.assertGreater(location.radius, 0)
                self.assertGreaterEqual(location.x, 0)
                self.assertGreaterEqual(location.y, 0)

    def test_every_building_kind_maps_to_a_tile_index(self):
        for name, location in self.sim.locations.items():
            with self.subTest(building=name):
                self.assertIn(location.kind, LOCATION_TILE_INDEX)

    def test_every_building_kind_maps_to_a_draw_color(self):
        for name, location in self.sim.locations.items():
            with self.subTest(building=name):
                color = App._location_color(location)
                self.assertEqual(len(color), 3)
                for channel in color:
                    self.assertGreaterEqual(channel, 0)
                    self.assertLessEqual(channel, 255)

    def test_every_building_tile_sprite_is_nonblank(self):
        manifest = load_kenney_manifest()
        pygame.init()
        pygame.display.set_mode((10, 10))
        sheet = pygame.image.load(str(manifest.tiles_path)).convert_alpha()
        try:
            for kind, index in LOCATION_TILE_INDEX.items():
                with self.subTest(kind=kind):
                    self.assertTrue(
                        _tile_nonblank(sheet, index, manifest.tile_size, manifest.margin),
                        f"Tile index {index} for kind {kind!r} renders blank",
                    )
        finally:
            pygame.quit()

    def test_walking_paths_only_reference_real_buildings(self):
        for start_name, end_name in PATH_ENDPOINTS:
            with self.subTest(path=(start_name, end_name)):
                self.assertIn(start_name, self.sim.locations)
                self.assertIn(end_name, self.sim.locations)

    def test_every_building_is_reachable_by_at_least_one_agent_kind_need(self):
        kinds_present = {location.kind for location in self.sim.locations.values()}
        self.assertEqual(kinds_present, set(EXPECTED_LOCATIONS.values()))


if __name__ == "__main__":
    unittest.main()
