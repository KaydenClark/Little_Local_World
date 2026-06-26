from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
import json
import os
import socket
import time
from typing import Any, Callable
import urllib.error
import urllib.request

from .core import Agent, DecisionResult, Simulation


DEFAULT_BASE_URL = "http://localhost:1234/v1"
DEFAULT_TIMEOUT = 4.0
DEFAULT_MAX_TOKENS = 180

HttpPost = Callable[[dict[str, Any], float], dict[str, Any]]


class LLMClientError(RuntimeError):
    pass


@dataclass
class LLMRuntimeStatus:
    enabled: bool
    state: str
    model: str = ""
    base_url: str = DEFAULT_BASE_URL
    last_error: str = ""
    last_latency: float = 0.0
    in_flight_agent_id: str = ""
    last_agent_id: str = ""


class LocalLLMClient:
    def __init__(
        self,
        *,
        model: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        http_post: HttpPost | None = None,
    ) -> None:
        self.model = (model or "").strip()
        self.base_url = base_url.rstrip("/")
        self.timeout = max(0.1, float(timeout))
        self.max_tokens = max(32, min(int(max_tokens), 400))
        self._http_post = http_post or self._default_http_post

    @classmethod
    def from_env(cls) -> LocalLLMClient:
        model = os.environ.get("AGENT_TOWN_LLM_MODEL", "").strip()
        base_url = os.environ.get("AGENT_TOWN_LLM_BASE_URL", DEFAULT_BASE_URL).strip() or DEFAULT_BASE_URL
        timeout = _float_env("AGENT_TOWN_LLM_TIMEOUT", DEFAULT_TIMEOUT)
        max_tokens = _int_env("AGENT_TOWN_LLM_MAX_TOKENS", DEFAULT_MAX_TOKENS)
        return cls(model=model or None, base_url=base_url, timeout=timeout, max_tokens=max_tokens)

    @property
    def enabled(self) -> bool:
        return bool(self.model)

    def request_decision(self, context: dict[str, Any]) -> DecisionResult:
        if not self.enabled:
            raise LLMClientError("LLM disabled; set AGENT_TOWN_LLM_MODEL to enable local planning")

        payload = self._build_payload(context)
        try:
            response = self._http_post(payload, self.timeout)
        except (TimeoutError, socket.timeout) as exc:
            raise LLMClientError("LLM request timed out") from exc
        except (ConnectionError, OSError, urllib.error.URLError) as exc:
            raise LLMClientError(f"LLM connection failed: {exc}") from exc

        return parse_decision_response(response)

    def _build_payload(self, context: dict[str, Any]) -> dict[str, Any]:
        system = (
            "You are the local planning layer for a desktop town simulation. "
            "Choose one compact, plausible next action for the selected agent. "
            "Return valid JSON only. Do not include markdown or chain-of-thought."
        )
        user = {
            "context": context,
            "schema": {
                "destination": "one exact name from context.locations",
                "intent": "short motive, 120 chars max",
                "speech": "optional in-character line, 140 chars max",
                "memory": "optional memory note, 160 chars max",
                "relationship_target": "optional agent id from context.other_agents",
                "relationship_effect": "optional number from -0.1 to 0.1",
            },
        }
        return {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user, separators=(",", ":"))},
            ],
            "temperature": 0.6,
            "top_p": 0.85,
            "max_tokens": self.max_tokens,
            "stream": False,
            "response_format": {"type": "json_object"},
        }

    def _default_http_post(self, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as exc:
            raise LLMClientError("LLM server returned invalid JSON") from exc
        if not isinstance(parsed, dict):
            raise LLMClientError("LLM server response must be a JSON object")
        return parsed


class LLMDecisionScheduler:
    def __init__(
        self,
        client: LocalLLMClient | None = None,
        *,
        global_interval: float = 10.0,
        agent_interval: float = 75.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.client = client or LocalLLMClient.from_env()
        self.global_interval = max(0.0, global_interval)
        self.agent_interval = max(0.0, agent_interval)
        self.clock = clock
        self.status = LLMRuntimeStatus(
            enabled=self.client.enabled,
            state="idle" if self.client.enabled else "disabled",
            model=self.client.model,
            base_url=self.client.base_url,
        )
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="agent-town-llm")
        self._future: Future[tuple[str, DecisionResult, float]] | None = None
        self._next_global_time = 0.0

    def update(self, sim: Simulation) -> None:
        if self._finish_if_ready(sim):
            return
        if not self.client.enabled:
            self.status.state = "disabled"
            self.status.enabled = False
            return
        if self._future is not None:
            self.status.state = "thinking"
            return

        now = self.clock()
        if now < self._next_global_time:
            return

        agent = self._select_due_agent(sim)
        if agent is None:
            self.status.state = "idle"
            return

        context = build_decision_context(sim, agent.id)
        self.status = LLMRuntimeStatus(
            enabled=True,
            state="thinking",
            model=self.client.model,
            base_url=self.client.base_url,
            in_flight_agent_id=agent.id,
            last_latency=self.status.last_latency,
            last_agent_id=self.status.last_agent_id,
        )
        self._future = self._executor.submit(self._request_with_latency, agent.id, context)

    def shutdown(self, *, wait: bool = False) -> None:
        self._executor.shutdown(wait=wait, cancel_futures=not wait)

    def _select_due_agent(self, sim: Simulation) -> Agent | None:
        due_agents = [
            agent
            for agent in sim.agents.values()
            if sim.elapsed - agent.last_llm_turn >= self.agent_interval
        ]
        if not due_agents:
            return None
        return min(due_agents, key=lambda agent: (agent.last_llm_turn, agent.id))

    def _request_with_latency(self, agent_id: str, context: dict[str, Any]) -> tuple[str, DecisionResult, float]:
        start = self.clock()
        decision = self.client.request_decision(context)
        return agent_id, decision, self.clock() - start

    def _finish_if_ready(self, sim: Simulation) -> bool:
        if self._future is None or not self._future.done():
            return False

        now = self.clock()
        future = self._future
        self._future = None
        self._next_global_time = now + self.global_interval

        try:
            agent_id, decision, latency = future.result()
            sim.apply_decision(agent_id, decision)
        except LLMClientError as exc:
            self.status.state = _error_state(str(exc))
            self.status.last_error = str(exc)
            self.status.in_flight_agent_id = ""
            return True
        except (KeyError, ValueError, TypeError) as exc:
            self.status.state = "invalid"
            self.status.last_error = str(exc)
            self.status.in_flight_agent_id = ""
            return True

        self.status.state = "idle"
        self.status.last_error = ""
        self.status.last_latency = latency
        self.status.last_agent_id = agent_id
        self.status.in_flight_agent_id = ""
        return True


def build_decision_context(sim: Simulation, agent_id: str) -> dict[str, Any]:
    if agent_id not in sim.agents:
        raise KeyError(f"Unknown agent: {agent_id}")

    agent = sim.agents[agent_id]
    other_agents = [
        {
            "id": other.id,
            "name": other.name,
            "location": sim.agent_location_name(other),
            "relationship": agent.relationships.get(other.id, 0.3),
            "relationship_label": sim.relationship_label(agent, other.id),
        }
        for other in sim.agents.values()
        if other.id != agent.id
    ]
    return {
        "tick": sim.tick,
        "elapsed": round(sim.elapsed, 1),
        "locations": [
            {"name": location.name, "kind": location.kind}
            for location in sim.locations.values()
        ],
        "agent": {
            "id": agent.id,
            "name": agent.name,
            "traits": list(agent.traits),
            "location": sim.agent_location_name(agent),
            "destination": agent.destination,
            "goal": agent.goal,
            "activity": agent.activity,
            "needs": {
                "energy": round(agent.energy, 2),
                "hunger": round(agent.hunger, 2),
                "social": round(agent.social, 2),
                "curiosity": round(agent.curiosity, 2),
            },
            "recent_memories": [memory.text for memory in agent.memories[-5:]],
            "pending_suggestions": agent.suggestions[-2:],
        },
        "other_agents": other_agents,
        "recent_events": [event.text for event in sim.events[-6:]],
    }


def parse_decision_response(response: dict[str, Any]) -> DecisionResult:
    content = _extract_content(response)
    data = _parse_json_object(content)

    destination = _clean_value(data.get("destination"), 80)
    intent = _clean_value(data.get("intent"), 120)
    if not destination or not intent:
        raise LLMClientError("LLM decision must include destination and intent")

    relationship_effect = data.get("relationship_effect", 0.0)
    try:
        effect = max(-0.1, min(0.1, float(relationship_effect)))
    except (TypeError, ValueError) as exc:
        raise LLMClientError("LLM relationship_effect must be numeric") from exc

    return DecisionResult(
        destination=destination,
        intent=intent,
        speech=_clean_value(data.get("speech"), 140),
        memory=_clean_value(data.get("memory"), 160),
        relationship_target=_clean_value(data.get("relationship_target"), 40),
        relationship_effect=effect,
    )


def _extract_content(response: dict[str, Any]) -> str:
    try:
        content = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMClientError("LLM response missing choices[0].message.content") from exc
    if not isinstance(content, str):
        raise LLMClientError("LLM response content must be text")
    return content


def _parse_json_object(content: str) -> dict[str, Any]:
    text = content.strip()
    if "</think>" in text:
        text = text.split("</think>", 1)[1].strip()
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise LLMClientError("LLM response must contain valid JSON object")
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise LLMClientError("LLM response must contain valid JSON object") from exc
    if not isinstance(parsed, dict):
        raise LLMClientError("LLM response must contain a JSON object")
    return parsed


def _clean_value(value: Any, limit: int) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())[:limit]


def _error_state(message: str) -> str:
    lowered = message.lower()
    if any(word in lowered for word in ("connection", "timed out", "refused", "unreachable")):
        return "offline"
    return "invalid"


def _float_env(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default
