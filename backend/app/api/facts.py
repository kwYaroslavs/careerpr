"""API endpoints for Fact Base management."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.domain.schemas import Fact, Verification
from app.domain.services.facts import FactService

router = APIRouter(prefix="/facts", tags=["facts"])


class FactCreateRequest(BaseModel):
    id: str
    text: str
    normalized_claim: str | None = None
    category: str = "general"
    tags: list[str] = Field(default_factory=list)
    risk_tier: str = "low"
    verification_status: Verification = Verification.UNVERIFIED
    source_reference: str | None = None
    evidence_ref: str | None = None
    approved_variants: list[str] = Field(default_factory=list)
    confidence: float | None = None
    interview_note: str | None = None


class FactUpdateRequest(BaseModel):
    text: str | None = None
    normalized_claim: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    risk_tier: str | None = None
    verification_status: Verification | None = None
    source_reference: str | None = None
    evidence_ref: str | None = None
    approved_variants: list[str] | None = None
    confidence: float | None = None
    interview_note: str | None = None


@router.post("", response_model=Fact, status_code=status.HTTP_201_CREATED)
def create_fact(body: FactCreateRequest, db: Annotated[Session, Depends(get_db)]) -> Any:
    """Create a new fact in the Fact Base."""
    try:
        fact_obj = Fact(
            id=body.id,
            text=body.text,
            normalized_claim=body.normalized_claim,
            category=body.category,
            tags=body.tags,
            risk_tier=body.risk_tier,
            verification_status=body.verification_status,
            source_reference=body.source_reference,
            evidence_ref=body.evidence_ref,
            approved_variants=body.approved_variants,
            confidence=body.confidence,
            interview_note=body.interview_note,
        )
        created = FactService.create_fact(db, fact_obj)
        return Fact(
            schema_version=created.schema_version,
            id=created.id,
            text=created.text,
            normalized_claim=created.normalized_claim,
            category=created.category,
            tags=created.tags,
            risk_tier=created.risk_tier,
            verification_status=Verification(created.verification_status),
            source_reference=created.source_reference,
            evidence_ref=created.evidence_ref,
            approved_variants=created.approved_variants,
            version=created.version,
            created_at=created.created_at,
            confidence=created.confidence,
            interview_note=created.interview_note,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/{fact_id}", response_model=Fact)
def get_fact(fact_id: str, db: Annotated[Session, Depends(get_db)]) -> Any:
    """Retrieve a specific fact by ID."""
    fact_model = FactService.get_fact(db, fact_id)
    if not fact_model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fact not found")
    return Fact(
        schema_version=fact_model.schema_version,
        id=fact_model.id,
        text=fact_model.text,
        normalized_claim=fact_model.normalized_claim,
        category=fact_model.category,
        tags=fact_model.tags,
        risk_tier=fact_model.risk_tier,
        verification_status=Verification(fact_model.verification_status),
        source_reference=fact_model.source_reference,
        evidence_ref=fact_model.evidence_ref,
        approved_variants=fact_model.approved_variants,
        version=fact_model.version,
        created_at=fact_model.created_at,
        confidence=fact_model.confidence,
        interview_note=fact_model.interview_note,
    )


@router.put("/{fact_id}", response_model=Fact)
def update_fact(
    fact_id: str, body: FactUpdateRequest, db: Annotated[Session, Depends(get_db)]
) -> Any:
    """Update an existing fact, creating a new version."""
    try:
        updates = {k: v for k, v in body.model_dump().items() if v is not None}
        updated = FactService.update_fact(db, fact_id, updates)
        return Fact(
            schema_version=updated.schema_version,
            id=updated.id,
            text=updated.text,
            normalized_claim=updated.normalized_claim,
            category=updated.category,
            tags=updated.tags,
            risk_tier=updated.risk_tier,
            verification_status=Verification(updated.verification_status),
            source_reference=updated.source_reference,
            evidence_ref=updated.evidence_ref,
            approved_variants=updated.approved_variants,
            version=updated.version,
            created_at=updated.created_at,
            confidence=updated.confidence,
            interview_note=updated.interview_note,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("", response_model=list[Fact])
def list_facts(
    db: Annotated[Session, Depends(get_db)],
    category: str | None = None,
    verification_status: str | None = None,
) -> Any:
    """List facts with optional filters."""
    facts = FactService.list_facts(db, category=category, verification_status=verification_status)
    return [
        Fact(
            schema_version=f.schema_version,
            id=f.id,
            text=f.text,
            normalized_claim=f.normalized_claim,
            category=f.category,
            tags=f.tags,
            risk_tier=f.risk_tier,
            verification_status=Verification(f.verification_status),
            source_reference=f.source_reference,
            evidence_ref=f.evidence_ref,
            approved_variants=f.approved_variants,
            version=f.version,
            created_at=f.created_at,
            confidence=f.confidence,
            interview_note=f.interview_note,
        )
        for f in facts
    ]
