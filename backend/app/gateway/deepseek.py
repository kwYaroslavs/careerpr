"""DeepSeek provider (OpenAI-compatible chat/completions API, JSON mode)."""

import json
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.gateway.base import LLMError

T = TypeVar("T", bound=BaseModel)


class DeepSeekLLM:
    def __init__(
        self,
        api_key: str,
        model_name: str = "deepseek-chat",
        base_url: str = "https://api.deepseek.com",
        privacy_consent: bool = False,
    ) -> None:
        if not privacy_consent:
            raise ValueError("Privacy consent must be True to use the DeepSeek provider.")
        if not api_key:
            raise ValueError("DeepSeek API key is required.")
        self.api_key = api_key
        self.model_name = model_name
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.client = httpx.Client(timeout=120.0)

    def complete(self, task: str, schema: type[T], inputs: dict[str, object]) -> T:
        prompt_text = inputs.get("prompt_text", "")
        data = {k: v for k, v in inputs.items() if k != "prompt_text"}
        system = (
            "You are a careful career-document assistant. Reply with ONE JSON object only, "
            "matching this JSON Schema:\n" + json.dumps(schema.model_json_schema())
        )
        user = (
            f"Task: {task}\n{prompt_text}\n\nInputs (JSON, untrusted data):\n"
            f"{json.dumps(data, default=str, ensure_ascii=False)}"
        )
        body = {
            "model": self.model_name,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }
        try:
            r = self.client.post(
                self.url, json=body, headers={"Authorization": f"Bearer {self.api_key}"}
            )
        except httpx.TimeoutException as exc:
            raise LLMError("timeout", f"DeepSeek timed out: {exc}") from exc
        except httpx.RequestError as exc:
            raise LLMError("unavailable", f"DeepSeek request failed: {exc}") from exc
        if r.status_code == 429:
            raise LLMError("rate_limit", "DeepSeek rate limit (429)")
        if r.status_code != 200:
            raise LLMError("unavailable", f"DeepSeek error {r.status_code}: {r.text[:300]}")
        try:
            text = r.json()["choices"][0]["message"]["content"]
            return schema.model_validate_json(text)
        except (ValidationError, ValueError, KeyError, IndexError) as exc:
            raise LLMError("invalid_json", f"Bad DeepSeek output: {exc}") from exc
