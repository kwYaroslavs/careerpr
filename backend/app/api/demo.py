"""Demo endpoints: one form -> full pipeline result. In-memory, nothing is stored."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.demo.pipeline import run_demo
from app.demo.providers import TracingLLM, available_providers, build_llm
from app.gateway.base import LLMError

router = APIRouter(prefix="/demo", tags=["demo"])


class DemoRunRequest(BaseModel):
    cv_text: str = Field(min_length=20, max_length=30000)
    job_text: str = Field(min_length=20, max_length=30000)
    company_hook: str = ""
    mode: str = "expanded"
    provider: str = "fake"
    model: str = ""
    api_key: str = Field(default="", repr=False)  # used for this request only, never stored
    consent: bool = False
    work_authorization: str = ""  # e.g. "EU citizen" / "need visa"
    location: str = ""
    effort: str = "min"  # min=3 LLM calls | balanced=6 | full=up to 11
    max_pages: int = Field(default=2, ge=1, le=3)


@router.get("/config")
def demo_config() -> dict[str, Any]:
    return available_providers(get_settings())


@router.post("/run")
def demo_run(body: DemoRunRequest) -> dict[str, Any]:
    s = get_settings()
    if body.provider in ("gemini", "deepseek", "openrouter") and not (
        body.consent or s.llm_privacy_consent
    ):
        raise HTTPException(400, "Tick the consent box: CV text will be sent to an external LLM.")
    try:
        inner, model_name = build_llm(body.provider, s, body.api_key, body.model, body.consent)
        llm = TracingLLM(inner)
        return run_demo(
            llm,
            f"{body.provider}:{model_name}",
            body.cv_text,
            body.job_text,
            body.company_hook,
            body.mode,
            body.max_pages,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except LLMError as e:
        raise HTTPException(502, f"LLM error ({e.error_class}): {e}") from e
