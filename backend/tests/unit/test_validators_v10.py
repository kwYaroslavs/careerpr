from app.domain.schemas import (
    ChangeProposal,
    Fact,
    Operation,
    ProposalStatus,
    Resume,
    ResumeItem,
    RiskTier,
)
from app.validators import ValidationContext, run_validators

BEFORE = "Developed Python backend applications and configured Docker containers."


def test_v10_transferable_framing_allowed() -> None:
    """Allowed transferable framing (R2) without claiming direct new title or ownership."""
    resume = Resume(
        id="r1",
        items=[ResumeItem(id="i1", text=BEFORE)],
    )
    facts = [
        Fact(
            id="f1",
            text="Developed Python backend applications and configured Docker containers.",
        )
    ]
    ctx = ValidationContext(
        resume=resume,
        facts=facts,
        vocabulary={"Python", "Docker", "CI", "CD", "Automated", "container"},
    )
    proposal = ChangeProposal(
        id="p1",
        run_id="run1",
        target_id="i1",
        operation=Operation.REWRITE,
        risk_tier=RiskTier.R2,
        before=BEFORE,
        after="Automated container deployments using Docker and CI/CD pipelines.",
        change_reason="framing transferable deployment experience",
        fact_ids=["f1"],
        expected_version=1,
    )
    result = run_validators(proposal, ctx)
    assert result.status == ProposalStatus.PENDING
    assert "V10" in result.validators_passed


def test_v10_transferable_blocked_direct_title() -> None:
    """V10 blocks presenting transferable experience as a direct new title/role not in facts."""
    resume = Resume(
        id="r1",
        items=[ResumeItem(id="i1", text=BEFORE)],
    )
    facts = [
        Fact(
            id="f1",
            text="Developed Python backend applications.",
        )
    ]
    ctx = ValidationContext(
        resume=resume,
        facts=facts,
        vocabulary={"Platform", "Engineer", "EnterpriseCorp", "infrastructure"},
    )
    proposal = ChangeProposal(
        id="p1",
        run_id="run1",
        target_id="i1",
        operation=Operation.REWRITE,
        risk_tier=RiskTier.R2,
        before=BEFORE,
        after="Worked as Platform Engineer at EnterpriseCorp building cloud infrastructure.",
        change_reason="adversarial transferable claim",
        fact_ids=["f1"],
        expected_version=1,
    )
    result = run_validators(proposal, ctx)
    assert result.status == ProposalStatus.BLOCKED
    assert "V10" in (result.blocked_reason or "")


def test_v10_transferable_blocked_ownership_claim() -> None:
    """V10 blocks claiming unbacked ownership or team building in new areas."""
    resume = Resume(
        id="r1",
        items=[ResumeItem(id="i1", text=BEFORE)],
    )
    facts = [
        Fact(
            id="f1",
            text="Developed Python backend applications.",
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
        after="Built a platform team and owned all infrastructure across AWS.",
        change_reason="adversarial ownership claim",
        fact_ids=["f1"],
        expected_version=1,
    )
    result = run_validators(proposal, ctx)
    assert result.status == ProposalStatus.BLOCKED
    assert "V10" in (result.blocked_reason or "")


def test_v10_edge_cases_and_fact_linked_titles() -> None:
    """V10 allows title/role if explicitly supported in the linked source facts."""
    resume = Resume(
        id="r1",
        items=[ResumeItem(id="i1", text=BEFORE)],
    )
    facts = [
        Fact(
            id="f1",
            text="Worked as Platform Engineer at OldCorp building infrastructure.",
        )
    ]
    ctx = ValidationContext(
        resume=resume,
        facts=facts,
        vocabulary={
            "Platform",
            "Engineer",
            "OldCorp",
            "infrastructure",
            "worked",
            "as",
            "building",
            "scalable",
        },
    )
    proposal = ChangeProposal(
        id="p1",
        run_id="run1",
        target_id="i1",
        operation=Operation.REWRITE,
        risk_tier=RiskTier.R2,
        before=BEFORE,
        after="Worked as Platform Engineer building scalable infrastructure.",
        change_reason="refining role description with backing fact",
        fact_ids=["f1"],
        expected_version=1,
    )
    result = run_validators(proposal, ctx)
    assert result.status == ProposalStatus.PENDING
    assert "V10" in result.validators_passed
