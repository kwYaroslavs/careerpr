"""API endpoints for career discovery (roles, transferable skills, gaps, resolution).
T-041.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.career.gaps import (
    GapAnalysisResult,
    analyze_gaps,
    resolve_clarification_question_to_fact,
)
from app.career.roles import RoleDiscoveryResult, suggest_roles
from app.career.transferable import (
    TransferableDiscoveryResult,
    discover_transferable_skills,
)
from app.core.db import get_db
from app.domain.schemas import Fact, JobRequirement, SearchMode

router = APIRouter(prefix="/career", tags=["career"])


class RoleSuggestRequest(BaseModel):
    facts: list[Fact] = Field(default_factory=list)
    search_mode: SearchMode = SearchMode.EXPANDED
    hard_constraints: dict[str, Any] = Field(default_factory=dict)
    skill_aliases: dict[str, str] = Field(default_factory=dict)
    run_id: str = "default-run"


class TransferableRequest(BaseModel):
    job_id: str
    requirement: JobRequirement
    facts: list[Fact] = Field(default_factory=list)
    skill_aliases: dict[str, str] = Field(default_factory=dict)
    run_id: str = "default-run"


class GapAnalysisRequest(BaseModel):
    job_id: str
    requirements: list[JobRequirement] = Field(default_factory=list)
    facts: list[Fact] = Field(default_factory=list)
    skill_aliases: dict[str, str] = Field(default_factory=dict)


class ClarificationResolutionRequest(BaseModel):
    question_id: str
    answer_text: str
    fact_id: str
    tags: list[str] = Field(default_factory=lambda: ["clarification", "verified"])


@router.post("/roles", response_model=RoleDiscoveryResult)
def api_suggest_roles(body: RoleSuggestRequest, db: Annotated[Session, Depends(get_db)]) -> Any:
    """Suggest career roles based on candidate facts, taxonomy, and search mode."""
    try:
        result = suggest_roles(
            facts=body.facts,
            search_mode=body.search_mode,
            hard_constraints=body.hard_constraints,
            db_session=db,
            skill_aliases=body.skill_aliases,
            run_id=body.run_id,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/transferable", response_model=TransferableDiscoveryResult)
def api_discover_transferable(
    body: TransferableRequest, db: Annotated[Session, Depends(get_db)]
) -> Any:
    """Discover transferable skills and evaluate match categories."""
    try:
        result = discover_transferable_skills(
            job_id=body.job_id,
            requirement=body.requirement,
            facts=body.facts,
            db_session=db,
            skill_aliases=body.skill_aliases,
            run_id=body.run_id,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/gaps", response_model=GapAnalysisResult)
def api_analyze_gaps(body: GapAnalysisRequest) -> Any:
    """Analyze gaps between requirements and facts, generating clarification questions."""
    try:
        result = analyze_gaps(
            job_id=body.job_id,
            requirements=body.requirements,
            facts=body.facts,
            skill_aliases=body.skill_aliases,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/gaps/resolve", response_model=Fact, status_code=status.HTTP_201_CREATED)
def api_resolve_clarification(
    body: ClarificationResolutionRequest, db: Annotated[Session, Depends(get_db)]
) -> Any:
    """Turn an answered clarification question into a new versioned fact."""
    try:
        fact = resolve_clarification_question_to_fact(
            session=db,
            question_id=body.question_id,
            answer_text=body.answer_text,
            fact_id=body.fact_id,
            tags=body.tags,
        )
        return fact
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
