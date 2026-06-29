import unittest

import agent_town
from agent_town.core import FactionState


class PackageRuntimeTests(unittest.TestCase):
    def test_package_exports_civilization_runtime_not_legacy_simulation(self):
        self.assertEqual(agent_town.__all__, ["FactionState", "create_default_civilization"])
        self.assertIs(agent_town.FactionState, FactionState)

        state = agent_town.create_default_civilization()

        self.assertIsInstance(state, FactionState)
        self.assertEqual(len(state.pawns), 12)


if __name__ == "__main__":
    unittest.main()
