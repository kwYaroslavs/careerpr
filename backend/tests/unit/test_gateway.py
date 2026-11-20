import pytest
from pydantic import BaseModel, Field

from app.gateway.base import LLMError
from app.gateway.fake import FakeLLM


class DummySchema(BaseModel):
    result: str = Field(...)
    score: int = Field(...)


def test_fake_llm_normal_case():
    responses = {"test_task": '{"result": "success", "score": 100}'}
    llm = FakeLLM(responses)
    res = llm.complete("test_task", DummySchema, {"input": 1})
    assert res.result == "success"
    assert res.score == 100
    assert llm.calls == [("test_task", {"input": 1})]


def test_fake_llm_unavailable():
    llm = FakeLLM({})
    with pytest.raises(LLMError) as exc_info:
        llm.complete("missing_task", DummySchema, {})
    assert exc_info.value.error_class == "unavailable"


def test_fake_llm_invalid_json_no_repair():
    responses = {"bad_task": '{"result": "success", "score": "not_an_int"}'}
    llm = FakeLLM(responses)
    with pytest.raises(LLMError) as exc_info:
        llm.complete("bad_task", DummySchema, {})
    assert exc_info.value.error_class == "invalid_json"


def test_fake_llm_repair_success():
    responses = {"repair_task": "malformed json or invalid schema"}
    repair_responses = {"repair_task:repair": '{"result": "repaired", "score": 95}'}
    llm = FakeLLM(responses, repair_responses)
    res = llm.complete("repair_task", DummySchema, {})
    assert res.result == "repaired"
    assert res.score == 95
    assert len(llm.repair_calls) == 1


def test_fake_llm_repair_failure():
    responses = {"repair_task": "malformed json"}
    repair_responses = {"repair_task:repair": "still malformed"}
    llm = FakeLLM(responses, repair_responses)
    with pytest.raises(LLMError) as exc_info:
        llm.complete("repair_task", DummySchema, {})
    assert exc_info.value.error_class == "invalid_json"
    assert len(llm.repair_calls) == 1
