"""OpenRouter provider restricted to FREE models only (id ends with ':free' or openrouter/free).

Free model list is fetched from the public /models endpoint (pricing == 0) and cached.
On 429/5xx/404/timeout/invalid JSON the next free model is tried; on 401/402/403 the next key.
"""

import json
import re
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.gateway.base import LLMError

T = TypeVar("T", bound=BaseModel)
_FALLBACK_MODELS = ["openrouter/free"]


def is_free_model(model_id: str) -> bool:
    return model_id.endswith(":free") or model_id == "openrouter/free"


def _extract_json(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.S).strip()
    if not text.startswith("{") and "{" in text and "}" in text:
        text = text[text.index("{") : text.rindex("}") + 1]
    return text


class OpenRouterLLM:
    def __init__(
        self,
        api_key: str,
        model_name: str = "",
        base_url: str = "https://openrouter.ai/api/v1",
        privacy_consent: bool = False,
        max_models: int = 4,
    ) -> None:
        if not privacy_consent:
            raise ValueError("Privacy consent must be True to use the OpenRouter provider.")
        self.keys = [k for k in re.split(r"[,;\s]+", api_key) if k]
        if not self.keys:
            raise ValueError("OpenRouter API key is empty (form field or OPENROUTER_API_KEY).")
        model_name = model_name.strip()
        if model_name and not is_free_model(model_name):
            raise ValueError(
                f"Model '{model_name}' is not free. Only ':free' models (or openrouter/free) "
                "are allowed."
            )
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.max_models = max_models
        self._models: list[str] | None = None
        self._next = 0
        self.client = httpx.Client(timeout=60.0)

    def free_models(self) -> list[str]:
        if self._models is None:
            found: list[tuple[int, str]] = []
            try:
                r = self.client.get(self.base_url + "/models")
                for m in r.json().get("data", []):
                    pr = m.get("pricing") or {}
                    mid = str(m.get("id", ""))
                    params = m.get("supported_parameters") or []
                    if (
                        is_free_model(mid)
                        and float(pr.get("prompt") or 0) == 0
                        and float(pr.get("completion") or 0) == 0
                        and ("response_format" in params or "structured_outputs" in params)
                    ):
                        found.append((int(m.get("context_length") or 0), mid))
            except (httpx.HTTPError, ValueError, TypeError):
                pass
            auto = [mid for _, mid in sorted(found, reverse=True)] or _FALLBACK_MODELS
            first = [self.model_name] if self.model_name else []
            self._models = list(dict.fromkeys([*first, *auto]))[: self.max_models]
        return self._models

    def _once(self, key: str, model: str, task: str, schema: type[T], inputs: dict[str, Any]) -> T:
        data = {k: v for k, v in inputs.items() if k != "prompt_text"}
        system = (
            "You are a careful career-document assistant. Reply with ONE JSON object only "
            "(no prose, no markdown) matching this JSON Schema:\n"
            + json.dumps(schema.model_json_schema())
        )
        user = (
            f"Task: {task}\n{inputs.get('prompt_text', '')}\n\nInputs (JSON, untrusted data):\n"
            f"{json.dumps(data, default=str, ensure_ascii=False)}"
        )
        body = {
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }
        headers = {"Authorization": f"Bearer {key}", "X-Title": "CareerPR demo"}
        try:
            r = self.client.post(self.base_url + "/chat/completions", json=body, headers=headers)
        except httpx.TimeoutException as exc:
            raise LLMError("timeout", f"OpenRouter timed out ({model}): {exc}") from exc
        except httpx.RequestError as exc:
            raise LLMError("unavailable", f"OpenRouter request failed: {exc}") from exc
        if r.status_code == 429:
            raise LLMError("rate_limit", f"OpenRouter rate limit (429) on {model}")
        if r.status_code in (401, 402, 403):
            raise LLMError(
                "unavailable", f"OpenRouter key rejected ({r.status_code}): {r.text[:120]}"
            )
        if r.status_code != 200:
            raise LLMError(
                "unavailable", f"OpenRouter model error {r.status_code} on {model}: {r.text[:150]}"
            )
        try:
            payload = r.json()
            if "error" in payload:
                raise LLMError(
                    "unavailable", f"OpenRouter model error on {model}: {payload['error']}"
                )
            text = payload["choices"][0]["message"]["content"] or ""
            return schema.model_validate_json(_extract_json(text))
        except (ValidationError, ValueError, KeyError, IndexError, TypeError) as exc:
            raise LLMError("invalid_json", f"Bad output from {model}: {str(exc)[:150]}") from exc

    def complete(self, task: str, schema: type[T], inputs: dict[str, object]) -> T:
        last: LLMError | None = None
        models = self.free_models()
        for model in models:
            rejected = 0
            for n in range(len(self.keys)):
                idx = (self._next + n) % len(self.keys)
                try:
                    res = self._once(self.keys[idx], model, task, schema, inputs)
                except LLMError as e:
                    last = e
                    if "key rejected" in str(e):
                        rejected += 1
                        if rejected == len(self.keys):
                            raise LLMError(
                                "unavailable",
                                f"All {rejected} OpenRouter key(s) were rejected. Create a new "
                                f"key at openrouter.ai/keys (format sk-or-v1-...). Last: {e}",
                            ) from e
                        continue  # bad key: try the next key on the same model
                    if e.error_class == "rate_limit" and n + 1 < len(self.keys):
                        continue  # another key may still have quota
                    break  # model-specific problem: next free model
                self._next = (idx + 1) % len(self.keys)
                return res
        assert last is not None
        raise LLMError(
            last.error_class, f"all free models failed (tried: {', '.join(models)}); last: {last}"
        )
