"""API endpoints for ChangeProposal lifecycle, review, and application."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.domain.schemas import ProposalStatus
from app.domain.services.proposals import ProposalService

router = APIRouter(prefix="/proposals", tags=["proposals"])


class ProposalStatusUpdateRequest(BaseModel):
    status: ProposalStatus
    actor: str = "user"
    is_stretch: bool = False


class ProposalApplyRequest(BaseModel):
    base_resume_id: str
    actor: str = "user"


@router.get("", response_model=list[dict[str, Any]])
def list_proposals(
    db: Annotated[Session, Depends(get_db)],
    run_id: str | None = None,
    status: str | None = None,
) -> Any:
    """List change proposals with optional filters."""
    proposals = ProposalService.list_proposals(db, run_id=run_id, status=status)
    return [
        {
            "id": p.id,
            "schema_version": p.schema_version,
            "run_id": p.run_id,
            "target_id": p.target_id,
            "operation": p.operation,
            "risk_tier": p.risk_tier,
            "before": p.before,
            "after": p.after,
            "change_reason": p.change_reason,
            "requirement_ids": p.requirement_ids,
            "fact_ids": p.fact_ids,
            "dedupe_key": p.dedupe_key,
            "expected_version": p.expected_version,
            "status": p.status,
            "validators_passed": p.validators_passed,
            "blocked_reason": p.blocked_reason,
        }
        for p in proposals
    ]


@router.get("/{proposal_id}", response_model=dict[str, Any])
def get_proposal(proposal_id: str, db: Annotated[Session, Depends(get_db)]) -> Any:
    """Retrieve a specific change proposal by ID."""
    p = ProposalService.get_proposal(db, proposal_id)
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found")
    return {
        "id": p.id,
        "schema_version": p.schema_version,
        "run_id": p.run_id,
        "target_id": p.target_id,
        "operation": p.operation,
        "risk_tier": p.risk_tier,
        "before": p.before,
        "after": p.after,
        "change_reason": p.change_reason,
        "requirement_ids": p.requirement_ids,
        "fact_ids": p.fact_ids,
        "dedupe_key": p.dedupe_key,
        "expected_version": p.expected_version,
        "status": p.status,
        "validators_passed": p.validators_passed,
        "blocked_reason": p.blocked_reason,
    }


@router.patch("/{proposal_id}/status", response_model=dict[str, Any])
def update_proposal_status(
    proposal_id: str,
    body: ProposalStatusUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
) -> Any:
    """Update proposal status (approve, reject).

    Rule: LLM never changes status or applies proposals; actions are performed by user/backend.
    """
    try:
        p = ProposalService.update_status(
            db, proposal_id, body.status, actor=body.actor, is_stretch=body.is_stretch
        )
        return {
            "id": p.id,
            "status": p.status,
            "blocked_reason": p.blocked_reason,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/{proposal_id}/apply", response_model=dict[str, Any])
def apply_proposal(
    proposal_id: str,
    body: ProposalApplyRequest,
    db: Annotated[Session, Depends(get_db)],
) -> Any:
    """Apply an approved proposal to the base resume with version conflict check."""
    try:
        p = ProposalService.apply_proposal(db, proposal_id, body.base_resume_id, actor=body.actor)
        return {
            "id": p.id,
            "status": p.status,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
