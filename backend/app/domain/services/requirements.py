"""Domain services for managing job requirements (T-010)."""

from sqlalchemy.orm import Session

from app.domain.models import JobPostingModel, JobRequirementModel
from app.domain.schemas import JobRequirement, RequirementKind


class RequirementService:
    """Service for managing job requirements, editing, adding, and confirming (gate G2)."""

    @staticmethod
    def get_job_requirements(session: Session, job_id: str) -> list[JobRequirementModel]:
        """Retrieve all requirements for a specific job posting."""
        return session.query(JobRequirementModel).filter(JobRequirementModel.job_id == job_id).all()

    @staticmethod
    def get_requirement(session: Session, requirement_id: str) -> JobRequirementModel | None:
        """Retrieve a single requirement by ID."""
        return session.get(JobRequirementModel, requirement_id)

    @staticmethod
    def save_requirements(
        session: Session, job_id: str, requirements: list[JobRequirement]
    ) -> list[JobRequirementModel]:
        """Save extracted or added requirements for a job."""
        job = session.get(JobPostingModel, job_id)
        if not job:
            raise ValueError(f"Job posting not found: {job_id}")

        saved = []
        for req in requirements:
            existing = session.get(JobRequirementModel, req.id)
            if existing:
                existing.text = req.text
                existing.kind = (
                    req.kind.value if isinstance(req.kind, RequirementKind) else req.kind
                )
                existing.normalized_skill_ids = req.normalized_skill_ids
                existing.evidence_ids = req.evidence_ids
                existing.user_confirmed = req.user_confirmed
                saved.append(existing)
            else:
                db_req = JobRequirementModel(
                    id=req.id,
                    schema_version=req.schema_version,
                    job_id=job_id,
                    text=req.text,
                    kind=(req.kind.value if isinstance(req.kind, RequirementKind) else req.kind),
                    normalized_skill_ids=req.normalized_skill_ids,
                    evidence_ids=req.evidence_ids,
                    user_confirmed=req.user_confirmed,
                )
                session.add(db_req)
                saved.append(db_req)
        session.commit()
        for r in saved:
            session.refresh(r)
        return saved

    @staticmethod
    def update_requirement(
        session: Session,
        requirement_id: str,
        text: str | None = None,
        kind: RequirementKind | str | None = None,
        user_confirmed: bool | None = None,
        normalized_skill_ids: list[str] | None = None,
        evidence_ids: list[str] | None = None,
    ) -> JobRequirementModel:
        """Update or confirm a specific requirement (explicit user action)."""
        db_req = session.get(JobRequirementModel, requirement_id)
        if not db_req:
            raise ValueError(f"Requirement not found: {requirement_id}")

        if text is not None:
            db_req.text = text
        if kind is not None:
            db_req.kind = kind.value if isinstance(kind, RequirementKind) else kind
        if user_confirmed is not None:
            db_req.user_confirmed = user_confirmed
        if normalized_skill_ids is not None:
            db_req.normalized_skill_ids = normalized_skill_ids
        if evidence_ids is not None:
            db_req.evidence_ids = evidence_ids

        session.commit()
        session.refresh(db_req)
        return db_req

    @staticmethod
    def add_requirement(
        session: Session,
        job_id: str,
        requirement_id: str,
        text: str,
        kind: RequirementKind | str = RequirementKind.MUST,
        user_confirmed: bool = True,
        normalized_skill_ids: list[str] | None = None,
        evidence_ids: list[str] | None = None,
    ) -> JobRequirementModel:
        """Manually add a new requirement by user."""
        job = session.get(JobPostingModel, job_id)
        if not job:
            raise ValueError(f"Job posting not found: {job_id}")

        existing = session.get(JobRequirementModel, requirement_id)
        if existing:
            raise ValueError(f"Requirement ID already exists: {requirement_id}")

        kind_val = kind.value if isinstance(kind, RequirementKind) else kind
        db_req = JobRequirementModel(
            id=requirement_id,
            job_id=job_id,
            text=text,
            kind=kind_val,
            user_confirmed=user_confirmed,
            normalized_skill_ids=normalized_skill_ids or [],
            evidence_ids=evidence_ids or [],
        )
        session.add(db_req)
        session.commit()
        session.refresh(db_req)
        return db_req
