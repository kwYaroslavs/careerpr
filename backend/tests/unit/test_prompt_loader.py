"""Unit tests for prompt loading and LLM run logging."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.db import Base
from app.domain.models import LLMRunModel
from app.gateway.base import LLMError
from app.gateway.fake import FakeLLM
from app.gateway.prompt_loader import (
    LoggedLLMGateway,
    compute_cache_key,
    compute_input_hash,
)


@pytest.fixture
def pydantic_schema():
    from pydantic import BaseModel

    class Dummy(BaseModel):
        output: str

    return Dummy


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def test_load_prompt_and_hashing(tmp_path):
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    prompt_file = prompts_dir / "extract_requirements@v1.md"
    prompt_file.write_text("Extract requirements from job description.", encoding="utf-8")

    inp_hash = compute_input_hash({"jd": "python engineer"})
    assert len(inp_hash) == 64

    cache_key = compute_cache_key("extract_requirements", "v1", inp_hash, "fake-model")
    assert len(cache_key) == 64


def test_logged_llm_gateway_success(db_session, pydantic_schema):
    inner = FakeLLM({"extract_reqs": '{"output": "ok"}'})
    logged_gw = LoggedLLMGateway(
        inner_gateway=inner, db_session=db_session, model_name="test-model"
    )

    res = logged_gw.complete(
        task="extract_reqs",
        schema=pydantic_schema,
        inputs={"text": "hello"},
        prompt_id="extract_reqs",
        version="v1",
        run_id="run-123",
        step="step-1",
    )

    assert res.output == "ok"

    runs = db_session.query(LLMRunModel).all()
    assert len(runs) == 1
    assert runs[0].run_id == "run-123"
    assert runs[0].step == "step-1"
    assert runs[0].prompt_id == "extract_reqs@v1"
    assert runs[0].model == "test-model"
    assert runs[0].error_class is None
    assert runs[0].latency_ms >= 0.0


def test_logged_llm_gateway_error(db_session, pydantic_schema):
    inner = FakeLLM({})
    logged_gw = LoggedLLMGateway(
        inner_gateway=inner, db_session=db_session, model_name="test-model"
    )

    with pytest.raises(LLMError) as exc_info:
        logged_gw.complete(
            task="missing_task",
            schema=pydantic_schema,
            inputs={"text": "hello"},
            run_id="run-456",
            step="step-2",
        )

    assert exc_info.value.error_class == "unavailable"

    runs = db_session.query(LLMRunModel).all()
    assert len(runs) == 1
    assert runs[0].run_id == "run-456"
    assert runs[0].error_class == "unavailable"
