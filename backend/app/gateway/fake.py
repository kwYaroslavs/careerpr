"""Deterministic provider for offline dev/tests. Responses come from a task->JSON dict."""

from typing import Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from app.gateway.base import LLMError

T = TypeVar("T", bound=BaseModel)


class LLMGateway(Protocol):
    def complete(self, task: str, schema: type[T], inputs: dict[str, object]) -> T: ...


class FakeLLM:
    def __init__(
        self,
        responses: dict[str, str],
        repair_responses: dict[str, str] | None = None,
    ) -> None:
        self.responses = responses
        self.repair_responses = repair_responses or {}
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.repair_calls: list[tuple[str, str]] = []

    def complete(self, task: str, schema: type[T], inputs: dict[str, object]) -> T:
        self.calls.append((task, inputs))
        if task not in self.responses:
            raise LLMError("unavailable", f"no fixture for task {task}")

        raw_output = self.responses[task]
        try:
            return schema.model_validate_json(raw_output)
        except (ValidationError, ValueError) as initial_err:
            repair_key = f"{task}:repair"
            if repair_key in self.repair_responses:
                self.repair_calls.append((task, raw_output))
                repaired_output = self.repair_responses[repair_key]
                try:
                    return schema.model_validate_json(repaired_output)
                except (ValidationError, ValueError) as repair_err:
                    raise LLMError(
                        "invalid_json",
                        f"Repair failed validation: {repair_err}",
                    ) from repair_err

            raise LLMError(
                "invalid_json",
                f"Initial validation/parsing failed: {initial_err}",
            ) from initial_err
