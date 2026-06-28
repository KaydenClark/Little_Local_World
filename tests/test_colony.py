import unittest

from agent_town import colony, economy, engine
from agent_town.core import Good
from agent_town import pawns


class DefaultColonyTests(unittest.TestCase):
    def test_seeded_colony_is_well_formed(self):
        state = colony.create_default_colony()

        self.assertIsNotNone(state.grid)
        self.assertEqual(len(state.pawns), len(colony.STARTING_PAWNS))
        self.assertEqual(len(state.buildings), len(colony.STARTING_BUILDINGS))
        self.assertTrue(state.resource_nodes)
        # Every building sits on the grid.
        for building in state.buildings.values():
            self.assertTrue(state.grid.in_bounds(building.x, building.y))

    def test_seeded_colony_is_deterministic(self):
        first = colony.create_default_colony()
        second = colony.create_default_colony()

        self.assertEqual(
            [(b.kind, b.x, b.y) for b in first.buildings.values()],
            [(b.kind, b.x, b.y) for b in second.buildings.values()],
        )
        self.assertEqual(
            [(n.kind, n.x, n.y) for n in first.resource_nodes],
            [(n.kind, n.x, n.y) for n in second.resource_nodes],
        )

    def test_fallback_governor_sustains_the_rendered_colony(self):
        # The viewer's colony must survive autopilot like the I1 colony does.
        state = colony.create_default_colony()

        engine.run_days(state, days=3)

        self.assertGreaterEqual(economy.average_mood(state), 0.45)
        self.assertGreater(state.coin, 0)
        self.assertFalse([p for p in state.pawns.values() if p.state == pawns.STATE_WANDERING])
        # Pawns were assigned to building slots by the fallback governor.
        self.assertTrue(any(b.staffed_by for b in state.buildings.values()))
        # The wood and stone chains have no consumption sink, so positive stock
        # proves staffed buildings are producing under autopilot.
        stock = state.stockpile.counts
        self.assertGreater(stock.get(Good.STONE, 0), 0)
        self.assertGreater(stock.get(Good.LOGS, 0) + stock.get(Good.PLANKS, 0), 0)


if __name__ == "__main__":
    unittest.main()
