import unittest

from agent_town.core import Agent, DecisionResult, Location, Simulation, create_default_simulation


class SimulationTests(unittest.TestCase):
    def test_agent_moves_toward_destination(self):
        sim = Simulation(
            [Location("Home", 100, 0, "home", 10)],
            [Agent("a", "Ari", 0, 0, (255, 255, 255), (), destination="Home")],
        )

        sim.step(1.0)

        agent = sim.agents["a"]
        self.assertGreater(agent.x, 0)
        self.assertEqual(agent.y, 0)
        self.assertEqual(agent.activity, "walking to Home")

    def test_suggestion_can_send_agent_to_named_location(self):
        sim = create_default_simulation()
        agent = sim.agents["mira"]
        agent.x = sim.locations["Town Square"].x
        agent.y = sim.locations["Town Square"].y

        sim.suggest("mira", "Go study at Archive Library")
        sim.step(0.1)

        self.assertEqual(agent.destination, "Archive Library")
        self.assertIn("try suggestion", agent.goal)
        self.assertEqual(agent.suggestions, [])

    def test_agents_remember_conversation_when_at_same_location(self):
        sim = Simulation(
            [Location("Square", 100, 100, "social", 80)],
            [
                Agent("a", "Ari", 100, 100, (255, 255, 255), (), destination="Square"),
                Agent("b", "Bea", 105, 100, (255, 255, 255), (), destination="Square"),
            ],
            seed=2,
        )

        sim.step(0.1)

        self.assertTrue(sim.agents["a"].memories)
        self.assertTrue(sim.agents["b"].memories)
        self.assertIn("Talked with Bea", sim.agents["a"].memories[-1].text)
        self.assertIn("Talked with Ari", sim.agents["b"].memories[-1].text)

    def test_unknown_agent_suggestion_fails_clearly(self):
        sim = create_default_simulation()

        with self.assertRaisesRegex(KeyError, "Unknown agent"):
            sim.suggest("missing", "go somewhere")

    def test_default_simulation_supports_ten_agents(self):
        sim = create_default_simulation()

        self.assertEqual(len(sim.agents), 10)
        for agent in sim.agents.values():
            self.assertIn(agent.destination, sim.locations)

    def test_llm_decision_validates_destination_before_mutating(self):
        sim = create_default_simulation()
        original_destination = sim.agents["mira"].destination

        with self.assertRaisesRegex(ValueError, "Unknown destination"):
            sim.apply_decision(
                "mira",
                DecisionResult(destination="Moon Base", intent="visit somewhere impossible"),
            )

        self.assertEqual(sim.agents["mira"].destination, original_destination)

    def test_ten_agent_simulation_runs_without_llm_access(self):
        sim = create_default_simulation()

        for _ in range(240):
            sim.step(0.5)

        self.assertEqual(len(sim.agents), 10)
        self.assertTrue(sim.events)
        for agent in sim.agents.values():
            self.assertIn(agent.destination, sim.locations)
            self.assertGreaterEqual(agent.x, 0)
            self.assertLessEqual(agent.x, 2400)
            self.assertGreaterEqual(agent.y, 0)
            self.assertLessEqual(agent.y, 1600)


if __name__ == "__main__":
    unittest.main()
