import tempfile
import unittest
from pathlib import Path

from agent_town.core import create_default_simulation
from agent_town.persistence import load_simulation, load_snapshot, save_snapshot


class PersistenceTests(unittest.TestCase):
    def test_sqlite_snapshot_round_trips_simulation_state(self):
        sim = create_default_simulation()
        sim.suggest("mira", "Go study at Archive Library")
        sim.step(0.1)
        sim.agents["mira"].remember(sim.tick, "Mira tested persistence.")

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "town.db"
            snapshot_id = save_snapshot(db_path, sim)
            state = load_snapshot(db_path, snapshot_id)
            restored = load_simulation(db_path, snapshot_id)

        self.assertEqual(state.tick, sim.tick)
        self.assertEqual(restored.agents["mira"].destination, sim.agents["mira"].destination)
        self.assertEqual(restored.agents["mira"].memories[-1].text, "Mira tested persistence.")
        self.assertEqual(restored.events[-1].text, sim.events[-1].text)

    def test_save_snapshot_rejects_empty_database_path(self):
        sim = create_default_simulation()

        with self.assertRaises(ValueError):
            save_snapshot("", sim)


if __name__ == "__main__":
    unittest.main()
