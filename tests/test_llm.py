import os
import time
import unittest
from unittest.mock import patch

from agent_town.core import create_default_simulation
from agent_town.llm import LLMClientError, LLMDecisionScheduler, LocalLLMClient, build_decision_context


class LocalLLMClientTests(unittest.TestCase):
    def test_adapter_parses_successful_chat_completion(self):
        sim = create_default_simulation()

        def fake_post(payload, timeout):
            self.assertEqual(payload["model"], "gemma-4-e4b-it")
            self.assertEqual(payload["response_format"]["type"], "json_schema")
            schema = payload["response_format"]["json_schema"]["schema"]
            self.assertIn("destination", schema["required"])
            self.assertIn("intent", schema["required"])
            self.assertLessEqual(payload["max_tokens"], 220)
            return {
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"destination":"Archive Library",'
                                '"intent":"compare town rumors with old notes",'
                                '"speech":"I should ask Orin about this.",'
                                '"memory":"Mira formed a library plan.",'
                                '"relationship_target":"orin",'
                                '"relationship_effect":0.03}'
                            )
                        }
                    }
                ]
            }

        client = LocalLLMClient(
            model="gemma-4-e4b-it",
            base_url="http://localhost:1234/v1",
            http_post=fake_post,
        )

        decision = client.request_decision(build_decision_context(sim, "mira"))

        self.assertEqual(decision.destination, "Archive Library")
        self.assertEqual(decision.relationship_target, "orin")
        self.assertAlmostEqual(decision.relationship_effect, 0.03)

    def test_from_env_discovers_local_chat_model_when_model_is_unset(self):
        with patch.dict(
            os.environ,
            {
                "AGENT_TOWN_LLM_BASE_URL": "http://localhost:1234/v1",
                "AGENT_TOWN_LLM_TIMEOUT": "4",
            },
            clear=True,
        ):
            client = LocalLLMClient.from_env(
                model_discovery=lambda base_url, timeout: "google/gemma-4-e4b"
            )

        self.assertTrue(client.enabled)
        self.assertEqual(client.model, "google/gemma-4-e4b")
        self.assertEqual(client.base_url, "http://localhost:1234/v1")

    def test_from_env_model_setting_overrides_discovery(self):
        discovered = []

        def discovery(base_url, timeout):
            discovered.append(base_url)
            return "google/gemma-4-e4b"

        with patch.dict(
            os.environ,
            {
                "AGENT_TOWN_LLM_MODEL": "qwen/qwen3.5-9b",
                "AGENT_TOWN_LLM_BASE_URL": "http://localhost:1234/v1",
            },
            clear=True,
        ):
            client = LocalLLMClient.from_env(model_discovery=discovery)

        self.assertEqual(client.model, "qwen/qwen3.5-9b")
        self.assertEqual(discovered, [])

    def test_from_env_stays_disabled_when_discovery_fails(self):
        def discovery(base_url, timeout):
            raise LLMClientError("no local server")

        with patch.dict(os.environ, {}, clear=True):
            client = LocalLLMClient.from_env(model_discovery=discovery)

        self.assertFalse(client.enabled)

    def test_adapter_reports_timeout_as_client_error(self):
        def fake_post(payload, timeout):
            raise TimeoutError("request took too long")

        client = LocalLLMClient(
            model="gemma-4-e4b-it",
            base_url="http://localhost:1234/v1",
            http_post=fake_post,
            timeout=0.01,
        )

        with self.assertRaisesRegex(LLMClientError, "timed out"):
            client.request_decision(build_decision_context(create_default_simulation(), "mira"))

    def test_adapter_rejects_malformed_json(self):
        def fake_post(payload, timeout):
            return {"choices": [{"message": {"content": "not json"}}]}

        client = LocalLLMClient(
            model="gemma-4-e4b-it",
            base_url="http://localhost:1234/v1",
            http_post=fake_post,
        )

        with self.assertRaisesRegex(LLMClientError, "valid JSON"):
            client.request_decision(build_decision_context(create_default_simulation(), "mira"))


class LLMDecisionSchedulerTests(unittest.TestCase):
    def test_scheduler_does_not_block_simulation_step(self):
        sim = create_default_simulation()
        calls = []

        def slow_post(payload, timeout):
            calls.append(payload)
            time.sleep(0.2)
            return {
                "choices": [
                    {
                        "message": {
                            "content": '{"destination":"Town Square","intent":"check the square"}'
                        }
                    }
                ]
            }

        scheduler = LLMDecisionScheduler(
            LocalLLMClient(
                model="gemma-4-e4b-it",
                base_url="http://localhost:1234/v1",
                http_post=slow_post,
            ),
            global_interval=0.0,
            agent_interval=0.0,
        )

        start = time.perf_counter()
        scheduler.update(sim)
        elapsed = time.perf_counter() - start

        scheduler.shutdown(wait=True)
        self.assertLess(elapsed, 0.05)
        self.assertEqual(len(calls), 1)

    def test_scheduler_keeps_one_request_in_flight(self):
        sim = create_default_simulation()
        calls = []

        def slow_post(payload, timeout):
            calls.append(payload)
            time.sleep(0.2)
            return {
                "choices": [
                    {
                        "message": {
                            "content": '{"destination":"Town Square","intent":"check the square"}'
                        }
                    }
                ]
            }

        scheduler = LLMDecisionScheduler(
            LocalLLMClient(
                model="gemma-4-e4b-it",
                base_url="http://localhost:1234/v1",
                http_post=slow_post,
            ),
            global_interval=0.0,
            agent_interval=0.0,
        )

        scheduler.update(sim)
        deadline = time.perf_counter() + 0.1
        while not calls and time.perf_counter() < deadline:
            time.sleep(0.005)
        scheduler.update(sim)

        scheduler.shutdown(wait=True)
        self.assertEqual(len(calls), 1)

    def test_scheduler_falls_back_when_model_is_offline(self):
        sim = create_default_simulation()
        original_destination = sim.agents["mira"].destination

        def offline_post(payload, timeout):
            raise ConnectionError("server refused connection")

        scheduler = LLMDecisionScheduler(
            LocalLLMClient(
                model="gemma-4-e4b-it",
                base_url="http://localhost:1234/v1",
                http_post=offline_post,
            ),
            global_interval=0.0,
            agent_interval=0.0,
        )

        scheduler.update(sim)
        deadline = time.perf_counter() + 0.5
        while scheduler.status.state == "thinking" and time.perf_counter() < deadline:
            scheduler.update(sim)
            time.sleep(0.01)

        scheduler.shutdown(wait=True)
        self.assertIn(scheduler.status.state, {"offline", "invalid"})
        self.assertEqual(sim.agents["mira"].destination, original_destination)


if __name__ == "__main__":
    unittest.main()
