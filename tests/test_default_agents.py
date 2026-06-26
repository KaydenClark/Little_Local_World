import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from agent_town.assets import load_kenney_manifest
from agent_town.core import create_default_simulation

AGENT_IDS = ["mira", "sol", "juno", "tess", "orin", "vale", "rhea", "pax", "ivo", "nia"]


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


class DefaultAgentRosterTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((10, 10))
        self.sim = create_default_simulation()

    def tearDown(self):
        pygame.quit()

    def test_roster_contains_exactly_the_ten_named_agents(self):
        self.assertEqual(sorted(self.sim.agents), sorted(AGENT_IDS))

    def test_each_agent_only_prefers_real_places(self):
        # home/workplace are coerced to a valid location by _validate_initial_state
        # (covered in test_core), but preferred_places is never validated, so a
        # typo there can only be caught here.
        for agent_id in AGENT_IDS:
            with self.subTest(agent=agent_id):
                agent = self.sim.agents[agent_id]
                for place in agent.preferred_places:
                    self.assertIn(place, self.sim.locations)

    def test_each_agent_has_traits_and_a_distinct_color(self):
        seen_colors = set()
        for agent_id in AGENT_IDS:
            with self.subTest(agent=agent_id):
                agent = self.sim.agents[agent_id]
                self.assertTrue(agent.traits)
                self.assertNotIn(agent.color, seen_colors)
                seen_colors.add(agent.color)

    def test_each_agent_sprite_index_is_unique(self):
        indices = [self.sim.agents[agent_id].sprite_index for agent_id in AGENT_IDS]
        self.assertEqual(len(indices), len(set(indices)))

    def test_each_agent_sprite_renders_a_nonblank_tile(self):
        manifest = load_kenney_manifest()
        sheet = pygame.image.load(str(manifest.characters_path)).convert_alpha()
        for agent_id in AGENT_IDS:
            with self.subTest(agent=agent_id):
                agent = self.sim.agents[agent_id]
                self.assertTrue(
                    _tile_nonblank(sheet, agent.sprite_index, manifest.tile_size, manifest.margin),
                    f"{agent.name}'s sprite_index {agent.sprite_index} renders a blank tile",
                )


if __name__ == "__main__":
    unittest.main()
