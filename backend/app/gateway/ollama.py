"""Real Ollama provider via httpx using Ollama chat API with JSON format enforcement."""

import json
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.gateway.base import LLMError

T = TypeVar("T", bound=BaseModel)


class OllamaLLM:
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model_name: str = "llama3",
        privacy_consent: bool = False,
    ) -> None:
        if not privacy_consent:
            raise ValueError(
                "Privacy consent (llm_privacy_consent) must be True to use Ollama provider."
            )
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.client = httpx.Client(timeout=60.0)

    def complete(self, task: str, schema: type[T], inputs: dict[str, object]) -> T:
        url = f"{self.base_url}/api/chat"

        prompt_text = inputs.get("prompt_text", "")
        payload_data = {k: v for k, v in inputs.items() if k != "prompt_text"}

        content_msg = (
            f"Task: {task}\nPrompt:\n{prompt_text}\nInputs:\n"
            f"{json.dumps(payload_data, default=str)}"
        )

        body = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": content_msg}],
            "format": "json",
            "stream": False,
        }

        try:
            response = self.client.post(url, json=body)
        except httpx.TimeoutException as exc:
            raise LLMError("timeout", f"Ollama request timed out: {exc}") from exc
        except httpx.RequestError as exc:
            raise LLMError("unavailable", f"Ollama request failed: {exc}") from exc

        if response.status_code == 429:
            raise LLMError("rate_limit", "Ollama rate limit exceeded (429)")
        if response.status_code >= 500:
            raise LLMError(
                "unavailable",
                f"Ollama server error: {response.status_code}",
            )
        if response.status_code != 200:
            raise LLMError(
                "unavailable",
                f"Ollama API error status {response.status_code}: {response.text}",
            )

        try:
            data = response.json()
            message = data.get("message", {})
            content = message.get("content", "")
            if not content:
                raise LLMError("invalid_json", "Ollama response content is empty")

            return schema.model_validate_json(content)
        except (ValidationError, ValueError) as initial_err:
            raise LLMError(
                "invalid_json",
                f"Failed to validate JSON against schema: {initial_err}",
            ) from initial_err
        except Exception as exc:
            raise LLMError(
                "invalid_json",
                f"Failed to parse Ollama response: {exc}",
            ) from exc
