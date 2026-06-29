from __future__ import annotations

import json
import os
import socket
from typing import Any, Callable
import urllib.error
import urllib.request


DEFAULT_BASE_URL = "http://localhost:1234/v1"
DEFAULT_TIMEOUT = 4.0
DEFAULT_MAX_TOKENS = 180
DEFAULT_DISCOVERY_TIMEOUT = 0.75

HttpPost = Callable[[dict[str, Any], float], dict[str, Any]]
ModelDiscovery = Callable[[str, float], str]


class LLMClientError(RuntimeError):
    pass


class LocalLLMClient:
    """OpenAI-compatible local chat client used by the civilization governor."""

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
    def from_env(cls, *, model_discovery: ModelDiscovery | None = None) -> "LocalLLMClient":
        model = os.environ.get("AGENT_TOWN_LLM_MODEL", "").strip()
        base_url = os.environ.get("AGENT_TOWN_LLM_BASE_URL", DEFAULT_BASE_URL).strip() or DEFAULT_BASE_URL
        timeout = _float_env("AGENT_TOWN_LLM_TIMEOUT", DEFAULT_TIMEOUT)
        max_tokens = _int_env("AGENT_TOWN_LLM_MAX_TOKENS", DEFAULT_MAX_TOKENS)
        if not model and _bool_env("AGENT_TOWN_LLM_AUTO_DISCOVER", True):
            discovery = model_discovery or discover_local_model
            try:
                model = discovery(base_url, min(timeout, DEFAULT_DISCOVERY_TIMEOUT)).strip()
            except LLMClientError:
                model = ""
        return cls(model=model or None, base_url=base_url, timeout=timeout, max_tokens=max_tokens)

    @property
    def enabled(self) -> bool:
        return bool(self.model)

    def complete_json(
        self,
        system: str,
        user: Any,
        *,
        schema: dict[str, Any] | None = None,
        name: str = "response",
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        """Request a structured JSON object from a local chat model."""
        if not self.enabled:
            raise LLMClientError("LLM disabled; set AGENT_TOWN_LLM_MODEL to enable local planning")

        user_text = user if isinstance(user, str) else json.dumps(user, separators=(",", ":"))
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_text},
            ],
            "temperature": temperature,
            "top_p": 0.9,
            "max_tokens": self.max_tokens,
            "stream": False,
        }
        if schema is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": name, "schema": schema},
            }

        try:
            response = self._http_post(payload, self.timeout)
        except LLMClientError:
            raise
        except (TimeoutError, socket.timeout) as exc:
            raise LLMClientError("LLM request timed out") from exc
        except (ConnectionError, OSError, urllib.error.URLError) as exc:
            raise LLMClientError(f"LLM connection failed: {exc}") from exc

        return _parse_json_object(_extract_content(response))

    def _default_http_post(self, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = _http_error_detail(exc)
            message = f"LLM server rejected request ({exc.code} {exc.reason})"
            if detail:
                message = f"{message}: {detail}"
            raise LLMClientError(message) from exc
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as exc:
            raise LLMClientError("LLM server returned invalid JSON") from exc
        if not isinstance(parsed, dict):
            raise LLMClientError("LLM server response must be a JSON object")
        return parsed


def discover_local_model(base_url: str, timeout: float = DEFAULT_DISCOVERY_TIMEOUT) -> str:
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/models",
        headers={"Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except (TimeoutError, socket.timeout, ConnectionError, OSError, urllib.error.URLError) as exc:
        raise LLMClientError(f"LLM model discovery failed: {exc}") from exc

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise LLMClientError("LLM model discovery returned invalid JSON") from exc
    if not isinstance(parsed, dict):
        raise LLMClientError("LLM model discovery response must be a JSON object")

    models = parsed.get("data", [])
    if not isinstance(models, list):
        raise LLMClientError("LLM model discovery response missing data list")

    model_ids: list[str] = []
    for model in models:
        if not isinstance(model, dict):
            continue
        model_id = str(model.get("id", "")).strip()
        if model_id:
            model_ids.append(model_id)

    for model_id in model_ids:
        lowered = model_id.lower()
        if "embed" not in lowered and "embedding" not in lowered:
            return model_id
    return ""


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


def _http_error_detail(exc: urllib.error.HTTPError) -> str:
    try:
        raw = exc.read().decode("utf-8", errors="replace").strip()
    except OSError:
        return ""
    if not raw:
        return ""
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return raw[:240]
    if not isinstance(parsed, dict):
        return raw[:240]
    error = parsed.get("error")
    if isinstance(error, str):
        return error[:240]
    if isinstance(error, dict):
        message = error.get("message") or error.get("error")
        if message:
            return str(message)[:240]
    return raw[:240]


def _bool_env(name: str, default: bool) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return default


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
