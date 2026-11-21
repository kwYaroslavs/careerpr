"""Unit tests for ChangeProposal lifecycle, review, apply,
idempotency, and conflict handling (T-020).
"""

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.db import Base
from app.domain.proposals import generate_r0_proposal
from app.domain.schemas import (
    BaseResume,
    Fact,
    ProposalStatus,
    ResumeItem,
    Verification,
)
from app.domain.services.proposals import ProposalService
from app.domain.services.resume import ResumeService
from app.validators.core import ValidationContext


@pytest.fixture
def db_session() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()
    Base.metadata.drop_all(engine)


def test_proposal_lifecycle_normal(db_session: Session) -> None:
    resume = BaseResume(
        id="br_1",
        profile_id="prof_1",
        version=1,
        items=[ResumeItem(id="i1", text="Software Engineer", fact_ids=["f1"], priority=1)],
    )
    ResumeService.create_base_resume(db_session, resume)

    fact = Fact(
        id="f1",
        text="Software Engineer with Python",
        category="experience",
        verification_status=Verification.CONFIRMED,
        risk_tier="low",
    )

    ctx = ValidationContext(resume=resume, facts=[fact])

    proposal = generate_r0_proposal(
        run_id="run_1",
        resume=resume,
        item=resume.items[0],
        new_priority=2,
        requirement_ids=["req_1"],
        fact_ids=["f1"],
    )

    db_cp = ProposalService.create_proposal(db_session, proposal, ctx)
    assert db_cp.status == ProposalStatus.PENDING
    assert db_cp.dedupe_key is not None

    # Test idempotency / dedupe
    db_cp_duplicate = ProposalService.create_proposal(db_session, proposal, ctx)
    assert db_cp_duplicate.id == db_cp.id

    # Approve proposal
    approved = ProposalService.update_status(db_session, db_cp.id, ProposalStatus.APPROVED)
    assert approved.status == ProposalStatus.APPROVED

    # Apply proposal
    applied = ProposalService.apply_proposal(db_session, db_cp.id, resume.id)
    assert applied.status == ProposalStatus.APPLIED

    updated_resume = ResumeService.get_base_resume(db_session, resume.id)
    assert updated_resume.version == 2


def test_proposal_expected_version_conflict(db_session: Session) -> None:
    resume = BaseResume(
        id="br_2",
        profile_id="prof_1",
        version=1,
        items=[ResumeItem(id="i1", text="Engineer", fact_ids=["f1"], priority=1)],
    )
    ResumeService.create_base_resume(db_session, resume)

    fact = Fact(
        id="f1",
        text="Engineer",
        category="experience",
        verification_status=Verification.CONFIRMED,
        risk_tier="low",
    )

    ctx = ValidationContext(resume=resume, facts=[fact])

    proposal = generate_r0_proposal(
        run_id="run_1",
        resume=resume,
        item=resume.items[0],
        new_priority=2,
        requirement_ids=["req_1"],
        fact_ids=["f1"],
    )

    db_cp = ProposalService.create_proposal(db_session, proposal, ctx)
    ProposalService.update_status(db_session, db_cp.id, ProposalStatus.APPROVED)

    # Bump resume version externally to simulate concurrent edit / stale version conflict
    ResumeService.update_base_resume(db_session, resume.id, {"priority": 10}, expected_version=1)

    with pytest.raises(ValueError, match="Conflict: expected version"):
        ProposalService.apply_proposal(db_session, db_cp.id, resume.id)

    db_cp_refreshed = ProposalService.get_proposal(db_session, db_cp.id)
    assert db_cp_refreshed.status == ProposalStatus.CONFLICT
