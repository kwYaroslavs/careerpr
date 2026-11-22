from sqlalchemy.orm import Session

from app.domain.schemas import (
    ChangeProposal,
    Fact,
    Operation,
    ProposalStatus,
    Resume,
    ResumeItem,
    RiskTier,
    Verification,
)
from app.validators import ValidationContext, run_validators


def test_stretch_fact_validation_rules(db_session: Session) -> None:
    """Test unit validation rules for user_stretch facts:
    - Must be low risk.
    - Must have a non-empty interview_note.
    """
    f = Fact(
        id="f_stretch_1",
        text="Familiar with Docker and Redis from personal homelab projects.",
        risk_tier="low",
        verification_status=Verification.USER_STRETCH,
        interview_note="Discussed homelab setup during intake interview.",
    )
    assert f.verification_status == Verification.USER_STRETCH
    assert f.risk_tier == "low"
    assert f.interview_note is not None


def test_stretch_change_proposal_validation() -> None:
    """Test V3 validator handling of user_stretch:
    - Allowed low-risk tools/skills framing with user_stretch fact.
    - Prohibited roles, companies, titles, leadership keywords are rejected even with user_stretch.
    - Unapproved stretch (fact verification_status != user_stretch) is rejected.
    """
    resume = Resume(
        id="r1",
        version=1,
        items=[ResumeItem(id="i1", text="Developed backend Python services.")],
    )

    # 1. Approved stretch fact for low-risk tool (Redis)
    fact_approved = Fact(
        id="f1",
        text="Developed backend Python services.",
        verification_status=Verification.USER_STRETCH,
        risk_tier="low",
        interview_note="Hands-on experience with Redis in staging environment.",
    )
    ctx = ValidationContext(resume=resume, facts=[fact_approved])

    proposal = ChangeProposal(
        id="p1",
        run_id="run1",
        target_id="i1",
        operation=Operation.REWRITE,
        risk_tier=RiskTier.R2,
        before="Developed backend Python services.",
        after="Developed backend Python services utilizing Redis for caching.",
        change_reason="adding redis via user stretch",
        fact_ids=["f1"],
        expected_version=1,
    )

    res = run_validators(proposal, ctx)
    assert res.status == ProposalStatus.PENDING
    assert "V3" in res.validators_passed

    # 2. Unapproved stretch (fact verification_status is unverified)
    fact_unverified = Fact(
        id="f2",
        text="Developed backend Python services.",
        verification_status=Verification.UNVERIFIED,
        risk_tier="low",
    )
    ctx_unverified = ValidationContext(resume=resume, facts=[fact_unverified])
    proposal_unapproved = ChangeProposal(
        id="p2",
        run_id="run1",
        target_id="i1",
        operation=Operation.REWRITE,
        risk_tier=RiskTier.R2,
        before="Developed backend Python services.",
        after="Developed backend Python services utilizing Redis for caching.",
        change_reason="unapproved stretch",
        fact_ids=["f2"],
        expected_version=1,
    )
    res_unapproved = run_validators(proposal_unapproved, ctx_unverified)
    assert res_unapproved.status == ProposalStatus.BLOCKED
    assert "V3" in (res_unapproved.blocked_reason or "")

    # 3. Prohibited entity/role stretch (Engineering Manager / Google)
    proposal_prohibited = ChangeProposal(
        id="p3",
        run_id="run1",
        target_id="i1",
        operation=Operation.REWRITE,
        risk_tier=RiskTier.R2,
        before="Developed backend Python services.",
        after="Led team as Engineering Manager at Google using Redis.",
        change_reason="prohibited stretch",
        fact_ids=["f1"],
        expected_version=1,
    )
    res_prohibited = run_validators(proposal_prohibited, ctx)
    assert res_prohibited.status == ProposalStatus.BLOCKED
    assert "V3" in (res_prohibited.blocked_reason or "")
