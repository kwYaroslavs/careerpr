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

BEFORE = "Software engineer at OldCorp, working since 2020."


def test_v5_protected_unchanged_success() -> None:
    resume = Resume(
        id="r1",
        items=[ResumeItem(id="i1", text=BEFORE)],
        protected={"email": "test@example.com", "phone": "+1234567890"},
    )
    facts = [
        Fact(
            id="f1",
            text="Software engineer at OldCorp, working since 2020, email: test@example.com.",  # noqa: E501
        )
    ]
    ctx = ValidationContext(resume=resume, facts=facts)
    proposal = ChangeProposal(
        id="p1",
        run_id="run1",
        target_id="i1",
        operation=Operation.REWRITE,
        risk_tier=RiskTier.R1,
        before=BEFORE,
        after="Senior software engineer at OldCorp, working since 2020, contact: test@example.com.",
        change_reason="seniority",
        fact_ids=["f1"],
        expected_version=1,
    )
    result = run_validators(proposal, ctx)
    assert result.status == ProposalStatus.PENDING
    assert "V5" in result.validators_passed


def test_v5_protected_altered_blocked() -> None:
    resume = Resume(
        id="r1",
        items=[ResumeItem(id="i1", text=BEFORE)],
        protected={"email": "test@example.com"},
    )
    facts = [Fact(id="f1", text="Software engineer at OldCorp.")]
    ctx = ValidationContext(resume=resume, facts=facts)
    proposal = ChangeProposal(
        id="p1",
        run_id="run1",
        target_id="i1",
        operation=Operation.REWRITE,
        risk_tier=RiskTier.R1,
        before="Software engineer with email test@example.com.",
        after="Software engineer with email altered@example.com.",
        change_reason="change email",
        fact_ids=["f1"],
        expected_version=1,
    )
    result = run_validators(proposal, ctx)
    assert result.status == ProposalStatus.BLOCKED
    assert "V5" in (result.blocked_reason or "")


def test_v6_no_placeholders_success() -> None:
    resume = Resume(
        id="r1",
        items=[ResumeItem(id="i1", text=BEFORE)],
    )
    facts = [Fact(id="f1", text="Clean engineering text.")]
    ctx = ValidationContext(resume=resume, facts=facts)
    proposal = ChangeProposal(
        id="p1",
        run_id="run1",
        target_id="i1",
        operation=Operation.REWRITE,
        risk_tier=RiskTier.R1,
        before=BEFORE,
        after="Clean engineering text without placeholders.",
        change_reason="clean rewrite",
        fact_ids=["f1"],
        expected_version=1,
    )
    result = run_validators(proposal, ctx)
    assert result.status == ProposalStatus.PENDING
    assert "V6" in result.validators_passed


def test_v6_placeholder_blocked() -> None:
    resume = Resume(
        id="r1",
        items=[ResumeItem(id="i1", text=BEFORE)],
    )
    facts = [Fact(id="f1", text="Clean engineering text.")]
    ctx = ValidationContext(resume=resume, facts=facts)
    for bad_text in [
        "Worked at [Company Name].",
        "Achieved {{metric}} growth.",
        "TODO: add more details",
        "TBD project",
        "lorem ipsum dolor sit amet",
    ]:
        proposal = ChangeProposal(
            id="p1",
            run_id="run1",
            target_id="i1",
            operation=Operation.REWRITE,
            risk_tier=RiskTier.R1,
            before=BEFORE,
            after=bad_text,
            change_reason="placeholder test",
            fact_ids=["f1"],
            expected_version=1,
        )
        result = run_validators(proposal, ctx)
        assert result.status == ProposalStatus.BLOCKED
        assert "V6" in (result.blocked_reason or "")


def test_v7_no_company_leak_success() -> None:
    resume = Resume(
        id="r1",
        items=[ResumeItem(id="i1", text=BEFORE)],
    )
    facts = [Fact(id="f1", text="Worked on internal systems.")]
    ctx = ValidationContext(
        resume=resume, facts=facts, other_companies={"CompetitorX", "StellarTech"}
    )
    proposal = ChangeProposal(
        id="p1",
        run_id="run1",
        target_id="i1",
        operation=Operation.REWRITE,
        risk_tier=RiskTier.R1,
        before=BEFORE,
        after="Worked on internal high-performance systems.",
        change_reason="safe rewrite",
        fact_ids=["f1"],
        expected_version=1,
    )
    result = run_validators(proposal, ctx)
    assert result.status == ProposalStatus.PENDING
    assert "V7" in result.validators_passed


def test_v7_company_leak_blocked() -> None:
    resume = Resume(
        id="r1",
        items=[ResumeItem(id="i1", text=BEFORE)],
    )
    facts = [Fact(id="f1", text="Worked on internal systems.")]
    ctx = ValidationContext(
        resume=resume, facts=facts, other_companies={"CompetitorX", "StellarTech"}
    )
    proposal = ChangeProposal(
        id="p1",
        run_id="run1",
        target_id="i1",
        operation=Operation.REWRITE,
        risk_tier=RiskTier.R1,
        before=BEFORE,
        after="Migrated legacy architecture from CompetitorX to modern stack.",
        change_reason="leak test",
        fact_ids=["f1"],
        expected_version=1,
    )
    result = run_validators(proposal, ctx)
    assert result.status == ProposalStatus.BLOCKED
    assert "V7" in (result.blocked_reason or "")
