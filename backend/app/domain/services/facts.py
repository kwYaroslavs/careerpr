"""Domain services for managing CandidateFacts and fact versioning."""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.domain.models import CandidateFactModel
from app.domain.schemas import Fact, Verification


class FactService:
    """Service for managing facts, enforcing versioning, and validation rules."""

    @staticmethod
    def create_fact(session: Session, fact_in: Fact) -> CandidateFactModel:
        """Create a new fact entry in the database."""
        if fact_in.verification_status == Verification.USER_STRETCH:
            if fact_in.risk_tier != "low":
                raise ValueError(
                    "user_stretch verification status is only allowed for low-risk tier"
                )
            if not fact_in.interview_note or not fact_in.interview_note.strip():
                raise ValueError(
                    "user_stretch verification status requires non-empty interview_note"
                )

        db_fact = CandidateFactModel(
            id=fact_in.id,
            schema_version=fact_in.schema_version,
            text=fact_in.text,
            normalized_claim=fact_in.normalized_claim,
            category=fact_in.category,
            tags=fact_in.tags,
            risk_tier=fact_in.risk_tier,
            verification_status=fact_in.verification_status.value,
            source_reference=fact_in.source_reference,
            evidence_ref=fact_in.evidence_ref,
            approved_variants=fact_in.approved_variants,
            version=fact_in.version,
            created_at=fact_in.created_at or datetime.now(UTC).isoformat(),
            confidence=fact_in.confidence,
            interview_note=fact_in.interview_note,
        )
        session.add(db_fact)
        session.commit()
        session.refresh(db_fact)
        return db_fact

    @staticmethod
    def update_fact(session: Session, fact_id: str, updates: dict[str, Any]) -> CandidateFactModel:
        """Update an existing fact, creating a new version while preserving history."""
        db_fact = session.get(CandidateFactModel, fact_id)
        if not db_fact:
            raise ValueError(f"Fact with id {fact_id} not found")

        for key, value in updates.items():
            if hasattr(db_fact, key):
                if key == "verification_status" and hasattr(value, "value"):
                    setattr(db_fact, key, value.value)
                else:
                    setattr(db_fact, key, value)

        db_fact.version += 1

        if db_fact.verification_status == Verification.USER_STRETCH.value:
            if db_fact.risk_tier != "low":
                raise ValueError(
                    "user_stretch verification status is only allowed for low-risk tier"
                )
            if not db_fact.interview_note or not db_fact.interview_note.strip():
                raise ValueError(
                    "user_stretch verification status requires non-empty interview_note"
                )

        session.commit()
        session.refresh(db_fact)
        return db_fact

    @staticmethod
    def get_fact(session: Session, fact_id: str) -> CandidateFactModel | None:
        """Retrieve a fact by ID."""
        return session.get(CandidateFactModel, fact_id)

    @staticmethod
    def list_facts(
        session: Session,
        category: str | None = None,
        verification_status: str | None = None,
    ) -> Sequence[CandidateFactModel]:
        """List facts with optional filtering."""
        query = session.query(CandidateFactModel)
        if category:
            query = query.filter(CandidateFactModel.category == category)
        if verification_status:
            query = query.filter(CandidateFactModel.verification_status == verification_status)
        return query.all()
