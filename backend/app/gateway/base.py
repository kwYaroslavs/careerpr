"""LLM Gateway interface. One method; providers plug in via config. See docs/LLM_CONTRACTS.md."""

from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    """error_class: rate_limit | timeout | invalid_json | unavailable"""

    def __init__(self, error_class: str, msg: str = "") -> None:
        super().__init__(msg or error_class)
        self.error_class = error_class


class LLMGateway(Protocol):
    def complete(self, task: str, schema: type[T], inputs: dict[str, object]) -> T: ...
