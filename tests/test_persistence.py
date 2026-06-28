import tempfile
import unittest
from pathlib import Path

from agent_town.core import DecisionResult, create_default_simulation
from agent_town.persistence import SQLiteSimulationStore


class SQLiteSimulationStoreTests(unittest.TestCase):
    def test_snapshot_round_trips_simulation_state(self):
        sim = create_default_simulation()
        sim.step(0.5)
        sim.apply_decision(
            "mira",
            DecisionResult(
                destination="Archive Library",
                intent="compare notes",
                speech="I should check the archives.",
                memory="Mira made a library plan.",
                relationship_target="orin",
                relationship_effect=0.04,
            ),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteSimulationStore(Path(temp_dir) / "town.sqlite3")
            store.save_snapshot(sim, label="test")

            loaded = store.load_snapshot(label="test")

        self.assertEqual(loaded.tick, sim.tick)
        self.assertEqual(loaded.elapsed, sim.elapsed)
        self.assertEqual(loaded.events[-1].text, sim.events[-1].text)
        self.assertEqual(loaded.agents["mira"].destination, "Archive Library")
        self.assertEqual(loaded.agents["mira"].memories[-1].text, "Mira made a library plan.")
        self.assertAlmostEqual(loaded.agents["mira"].relationships["orin"], 0.34)

    def test_event_log_replays_from_saved_snapshot(self):
        sim = create_default_simulation()
        sim.record_event("A bell rang in the square.")

        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteSimulationStore(Path(temp_dir) / "town.sqlite3")
            store.save_snapshot(sim, label="latest")

            events = store.load_event_log()

        self.assertGreaterEqual(len(events), 2)
        self.assertEqual(events[-1].text, "A bell rang in the square.")
        self.assertEqual(events[-1].tick, sim.tick)

    def test_loaded_snapshot_continues_deterministically(self):
        sim = create_default_simulation()
        for _ in range(10):
            sim.step(0.25)

        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteSimulationStore(Path(temp_dir) / "town.sqlite3")
            store.save_snapshot(sim, label="latest")
            loaded = store.load_snapshot(label="latest")

        for _ in range(30):
            sim.step(0.25)
            loaded.step(0.25)

        self.assertEqual(loaded.tick, sim.tick)
        self.assertEqual(loaded.events[-5:], sim.events[-5:])
        self.assertAlmostEqual(loaded.agents["mira"].x, sim.agents["mira"].x)
        self.assertAlmostEqual(loaded.agents["mira"].y, sim.agents["mira"].y)


if __name__ == "__main__":
    unittest.main()
