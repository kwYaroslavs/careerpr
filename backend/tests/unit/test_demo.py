import base64
import json

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.gateway.base import LLMError
from app.gateway.deepseek import DeepSeekLLM
from app.main import app

CV = (
    "Ivan Petrov\nivan@example.com +380 50 123 4567\n"
    "Built REST services in Python and Docker for an e-commerce platform\n"
    "Skills: Python, SQL, Docker, Git, Linux\nBachelor degree in Computer Science, KPI University"
)
JOB = "Python Developer\n3+ years of Python experience\nDocker and CI/CD\nKubernetes experience"
client = TestClient(app)


def test_demo_fake_full_flow() -> None:
    r = client.post("/demo/run", json={"cv_text": CV, "job_text": JOB, "provider": "fake"})
    assert r.status_code == 200
    d = r.json()
    assert d["triage"]["bucket"] in {"strong", "possible", "stretch", "blocked"}
    assert base64.b64decode(d["resume_pdf_b64"])[:4] == b"%PDF"
    assert base64.b64decode(d["cover_letter_pdf_b64"])[:4] == b"%PDF"
    assert "Ivan Petrov" in d["resume_markdown"]
    assert d["cover_letter"]["cover_letter"]


def test_demo_external_provider_needs_consent() -> None:
    r = client.post(
        "/demo/run",
        json={"cv_text": CV, "job_text": JOB, "provider": "deepseek", "api_key": "k"},
    )
    assert r.status_code == 400


def test_demo_rejects_short_input() -> None:
    assert client.post("/demo/run", json={"cv_text": "x", "job_text": "y"}).status_code == 422


class _Out(BaseModel):
    a: int


def _ds(handler: httpx.MockTransport) -> DeepSeekLLM:
    llm = DeepSeekLLM("k", privacy_consent=True)
    llm.client = httpx.Client(transport=handler)
    return llm


def test_deepseek_parses_json_and_maps_errors() -> None:
    ok = httpx.MockTransport(
        lambda req: httpx.Response(200, json={"choices": [{"message": {"content": '{"a": 1}'}}]})
    )
    assert _ds(ok).complete("t", _Out, {}).a == 1
    bad = httpx.MockTransport(
        lambda req: httpx.Response(200, json={"choices": [{"message": {"content": "nope"}}]})
    )
    with pytest.raises(LLMError) as e:
        _ds(bad).complete("t", _Out, {})
    assert e.value.error_class == "invalid_json"
    limited = httpx.MockTransport(lambda req: httpx.Response(429, text=json.dumps({})))
    with pytest.raises(LLMError) as e2:
        _ds(limited).complete("t", _Out, {})
    assert e2.value.error_class == "rate_limit"


def test_deepseek_requires_consent_and_key() -> None:
    with pytest.raises(ValueError):
        DeepSeekLLM("k", privacy_consent=False)
    with pytest.raises(ValueError):
        DeepSeekLLM("", privacy_consent=True)


def test_gemini_rotates_keys_on_rate_limit() -> None:
    from app.gateway.gemini import GeminiLLM

    seen: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        key = req.url.params["key"]
        seen.append(key)
        if key == "k1":
            return httpx.Response(429, text="quota")
        body = {"candidates": [{"content": {"parts": [{"text": '{"a": 2}'}]}}]}
        return httpx.Response(200, json=body)

    llm = GeminiLLM("k1, k2", privacy_consent=True)
    llm.client = httpx.Client(transport=httpx.MockTransport(handler))
    assert llm.complete("t", _Out, {}).a == 2
    assert seen == ["k1", "k2"]


def test_gemini_falls_back_to_next_model_on_503(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.gateway import gemini as gm

    monkeypatch.setattr(gm.time, "sleep", lambda s: None)
    models: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        model = req.url.path.split("/models/")[1].split(":")[0]
        models.append(model)
        if model == "main":
            return httpx.Response(503, text="overloaded")
        body = {"candidates": [{"content": {"parts": [{"text": '{"a": 3}'}]}}]}
        return httpx.Response(200, json=body)

    llm = gm.GeminiLLM("k1,k2", "main", True, ["backup"])
    llm.client = httpx.Client(transport=httpx.MockTransport(handler))
    assert llm.complete("t", _Out, {}).a == 3
    assert models == ["main", "backup"]  # overload skips remaining keys, switches model


def test_openrouter_free_only_and_model_fallback() -> None:
    from app.gateway.openrouter import OpenRouterLLM

    with pytest.raises(ValueError):
        OpenRouterLLM("k", "openai/gpt-4o", privacy_consent=True)  # paid model rejected

    calls: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("/models"):
            data = [
                {
                    "id": "paid/x",
                    "pricing": {"prompt": "0.1", "completion": "0.1"},
                    "supported_parameters": ["response_format"],
                    "context_length": 999999,
                },
                {
                    "id": "a/small:free",
                    "pricing": {"prompt": "0", "completion": "0"},
                    "supported_parameters": ["response_format"],
                    "context_length": 1000,
                },
                {
                    "id": "b/big:free",
                    "pricing": {"prompt": "0", "completion": "0"},
                    "supported_parameters": ["response_format"],
                    "context_length": 50000,
                },
            ]
            return httpx.Response(200, json={"data": data})
        model = json.loads(req.content)["model"]
        calls.append(model)
        if model == "b/big:free":
            return httpx.Response(429, text="limit")
        content = '```json\n{"a": 5}\n```'
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    llm = OpenRouterLLM("k", privacy_consent=True)
    llm.client = httpx.Client(transport=httpx.MockTransport(handler))
    assert llm.complete("t", _Out, {}).a == 5
    assert calls == ["b/big:free", "a/small:free"]  # paid model never used


def test_openrouter_all_keys_rejected_fails_fast() -> None:
    from app.gateway.openrouter import OpenRouterLLM

    calls = {"n": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("/models"):
            data = [
                {
                    "id": f"m{i}:free",
                    "pricing": {"prompt": "0", "completion": "0"},
                    "supported_parameters": ["response_format"],
                }
                for i in range(3)
            ]
            return httpx.Response(200, json={"data": data})
        calls["n"] += 1
        return httpx.Response(401, json={"error": {"message": "User not found.", "code": 401}})

    llm = OpenRouterLLM("bad1,bad2", privacy_consent=True)
    llm.client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(LLMError, match="rejected"):
        llm.complete("t", _Out, {})
    assert calls["n"] == 2  # one attempt per key, no model cycling
