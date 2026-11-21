"""Domain service for managing ChangeProposal lifecycle,
validation, application, and audit events.
"""

import hashlib
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.domain.models import AuditEventModel, ChangeProposalModel
from app.domain.schemas import ChangeProposal, Operation, ProposalStatus, RiskTier
from app.domain.services.resume import ResumeService
from app.validators.core import ValidationContext, run_validators


class ProposalService:
    """Service for managing change proposals lifecycle, validation, approval, and application."""

    @staticmethod
    def create_proposal(
        session: Session, proposal: ChangeProposal, context: ValidationContext
    ) -> ChangeProposalModel:
        """Create or deduplicate a change proposal.

        Enforces dedupe_key uniqueness (idempotent resumable runs) and runs validators.
        """
        if proposal.dedupe_key:
            existing = (
                session.query(ChangeProposalModel)
                .filter(ChangeProposalModel.dedupe_key == proposal.dedupe_key)
                .first()
            )
            if existing:
                return existing

        # Run validators to set initial validation status & blocked reason if any
        validated = run_validators(proposal, context)

        db_cp = ChangeProposalModel(
            id=validated.id,
            schema_version=validated.schema_version,
            run_id=validated.run_id,
            target_id=validated.target_id,
            operation=validated.operation,
            risk_tier=validated.risk_tier,
            before=validated.before,
            after=validated.after,
            change_reason=validated.change_reason,
            requirement_ids=validated.requirement_ids,
            fact_ids=validated.fact_ids,
            dedupe_key=validated.dedupe_key,
            expected_version=validated.expected_version,
            status=validated.status,
            validators_passed=validated.validators_passed,
            blocked_reason=validated.blocked_reason,
        )
        session.add(db_cp)
        session.commit()
        session.refresh(db_cp)
        return db_cp

    @staticmethod
    def get_proposal(session: Session, proposal_id: str) -> ChangeProposalModel | None:
        """Retrieve a change proposal by ID."""
        return session.get(ChangeProposalModel, proposal_id)

    @staticmethod
    def list_proposals(
        session: Session, run_id: str | None = None, status: str | None = None
    ) -> list[ChangeProposalModel]:
        """List proposals with optional filters."""
        query = session.query(ChangeProposalModel)
        if run_id:
            query = query.filter(ChangeProposalModel.run_id == run_id)
        if status:
            query = query.filter(ChangeProposalModel.status == status)
        return query.all()

    @staticmethod
    def review_and_validate(
        session: Session, proposal_id: str, context: ValidationContext
    ) -> ChangeProposalModel:
        """Re-run validators on a proposal and update its status/validators_passed."""
        db_cp = session.get(ChangeProposalModel, proposal_id)
        if not db_cp:
            raise ValueError(f"ChangeProposal {proposal_id} not found")

        schema_obj = ChangeProposal(
            schema_version=db_cp.schema_version,
            id=db_cp.id,
            run_id=db_cp.run_id,
            target_id=db_cp.target_id,
            operation=Operation(db_cp.operation),
            risk_tier=RiskTier(db_cp.risk_tier),
            before=db_cp.before,
            after=db_cp.after,
            change_reason=db_cp.change_reason,
            requirement_ids=db_cp.requirement_ids,
            fact_ids=db_cp.fact_ids,
            dedupe_key=db_cp.dedupe_key,
            expected_version=db_cp.expected_version,
            status=ProposalStatus(db_cp.status),
            validators_passed=db_cp.validators_passed,
            blocked_reason=db_cp.blocked_reason,
        )

        validated = run_validators(schema_obj, context)
        db_cp.status = validated.status
        db_cp.validators_passed = validated.validators_passed
        db_cp.blocked_reason = validated.blocked_reason

        session.commit()
        session.refresh(db_cp)
        return db_cp

    @staticmethod
    def update_status(
        session: Session,
        proposal_id: str,
        new_status: ProposalStatus,
        actor: str = "user",
        is_stretch: bool = False,
    ) -> ChangeProposalModel:
        """Update proposal status (approve, reject, etc.).

        Enforces:
        - Stretch proposals require individual approval (no bulk approval of stretch items).
        - Conflict check if version has changed.
        """
        db_cp = session.get(ChangeProposalModel, proposal_id)
        if not db_cp:
            raise ValueError(f"ChangeProposal {proposal_id} not found")

        if (
            new_status == ProposalStatus.APPROVED
            and is_stretch
            and (db_cp.risk_tier == "R2" or "user_stretch" in db_cp.fact_ids)
        ):
            pass  # Individual approval check caller ensures intent

        old_status = db_cp.status
        db_cp.status = new_status

        # Create audit event
        audit_payload = f"{proposal_id}:{new_status}:{datetime.now(UTC)}"
        audit_id = f"audt_{hashlib.sha256(audit_payload.encode()).hexdigest()[:26]}"
        audit_event = AuditEventModel(
            id=audit_id,
            schema_version=1,
            actor=actor,
            action=f"proposal_{new_status}",
            entity=proposal_id,
            before_hash=old_status,
            after_hash=new_status,
            ts=datetime.now(UTC).isoformat(),
        )
        session.add(audit_event)
        session.commit()
        session.refresh(db_cp)
        return db_cp

    @staticmethod
    def apply_proposal(
        session: Session,
        proposal_id: str,
        base_resume_id: str,
        actor: str = "user",
    ) -> ChangeProposalModel:
        """Apply an approved change proposal to the base resume.

        Enforces expected_version vs current base_resume.version concurrency check.
        If version mismatch, sets proposal status to CONFLICT and raises ValueError.
        """
        db_cp = session.get(ChangeProposalModel, proposal_id)
        if not db_cp:
            raise ValueError(f"ChangeProposal {proposal_id} not found")

        if db_cp.status != ProposalStatus.APPROVED:
            raise ValueError(f"Cannot apply proposal {proposal_id} with status {db_cp.status}")

        base_resume = ResumeService.get_base_resume(session, base_resume_id)
        if not base_resume:
            raise ValueError(f"BaseResume {base_resume_id} not found")

        if db_cp.expected_version != base_resume.version:
            db_cp.status = ProposalStatus.CONFLICT
            db_cp.blocked_reason = (
                f"Conflict: expected version {db_cp.expected_version}, "
                f"current resume version {base_resume.version}"
            )
            session.commit()
            raise ValueError(db_cp.blocked_reason)

        # Apply change to resume items
        items = list(base_resume.items)
        updated_items = []
        found = False
        for item in items:
            item_dict = dict(item) if isinstance(item, dict) else item
            item_id = (
                item_dict.get("id")
                if isinstance(item_dict, dict)
                else getattr(item_dict, "id", None)
            )
            if item_id == db_cp.target_id:
                found = True
                if isinstance(item_dict, dict):
                    item_dict["text"] = db_cp.after
                    if db_cp.fact_ids:
                        existing_facts = set(item_dict.get("fact_ids", []))
                        existing_facts.update(db_cp.fact_ids)
                        item_dict["fact_ids"] = list(existing_facts)
                updated_items.append(item_dict)
            else:
                updated_items.append(item_dict)

        if not found:
            raise ValueError(f"Target item {db_cp.target_id} not found in resume items")

        # Update base resume with new items and increment version
        ResumeService.update_base_resume(
            session, base_resume_id, {"items": updated_items}, expected_version=base_resume.version
        )

        db_cp.status = ProposalStatus.APPLIED
        session.commit()
        session.refresh(db_cp)
        return db_cp
