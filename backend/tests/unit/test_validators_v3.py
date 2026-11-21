from app.domain.schemas import (
    ChangeProposal,
    Fact,
    FactAlias,
    Operation,
    ProposalStatus,
    Resume,
    ResumeItem,
    RiskTier,
    Verification,
)
from app.validators import ValidationContext, run_validators

BEFORE = "Developed Python microservices using PostgreSQL and Docker."


def test_v3_normal_allowed_entities() -> None:
    resume = Resume(
        id="r1",
        items=[ResumeItem(id="i1", text=BEFORE)],
    )
    facts = [
        Fact(
            id="f1",
            text="Developed Python microservices using PostgreSQL and Docker.",
        )
    ]
    ctx = ValidationContext(resume=resume, facts=facts)
    proposal = ChangeProposal(
        id="p1",
        run_id="run1",
        target_id="i1",
        operation=Operation.REWRITE,
        risk_tier=RiskTier.R2,
        before=BEFORE,
        after=("Built Python microservices backed by PostgreSQL and containerized with Docker."),
        change_reason="clarity",
        fact_ids=["f1"],
        expected_version=1,
    )
    result = run_validators(proposal, ctx)
    assert result.status == ProposalStatus.PENDING
    assert "V3" in result.validators_passed


def test_v3_blocked_new_entity() -> None:
    resume = Resume(
        id="r1",
        items=[ResumeItem(id="i1", text=BEFORE)],
    )
    facts = [
        Fact(
            id="f1",
            text="Developed Python microservices using PostgreSQL and Docker.",
        )
    ]
    ctx = ValidationContext(resume=resume, facts=facts)
    proposal = ChangeProposal(
        id="p1",
        run_id="run1",
        target_id="i1",
        operation=Operation.REWRITE,
        risk_tier=RiskTier.R2,
        before=BEFORE,
        after=("Developed Python microservices using PostgreSQL, Docker, and Kubernetes."),
        change_reason="adding kubernetes",
        fact_ids=["f1"],
        expected_version=1,
    )
    result = run_validators(proposal, ctx)
    assert result.status == ProposalStatus.BLOCKED
    assert "V3" in (result.blocked_reason or "")


def test_v3_reviewed_aliases_allowed() -> None:
    resume = Resume(
        id="r1",
        items=[ResumeItem(id="i1", text=BEFORE)],
    )
    facts = [
        Fact(
            id="f1",
            text="Developed Python microservices using PostgreSQL and Docker.",
        )
    ]
    aliases = [
        FactAlias(
            canonical_skill_id="skill_k8s",
            alias="K8s",
            reviewed=True,
        )
    ]
    ctx = ValidationContext(resume=resume, facts=facts, aliases=aliases)
    proposal = ChangeProposal(
        id="p1",
        run_id="run1",
        target_id="i1",
        operation=Operation.REWRITE,
        risk_tier=RiskTier.R2,
        before=BEFORE,
        after=("Developed Python microservices using PostgreSQL, Docker, and K8s."),
        change_reason="using reviewed alias",
        fact_ids=["f1"],
        expected_version=1,
    )
    result = run_validators(proposal, ctx)
    assert result.status == ProposalStatus.PENDING
    assert "V3" in result.validators_passed


def test_v3_unreviewed_alias_blocked() -> None:
    resume = Resume(
        id="r1",
        items=[ResumeItem(id="i1", text=BEFORE)],
    )
    facts = [
        Fact(
            id="f1",
            text="Developed Python microservices using PostgreSQL and Docker.",
        )
    ]
    aliases = [
        FactAlias(
            canonical_skill_id="skill_k8s",
            alias="K8s",
            reviewed=False,
        )
    ]
    ctx = ValidationContext(resume=resume, facts=facts, aliases=aliases)
    proposal = ChangeProposal(
        id="p1",
        run_id="run1",
        target_id="i1",
        operation=Operation.REWRITE,
        risk_tier=RiskTier.R2,
        before=BEFORE,
        after=("Developed Python microservices using PostgreSQL, Docker, and K8s."),
        change_reason="using unreviewed alias",
        fact_ids=["f1"],
        expected_version=1,
    )
    result = run_validators(proposal, ctx)
    assert result.status == ProposalStatus.BLOCKED


def test_v3_stretch_low_risk_tool_allowed() -> None:
    resume = Resume(
        id="r1",
        items=[ResumeItem(id="i1", text=BEFORE)],
    )
    facts = [
        Fact(
            id="f1",
            text="Developed Python microservices using PostgreSQL and Docker.",
            verification_status=Verification.USER_STRETCH,
            risk_tier="low",
            interview_note="Familiar with Redis from side projects",
        )
    ]
    ctx = ValidationContext(resume=resume, facts=facts)
    proposal = ChangeProposal(
        id="p1",
        run_id="run1",
        target_id="i1",
        operation=Operation.REWRITE,
        risk_tier=RiskTier.R2,
        before=BEFORE,
        after=("Developed Python microservices using PostgreSQL, Docker, and Redis."),
        change_reason="stretch tool",
        fact_ids=["f1"],
        expected_version=1,
    )
    result = run_validators(proposal, ctx)
    assert result.status == ProposalStatus.PENDING
    assert "V3" in result.validators_passed


def test_v3_stretch_prohibited_role_company_blocked() -> None:
    resume = Resume(
        id="r1",
        items=[ResumeItem(id="i1", text=BEFORE)],
    )
    facts = [
        Fact(
            id="f1",
            text="Developed Python microservices using PostgreSQL and Docker.",
            verification_status=Verification.USER_STRETCH,
            risk_tier="low",
            interview_note="Tested stretch policy",
        )
    ]
    ctx = ValidationContext(resume=resume, facts=facts)
    proposal = ChangeProposal(
        id="p1",
        run_id="run1",
        target_id="i1",
        operation=Operation.REWRITE,
        risk_tier=RiskTier.R2,
        before=BEFORE,
        after=("Led team as Engineering Manager at Google using PostgreSQL and Docker."),
        change_reason="adversarial stretch",
        fact_ids=["f1"],
        expected_version=1,
    )
    result = run_validators(proposal, ctx)
    assert result.status == ProposalStatus.BLOCKED
    assert "V3" in (result.blocked_reason or "")
