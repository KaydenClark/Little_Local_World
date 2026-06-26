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

    def test_simulation_requires_at_least_one_location(self):
        with self.assertRaisesRegex(ValueError, "at least one location"):
            Simulation([], [])

    def test_construction_rejects_an_agent_pointing_at_an_unknown_destination(self):
        with self.assertRaisesRegex(ValueError, "Unknown destination"):
            Simulation(
                [Location("Home", 0, 0, "home", 10)],
                [Agent("a", "Ari", 0, 0, (1, 2, 3), (), destination="Nowhere")],
            )

    def test_construction_coerces_unknown_home_and_workplace_to_destination(self):
        sim = Simulation(
            [Location("Home", 0, 0, "home", 10)],
            [
                Agent(
                    "a",
                    "Ari",
                    0,
                    0,
                    (1, 2, 3),
                    (),
                    destination="Home",
                    home="Missing Home",
                    workplace="Missing Job",
                )
            ],
        )

        agent = sim.agents["a"]
        self.assertEqual(agent.home, "Home")
        self.assertEqual(agent.workplace, "Home")

    def test_apply_decision_moves_agent_and_records_speech_as_an_event(self):
        sim = create_default_simulation()

        sim.apply_decision(
            "mira",
            DecisionResult(
                destination="Greenhouse Cafe",
                intent="grab a snack",
                speech="I am hungry.",
            ),
        )

        agent = sim.agents["mira"]
        self.assertEqual(agent.destination, "Greenhouse Cafe")
        self.assertEqual(agent.goal, "grab a snack")
        self.assertEqual(agent.last_speech, "I am hungry.")
        self.assertTrue(any("I am hungry." in event.text for event in sim.events))

    def test_llm_decision_validates_destination_before_mutating(self):
        sim = create_default_simulation()
        original_destination = sim.agents["mira"].destination

        with self.assertRaisesRegex(ValueError, "Unknown destination"):
            sim.apply_decision(
                "mira",
                DecisionResult(destination="Moon Base", intent="visit somewhere impossible"),
            )

        self.assertEqual(sim.agents["mira"].destination, original_destination)

    def test_relationship_label_buckets_by_value(self):
        sim = create_default_simulation()
        agent = sim.agents["mira"]

        agent.relationships["sol"] = 0.8
        self.assertEqual(sim.relationship_label(agent, "sol"), "close")
        agent.relationships["sol"] = 0.6
        self.assertEqual(sim.relationship_label(agent, "sol"), "friendly")
        agent.relationships["sol"] = 0.1
        self.assertEqual(sim.relationship_label(agent, "sol"), "strained")
        self.assertEqual(sim.relationship_label(agent, "unknown-agent"), "distant")

    def test_apply_decision_rejects_relationship_target_equal_to_actor(self):
        sim = create_default_simulation()

        with self.assertRaisesRegex(ValueError, "cannot be the acting agent"):
            sim.apply_decision(
                "mira",
                DecisionResult(destination="Town Square", intent="reflect", relationship_target="mira"),
            )

    def test_apply_decision_clamps_relationship_effect_to_allowed_range(self):
        sim = create_default_simulation()

        sim.apply_decision(
            "mira",
            DecisionResult(
                destination="Town Square",
                intent="check in on sol",
                relationship_target="sol",
                relationship_effect=5.0,
            ),
        )

        self.assertLessEqual(sim.agents["mira"].relationships["sol"], 1.0)

    def test_apply_decision_rejects_empty_intent(self):
        sim = create_default_simulation()

        with self.assertRaisesRegex(ValueError, "intent is required"):
            sim.apply_decision("mira", DecisionResult(destination="Town Square", intent=""))

    def test_event_log_trims_to_max_length(self):
        sim = create_default_simulation()

        for index in range(100):
            sim.record_event(f"event {index}")

        self.assertEqual(len(sim.events), 80)
        self.assertEqual(sim.events[-1].text, "event 99")

    def test_agent_memory_trims_to_requested_limit(self):
        sim = create_default_simulation()
        agent = sim.agents["mira"]

        for index in range(20):
            agent.remember(index, f"memory {index}", limit=5)

        self.assertEqual(len(agent.memories), 5)
        self.assertEqual(agent.memories[-1].text, "memory 19")

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
