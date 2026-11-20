"""Prompt loader and LLM run logging implementation.

See docs/LLM_CONTRACTS.md and docs/DATA_MODEL.md.
Prompts live at backend/prompts/<id>@<version>.md. Released prompts are never edited in place.
Every LLM call computes input_hash, cache key, and writes an LLMRun record to the database.
"""

import contextlib
import hashlib
import json
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.domain.models import LLMRunModel
from app.gateway.base import LLMError

T = TypeVar("T", bound=BaseModel)


def get_prompts_dir() -> Path:
    if Path("backend/prompts").exists():
        return Path("backend/prompts")
    elif Path("prompts").exists():
        return Path("prompts")
    return Path("backend/prompts")


def load_prompt(prompt_id: str, version: str) -> str:
    """Load prompt content from backend/prompts/<prompt_id>@<version>.md.

    Raises FileNotFoundError if the prompt file does not exist.
    """
    prompts_dir = get_prompts_dir()
    filename = f"{prompt_id}@{version}.md"
    prompt_path = prompts_dir / filename
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def compute_input_hash(inputs: dict[str, Any]) -> str:
    """Compute SHA-256 hash of serialized inputs."""
    serialized = json.dumps(inputs, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def compute_cache_key(prompt_id: str, version: str, input_hash: str, model: str) -> str:
    """Compute cache key combining prompt id, version, input hash, and model."""
    raw = f"{prompt_id}@{version}:{model}:{input_hash}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class LoggedLLMGateway:
    """LLM Gateway wrapper that loads prompts, computes hashes/cache keys, and logs LLMRun."""

    def __init__(
        self,
        inner_gateway: Any,
        db_session: Session | None = None,
        model_name: str = "fake-model",
    ) -> None:
        self.inner_gateway = inner_gateway
        self.db_session = db_session
        self.model_name = model_name

    def complete(
        self,
        task: str,
        schema: type[T],
        inputs: dict[str, object],
        prompt_id: str | None = None,
        version: str | None = None,
        run_id: str = "default-run",
        step: str = "default-step",
    ) -> T:
        """Execute LLM completion, loading prompt, hashing inputs, and logging LLMRun."""
        effective_prompt_id = prompt_id or task
        effective_version = version or "v1"

        prompt_text = ""
        with contextlib.suppress(FileNotFoundError):
            prompt_text = load_prompt(effective_prompt_id, effective_version)

        augmented_inputs = dict(inputs)
        if prompt_text and "prompt_text" not in augmented_inputs:
            augmented_inputs["prompt_text"] = prompt_text

        input_hash = compute_input_hash(augmented_inputs)
        cache_key = compute_cache_key(
            effective_prompt_id, effective_version, input_hash, self.model_name
        )

        import time

        start_time = time.time()
        error_class: str | None = None
        tokens = 0

        try:
            res: Any = self.inner_gateway.complete(task, schema, augmented_inputs)
            latency_ms = (time.time() - start_time) * 1000.0
            result: T = schema.model_validate(res)
            return result
        except LLMError as e:
            error_class = e.error_class
            latency_ms = (time.time() - start_time) * 1000.0
            raise
        except Exception as e:
            error_class = "unavailable"
            latency_ms = (time.time() - start_time) * 1000.0
            raise LLMError("unavailable", str(e)) from e
        finally:
            if self.db_session is not None:
                run_hash_input = (run_id + step + cache_key).encode()
                run_id_str = f"llmrun_{hashlib.md5(run_hash_input).hexdigest()[:12]}"
                run_record = LLMRunModel(
                    id=run_id_str,
                    run_id=run_id,
                    step=step,
                    prompt_id=f"{effective_prompt_id}@{effective_version}",
                    input_hash=input_hash,
                    model=self.model_name,
                    tokens=tokens,
                    latency_ms=latency_ms,
                    error_class=error_class,
                )
                self.db_session.add(run_record)
                self.db_session.flush()
