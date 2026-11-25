"""Real Gemini provider via httpx using Gemini REST API with structured JSON output."""

import json
import re
import time
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.gateway.base import LLMError

T = TypeVar("T", bound=BaseModel)


class GeminiLLM:
    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-1.5-flash",
        privacy_consent: bool = False,
        fallback_models: list[str] | None = None,
    ) -> None:
        if not privacy_consent:
            raise ValueError(
                "Privacy consent (llm_privacy_consent) must be True to use Gemini provider."
            )
        if not api_key.strip():
            raise ValueError(
                "Gemini API key is empty: paste it in the form, or put GEMINI_API_KEY=... "
                "into backend/.env (or root .env) and RESTART the server."
            )
        # several keys may be given (comma/space/newline separated): rotate on failure
        self.keys = [k for k in re.split(r"[,;\s]+", api_key) if k]
        self.api_key = self.keys[0]
        self._next = 0
        self.model_name = model_name.strip().removeprefix("models/")
        self.fallback_models = [
            m.strip().removeprefix("models/") for m in (fallback_models or []) if m.strip()
        ]
        self.client = httpx.Client(timeout=90.0)

    def complete(self, task: str, schema: type[T], inputs: dict[str, object]) -> T:
        """Per model: round-robin keys on 429/timeout/bad key; on 5xx (model overloaded)
        skip to the next fallback model after a short pause."""
        last: LLMError | None = None
        for mi, model in enumerate([self.model_name, *self.fallback_models]):
            if mi:
                time.sleep(1.5)
            for n in range(len(self.keys)):
                idx = (self._next + n) % len(self.keys)
                try:
                    res = self._complete_once(self.keys[idx], model, task, schema, inputs)
                except LLMError as e:
                    last = e
                    msg = str(e)
                    if "(404)" in msg:
                        if mi == 0:
                            raise
                        break  # unknown fallback model: try the next one
                    if "server error" in msg:
                        break  # model overloaded for every key: switch model
                    if e.error_class in ("rate_limit", "timeout", "unavailable"):
                        continue
                    raise
                self._next = (idx + 1) % len(self.keys)
                return res
        assert last is not None
        tried = [self.model_name, *self.fallback_models]
        raise LLMError(
            last.error_class,
            f"all keys/models failed (models tried: {', '.join(tried)}); last: {last}",
        )

    def _complete_once(
        self, api_key: str, model: str, task: str, schema: type[T], inputs: dict[str, object]
    ) -> T:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={api_key}"
        )

        prompt_text = inputs.get("prompt_text", "")
        payload_data = {k: v for k, v in inputs.items() if k != "prompt_text"}

        contents_text = (
            f"Task: {task}\nPrompt:\n{prompt_text}\nInputs:\n"
            f"{json.dumps(payload_data, default=str, ensure_ascii=False)}\n\n"
            f"Return ONLY a JSON object matching this JSON Schema:\n"
            f"{json.dumps(schema.model_json_schema())}"
        )

        body = {
            "contents": [{"parts": [{"text": contents_text}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
            },
        }

        try:
            response = self.client.post(url, json=body)
        except httpx.TimeoutException as exc:
            raise LLMError("timeout", f"Gemini request timed out: {exc}") from exc
        except httpx.RequestError as exc:
            raise LLMError("unavailable", f"Gemini request failed: {exc}") from exc

        if response.status_code == 429:
            raise LLMError("rate_limit", "Gemini rate limit exceeded (429)")
        if response.status_code >= 500:
            raise LLMError(
                "unavailable",
                f"Gemini server error: {response.status_code} {response.text[:150]}",
            )
        if response.status_code == 404:
            raise LLMError(
                "unavailable",
                f"Gemini model '{model}' not found (404). Check the exact name "
                "(dots, not dashes: e.g. gemini-2.5-flash, gemini-2.5-flash-lite) "
                f"or leave the model field empty. {response.text[:200]}",
            )
        if response.status_code != 200:
            raise LLMError(
                "unavailable",
                f"Gemini API error status {response.status_code}: {response.text}",
            )

        try:
            data = response.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise LLMError(
                    "invalid_json",
                    "Gemini response contained no candidates",
                )

            content_part = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            if not content_part:
                raise LLMError(
                    "invalid_json",
                    "Gemini response text is empty",
                )

            return schema.model_validate_json(content_part)
        except (ValidationError, ValueError) as initial_err:
            raise LLMError(
                "invalid_json",
                f"Failed to validate JSON against schema: {initial_err}",
            ) from initial_err
        except Exception as exc:
            raise LLMError(
                "invalid_json",
                f"Failed to parse Gemini response: {exc}",
            ) from exc
