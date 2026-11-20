"""Domain service for managing MasterResume, BaseResume,

and ResumeVersion with stable item IDs and content hashing.
"""

import hashlib
import json
from typing import Any

from sqlalchemy.orm import Session

from app.domain.models import (
    BaseResumeModel,
    MasterResumeModel,
    ResumeVersionModel,
)
from app.domain.schemas import BaseResume, MasterResume


class ResumeService:
    """Service for managing MasterResume, BaseResume, and immutable ResumeVersions."""

    @staticmethod
    def create_master_resume(session: Session, master_resume: MasterResume) -> MasterResumeModel:
        """Create an immutable source MasterResume."""
        db_mr = MasterResumeModel(
            id=master_resume.id,
            schema_version=master_resume.schema_version,
            profile_id=master_resume.profile_id,
            items=[item.model_dump() for item in master_resume.items],
            fact_references=master_resume.fact_references,
            protected=master_resume.protected,
        )
        session.add(db_mr)
        session.commit()
        session.refresh(db_mr)
        return db_mr

    @staticmethod
    def get_master_resume(session: Session, master_resume_id: str) -> MasterResumeModel | None:
        """Retrieve a MasterResume by ID."""
        return session.get(MasterResumeModel, master_resume_id)

    @staticmethod
    def create_base_resume(session: Session, base_resume: BaseResume) -> BaseResumeModel:
        """Create a BaseResume."""
        db_br = BaseResumeModel(
            id=base_resume.id,
            schema_version=base_resume.schema_version,
            profile_id=base_resume.profile_id,
            version=base_resume.version,
            items=[item.model_dump() for item in base_resume.items],
            priority=base_resume.priority,
            approved_variants=base_resume.approved_variants,
            fact_ids=base_resume.fact_ids,
            protected=base_resume.protected,
        )
        session.add(db_br)
        session.commit()
        session.refresh(db_br)
        return db_br

    @staticmethod
    def get_base_resume(session: Session, base_resume_id: str) -> BaseResumeModel | None:
        """Retrieve a BaseResume by ID."""
        return session.get(BaseResumeModel, base_resume_id)

    @staticmethod
    def update_base_resume(
        session: Session,
        base_resume_id: str,
        updates: dict[str, Any],
        expected_version: int | None = None,
    ) -> BaseResumeModel:
        """Update a BaseResume.

        Rule: Base edits never alter existing ResumeVersions or Snapshots.
        If expected_version is provided, enforce optimistic concurrency check.
        """
        db_br = session.get(BaseResumeModel, base_resume_id)
        if not db_br:
            raise ValueError(f"BaseResume {base_resume_id} not found")

        if expected_version is not None and db_br.version != expected_version:
            raise ValueError(
                f"Conflict: expected version {expected_version}, "
                f"but current version is {db_br.version}"
            )

        for key, value in updates.items():
            if hasattr(db_br, key):
                if key == "items" and isinstance(value, list):
                    setattr(
                        db_br,
                        key,
                        [
                            item.model_dump() if hasattr(item, "model_dump") else item
                            for item in value
                        ],
                    )
                else:
                    setattr(db_br, key, value)

        db_br.version += 1
        session.commit()
        session.refresh(db_br)
        return db_br

    @staticmethod
    def compute_content_hash(
        items: list[dict[str, Any]], profile_id: str = "", version: int = 1
    ) -> str:
        """Deterministically compute content_hash for resume items and metadata."""
        canonical_data: dict[str, Any] = {
            "profile_id": profile_id,
            "version": version,
            "items": sorted(
                [
                    {
                        "id": item.get("id"),
                        "text": item.get("text"),
                        "fact_ids": sorted(item.get("fact_ids", [])),
                        "priority": item.get("priority", 0),
                    }
                    for item in items
                ],
                key=lambda x: str(x["id"]),
            ),
        }
        encoded = json.dumps(canonical_data, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def create_resume_version(
        session: Session,
        version_id: str,
        base_resume_id: str,
    ) -> ResumeVersionModel:
        """Create an immutable ResumeVersion snapshot copy from a BaseResume.

        Computes content_hash deterministically and enforces immutability.
        """
        db_br = session.get(BaseResumeModel, base_resume_id)
        if not db_br:
            raise ValueError(f"BaseResume {base_resume_id} not found")

        content_hash = ResumeService.compute_content_hash(
            db_br.items, profile_id=db_br.profile_id, version=db_br.version
        )

        db_rv = ResumeVersionModel(
            id=version_id,
            schema_version=db_br.schema_version,
            base_resume_id=db_br.id,
            version=db_br.version,
            content_hash=content_hash,
            items=db_br.items,
        )
        session.add(db_rv)
        session.commit()
        session.refresh(db_rv)
        return db_rv

    @staticmethod
    def get_resume_version(session: Session, version_id: str) -> ResumeVersionModel | None:
        """Retrieve an immutable ResumeVersion by ID."""
        return session.get(ResumeVersionModel, version_id)
