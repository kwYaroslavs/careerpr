"""API endpoints for requirement confirmation, editing, and addition (T-010, Gate G2)."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.domain.schemas import JobRequirement, RequirementKind
from app.domain.services.requirements import RequirementService

router = APIRouter(prefix="/requirements", tags=["requirements"])


class RequirementBatchSaveRequest(BaseModel):
    job_id: str
    requirements: list[JobRequirement]


class RequirementUpdateRequest(BaseModel):
    text: str | None = None
    kind: RequirementKind | None = None
    user_confirmed: bool | None = None
    normalized_skill_ids: list[str] | None = None
    evidence_ids: list[str] | None = None


class RequirementAddRequest(BaseModel):
    job_id: str
    id: str
    text: str
    kind: RequirementKind = RequirementKind.MUST
    user_confirmed: bool = True
    normalized_skill_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


def _to_schema(db_req: Any) -> JobRequirement:
    return JobRequirement(
        schema_version=db_req.schema_version,
        id=db_req.id,
        job_id=db_req.job_id,
        text=db_req.text,
        kind=RequirementKind(db_req.kind),
        normalized_skill_ids=db_req.normalized_skill_ids,
        evidence_ids=db_req.evidence_ids,
        user_confirmed=db_req.user_confirmed,
    )


@router.get("/job/{job_id}", response_model=list[JobRequirement])
def get_job_requirements(job_id: str, db: Annotated[Session, Depends(get_db)]) -> Any:
    """Retrieve all requirements for a job posting."""
    reqs = RequirementService.get_job_requirements(db, job_id)
    return [_to_schema(r) for r in reqs]


@router.post(
    "/batch",
    response_model=list[JobRequirement],
    status_code=status.HTTP_201_CREATED,
)
def save_batch_requirements(
    body: RequirementBatchSaveRequest, db: Annotated[Session, Depends(get_db)]
) -> Any:
    """Save or update extracted requirements for a job."""
    try:
        saved = RequirementService.save_requirements(db, body.job_id, body.requirements)
        return [_to_schema(r) for r in saved]
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("", response_model=JobRequirement, status_code=status.HTTP_201_CREATED)
def add_requirement(body: RequirementAddRequest, db: Annotated[Session, Depends(get_db)]) -> Any:
    """Manually add a new requirement (user explicit action)."""
    try:
        added = RequirementService.add_requirement(
            session=db,  # was: db=db
            job_id=body.job_id,
            requirement_id=body.id,
            text=body.text,
            kind=body.kind,
            user_confirmed=body.user_confirmed,
            normalized_skill_ids=body.normalized_skill_ids,
            evidence_ids=body.evidence_ids,
        )
        return _to_schema(added)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.patch("/{requirement_id}", response_model=JobRequirement)
def update_requirement(
    requirement_id: str,
    body: RequirementUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
) -> Any:
    """Edit or confirm a requirement (Gate G2)."""
    try:
        updated = RequirementService.update_requirement(
            session=db,
            requirement_id=requirement_id,
            text=body.text,
            kind=body.kind,
            user_confirmed=body.user_confirmed,
            normalized_skill_ids=body.normalized_skill_ids,
            evidence_ids=body.evidence_ids,
        )
        return _to_schema(updated)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
