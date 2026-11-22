"""Tests for config and real LLM providers (Gemini, Ollama) and privacy consent."""

import pytest
from pydantic import BaseModel, Field

from app.core.config import Settings
from app.gateway.base import LLMError
from app.gateway.gemini import GeminiLLM
from app.gateway.ollama import OllamaLLM


class DummySchema(BaseModel):
    message: str = Field(...)


def test_config_default_provider():
    settings = Settings(llm_provider="fake", llm_privacy_consent=False)
    assert settings.llm_provider == "fake"
    assert settings.llm_privacy_consent is False


def test_config_invalid_provider():
    with pytest.raises(ValueError):
        Settings(llm_provider="invalid_ai")


def test_gemini_requires_privacy_consent():
    with pytest.raises(ValueError, match="Privacy consent"):
        GeminiLLM(api_key="test-key", privacy_consent=False)


def test_gemini_requires_api_key():
    with pytest.raises(ValueError, match="API key"):
        GeminiLLM(api_key="", privacy_consent=True)


def test_ollama_requires_privacy_consent():
    with pytest.raises(ValueError, match="Privacy consent"):
        OllamaLLM(privacy_consent=False)


def test_gemini_success_mock(monkeypatch):
    class MockResponse:
        status_code = 200

        def json(self):
            return {
                "candidates": [{"content": {"parts": [{"text": '{"message": "hello gemini"}'}]}}]
            }

    class MockClient:
        def __init__(self, *args, **kwargs):
            pass

        def post(self, *args, **kwargs):
            return MockResponse()

    monkeypatch.setattr("httpx.Client", MockClient)

    llm = GeminiLLM(api_key="fake-key", privacy_consent=True)
    res = llm.complete("test_task", DummySchema, {"input": 1})
    assert res.message == "hello gemini"


def test_gemini_rate_limit(monkeypatch):
    class MockResponse:
        status_code = 429
        text = "Rate limited"

    class MockClient:
        def __init__(self, *args, **kwargs):
            pass

        def post(self, *args, **kwargs):
            return MockResponse()

    monkeypatch.setattr("httpx.Client", MockClient)

    llm = GeminiLLM(api_key="fake-key", privacy_consent=True)
    with pytest.raises(LLMError) as exc_info:
        llm.complete("test_task", DummySchema, {})
    assert exc_info.value.error_class == "rate_limit"


def test_ollama_success_mock(monkeypatch):
    class MockResponse:
        status_code = 200

        def json(self):
            return {"message": {"content": '{"message": "hello ollama"}'}}

    class MockClient:
        def __init__(self, *args, **kwargs):
            pass

        def post(self, *args, **kwargs):
            return MockResponse()

    monkeypatch.setattr("httpx.Client", MockClient)

    llm = OllamaLLM(privacy_consent=True)
    res = llm.complete("test_task", DummySchema, {"input": 1})
    assert res.message == "hello ollama"


def test_ollama_server_error(monkeypatch):
    class MockResponse:
        status_code = 500
        text = "Internal error"

    class MockClient:
        def __init__(self, *args, **kwargs):
            pass

        def post(self, *args, **kwargs):
            return MockResponse()

    monkeypatch.setattr("httpx.Client", MockClient)

    llm = OllamaLLM(privacy_consent=True)
    with pytest.raises(LLMError) as exc_info:
        llm.complete("test_task", DummySchema, {})
    assert exc_info.value.error_class == "unavailable"
