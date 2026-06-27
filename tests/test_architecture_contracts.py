import unittest

from agent_town.contracts import (
    ModelProfile,
    PlannerRequest,
    PlannerResult,
    RenderSnapshot,
    ReplayEvent,
    SimulationSystem,
    WorldState,
)
from agent_town.core import create_default_simulation, simulation_from_state
from agent_town.navigation import DirectPathfinder


class ArchitectureContractTests(unittest.TestCase):
    def test_simulation_can_emit_and_restore_serializable_world_state(self):
        sim = create_default_simulation()
        sim.suggest("mira", "Go study at Archive Library")
        sim.step(0.1)
        sim.agents["mira"].remember(sim.tick, "Mira checked the town map.")

        state = sim.snapshot()
        restored = simulation_from_state(state)

        self.assertIsInstance(state, WorldState)
        self.assertEqual(restored.tick, sim.tick)
        self.assertEqual(restored.elapsed, sim.elapsed)
        self.assertEqual(restored.agents["mira"].destination, sim.agents["mira"].destination)
        self.assertEqual(restored.agents["mira"].memories[-1].text, "Mira checked the town map.")
        self.assertEqual(restored.events[-1].text, sim.events[-1].text)

    def test_replay_events_record_mutating_world_events(self):
        sim = create_default_simulation()

        sim.suggest("mira", "Go study at Archive Library")
        events = sim.drain_events()

        self.assertTrue(events)
        self.assertIsInstance(events[-1], ReplayEvent)
        self.assertEqual(events[-1].kind, "town_feed")
        self.assertIn("Suggestion queued", events[-1].payload["text"])
        self.assertTrue(sim.replay_log)

    def test_planning_and_model_contracts_are_explicit(self):
        sim = create_default_simulation()
        request = PlannerRequest(agent_id="mira", world=sim.snapshot(), context={"reason": "test"})
        result = PlannerResult(agent_id="mira", destination="Town Square", intent="check the crowd")
        model = ModelProfile(
            name="gemma-4-e4b",
            tier="local-small",
            max_context_tokens=4096,
            expected_ram_gb=6.0,
            expected_vram_gb=4.0,
            concurrency=1,
            notes="prototype planning",
        )
        render = RenderSnapshot(world=request.world, selected_agent_id="mira")

        self.assertEqual(request.agent_id, result.agent_id)
        self.assertEqual(model.tier, "local-small")
        self.assertEqual(render.selected_agent_id, "mira")

    def test_simulation_system_protocol_accepts_step_implementations(self):
        class DummySystem:
            name = "dummy"

            def step(self, world, dt):
                return (ReplayEvent(tick=world.tick, elapsed=world.elapsed, kind="dummy", payload={"dt": dt}),)

        sim = create_default_simulation()
        system: SimulationSystem = DummySystem()

        events = tuple(system.step(sim.snapshot(), 0.5))

        self.assertEqual(events[0].payload["dt"], 0.5)

    def test_direct_pathfinder_provides_replaceable_pathfinding_interface(self):
        pathfinder = DirectPathfinder()

        result = pathfinder.find_path((0, 0), (10, 15))

        self.assertEqual(result.waypoints, ((0, 0), (10, 15)))
        self.assertEqual(result.cost, 25)


if __name__ == "__main__":
    unittest.main()
