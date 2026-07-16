import os
import unittest
from unittest.mock import patch

from agent_town.llm import LLMClientError, LocalLLMClient


class LocalLLMClientTests(unittest.TestCase):
    def test_complete_json_sends_schema_payload_and_parses_object(self):
        calls = []

        def fake_post(payload, timeout):
            calls.append((payload, timeout))
            return {"choices": [{"message": {"content": '{"actions":[]}'}}]}

        client = LocalLLMClient(
            model="gemma-4-e4b-it",
            base_url="http://localhost:1234/v1",
            http_post=fake_post,
        )

        result = client.complete_json(
            "system",
            {"civilization": {"day": 1}},
            schema={"type": "object", "properties": {"actions": {"type": "array"}}},
            name="civilization_actions",
        )

        payload, timeout = calls[0]
        self.assertEqual(result, {"actions": []})
        self.assertEqual(payload["model"], "gemma-4-e4b-it")
        self.assertEqual(payload["response_format"]["type"], "json_schema")
        self.assertEqual(payload["response_format"]["json_schema"]["name"], "civilization_actions")
        self.assertEqual(timeout, client.timeout)

    def test_complete_json_reports_timeout_as_client_error(self):
        def fake_post(payload, timeout):
            raise TimeoutError("request took too long")

        client = LocalLLMClient(model="gemma-4-e4b-it", http_post=fake_post, timeout=0.01)

        with self.assertRaisesRegex(LLMClientError, "timed out"):
            client.complete_json("system", {})

    def test_complete_json_rejects_malformed_json(self):
        def fake_post(payload, timeout):
            return {"choices": [{"message": {"content": "not json"}}]}

        client = LocalLLMClient(model="gemma-4-e4b-it", http_post=fake_post)

        with self.assertRaisesRegex(LLMClientError, "valid JSON"):
            client.complete_json("system", {})

    def test_complete_json_retries_once_after_malformed_json(self):
        responses = [
            {"choices": [{"message": {"content": '{"actions":['}}]},
            {"choices": [{"message": {"content": '{"actions":[]}'}}]},
        ]
        calls = []

        def fake_post(payload, timeout):
            calls.append(payload)
            return responses.pop(0)

        client = LocalLLMClient(model="gemma-4-e4b-it", http_post=fake_post)

        result = client.complete_json("system", {"civilization": {"day": 1}})

        self.assertEqual(result, {"actions": []})
        self.assertEqual(len(calls), 2)
        self.assertIn("Previous response was invalid JSON", calls[1]["messages"][-1]["content"])

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

    def test_from_env_uses_openai_api_key_as_bearer_auth(self):
        captured = []

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b'{"choices":[{"message":{"content":"{\\"actions\\":[]}"}}]}'

        def fake_urlopen(request, timeout):
            captured.append(request)
            return FakeResponse()

        with patch.dict(
            os.environ,
            {
                "AGENT_TOWN_LLM_MODEL": "gpt-5.4-mini",
                "AGENT_TOWN_LLM_BASE_URL": "https://api.openai.com/v1",
                "OPENAI_API_KEY": "test-secret",
            },
            clear=True,
        ), patch("urllib.request.urlopen", fake_urlopen):
            client = LocalLLMClient.from_env()
            result = client.complete_json("system", {})

        self.assertEqual(result, {"actions": []})
        self.assertEqual(captured[0].get_header("Authorization"), "Bearer test-secret")

    def test_openai_gpt5_chat_payload_uses_completion_token_limit(self):
        calls = []

        def fake_post(payload, timeout):
            calls.append(payload)
            return {"choices": [{"message": {"content": '{"actions":[]}'}}]}

        client = LocalLLMClient(
            model="gpt-5.4-mini",
            base_url="https://api.openai.com/v1",
            http_post=fake_post,
        )

        client.complete_json("system", {})

        self.assertEqual(calls[0]["max_completion_tokens"], client.max_tokens)
        self.assertNotIn("max_tokens", calls[0])


class DefaultsTests(unittest.TestCase):
    def test_loosened_defaults_for_local_4b_models(self):
        # Tuned up so a slow 4B model is not falsely recorded as dropped.
        from agent_town import llm

        self.assertEqual(llm.DEFAULT_TIMEOUT, 8.0)
        self.assertEqual(llm.DEFAULT_MAX_TOKENS, 320)


if __name__ == "__main__":
    unittest.main()
