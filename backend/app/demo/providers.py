"""Provider factory + tracing wrapper for the demo flow."""

import time
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.gateway.base import LLMError
from app.gateway.deepseek import DeepSeekLLM
from app.gateway.gemini import GeminiLLM
from app.gateway.ollama import OllamaLLM
from app.gateway.openrouter import OpenRouterLLM


class TracingLLM:
    """Wraps any provider and records each call (task, ms, ok, error) for the UI."""

    def __init__(self, inner: Any) -> None:
        self.inner = inner
        self.trace: list[dict[str, Any]] = []

    def complete(self, task: str, schema: type, inputs: dict[str, object]) -> Any:
        t0 = time.time()
        try:
            res = self.inner.complete(task, schema, inputs)
        except LLMError as e:
            self.trace.append(
                {"task": task, "ms": int((time.time() - t0) * 1000), "ok": False, "error": str(e)}
            )
            raise
        self.trace.append({"task": task, "ms": int((time.time() - t0) * 1000), "ok": True})
        return res


def _env_files() -> list[Path]:
    root = Path(__file__).resolve().parents[3]
    return [root / ".env", root / "backend" / ".env"]


def available_providers(s: Settings) -> dict[str, Any]:
    return {
        "default": s.llm_provider,
        "env_files": [str(p) for p in _env_files() if p.exists()],
        "providers": {
            "fake": {"ready": True, "model": "offline"},
            "gemini": {"ready": bool(s.gemini_api_key), "model": s.gemini_model},
            "deepseek": {"ready": bool(s.deepseek_api_key), "model": s.deepseek_model},
            "openrouter": {
                "ready": bool(s.openrouter_api_key),
                "model": s.openrouter_model or "auto (free)",
            },
            "ollama": {"ready": True, "model": s.ollama_model},
        },
    }


def build_llm(
    provider: str, s: Settings, api_key: str = "", model: str = "", consent: bool = False
) -> tuple[Any, str]:
    """Return (llm, model_name). A form key overrides .env; it is never stored."""
    ok = consent or s.llm_privacy_consent
    if provider == "fake":
        from app.demo.fake import DemoFakeLLM

        return DemoFakeLLM(), "fake"
    if provider == "gemini":
        m = model or s.gemini_model
        fb = [x for x in s.gemini_fallback_models.split(",") if x.strip() and x.strip() != m]
        return GeminiLLM(api_key or s.gemini_api_key, m, ok, fb), m
    if provider == "deepseek":
        m = model or s.deepseek_model
        return DeepSeekLLM(api_key or s.deepseek_api_key, m, s.deepseek_base_url, ok), m
    if provider == "openrouter":
        m = model or s.openrouter_model
        key = api_key or s.openrouter_api_key
        return OpenRouterLLM(key, m, s.openrouter_base_url, ok), m or "auto-free"
    if provider == "ollama":
        m = model or s.ollama_model
        return OllamaLLM(s.ollama_base_url, m, True), m
    raise ValueError(f"Unknown provider: {provider}")
