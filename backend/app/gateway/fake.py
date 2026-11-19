"""Deterministic provider for offline dev/tests. Responses come from a task->JSON dict."""

from typing import TypeVar

from pydantic import BaseModel

from app.gateway.base import LLMError

T = TypeVar("T", bound=BaseModel)


class FakeLLM:
    def __init__(self, responses: dict[str, str]) -> None:
        self.responses = responses
        self.calls: list[str] = []

    def complete(self, task: str, schema: type[T], inputs: dict[str, object]) -> T:
        self.calls.append(task)
        if task not in self.responses:
            raise LLMError("unavailable", f"no fixture for task {task}")
        return schema.model_validate_json(self.responses[task])
