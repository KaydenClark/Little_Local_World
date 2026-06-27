import unittest

from agent_town.benchmarks import (
    BenchmarkResult,
    build_synthetic_simulation,
    evaluate_threshold,
    percentile,
    run_rule_agent_benchmark,
)


class BenchmarkHarnessTests(unittest.TestCase):
    def test_build_synthetic_simulation_creates_requested_agent_count(self):
        sim = build_synthetic_simulation(25)

        self.assertEqual(len(sim.agents), 25)

    def test_percentile_handles_small_samples(self):
        self.assertEqual(percentile([4.0], 95), 4.0)
        self.assertEqual(percentile([1.0, 2.0, 3.0, 4.0], 50), 2.5)

    def test_evaluate_threshold_marks_pass_and_failure(self):
        passed = evaluate_threshold("rule_agents", 1000, 7.5)
        failed = evaluate_threshold("rule_agents", 1000, 9.0)

        self.assertTrue(passed.passed)
        self.assertFalse(failed.passed)
        self.assertEqual(passed.threshold_ms, 8.0)

    def test_rule_agent_benchmark_returns_structured_result(self):
        result = run_rule_agent_benchmark(20, iterations=2)

        self.assertIsInstance(result, BenchmarkResult)
        self.assertEqual(result.name, "rule_agents")
        self.assertEqual(result.entity_count, 20)
        self.assertGreaterEqual(result.p95_ms, 0.0)


if __name__ == "__main__":
    unittest.main()
