"""Unit tests for R0 and R1 deterministic proposal generation (T-018)."""

from app.domain.proposals import generate_r0_proposal, generate_r1_proposal
from app.domain.schemas import (
    Fact,
    Operation,
    ProposalStatus,
    Resume,
    ResumeItem,
    RiskTier,
    Verification,
)
from app.validators import ValidationContext, run_validators


def test_generate_r0_proposal_normal() -> None:
    resume = Resume(
        id="res_1",
        profile_id="prof_1",
        version=1,
        items=[ResumeItem(id="i1", text="Python dev", fact_ids=["f1"])],
    )
    item = resume.items[0]

    proposal = generate_r0_proposal(
        run_id="run_1",
        resume=resume,
        item=item,
        new_priority=1,
        requirement_ids=["req_1"],
        fact_ids=["f1"],
    )

    assert proposal.operation == Operation.REORDER
    assert proposal.risk_tier == RiskTier.R0
    assert proposal.target_id == "i1"
    assert proposal.expected_version == 1
    assert proposal.status == ProposalStatus.PENDING
    assert proposal.requirement_ids == ["req_1"]
    assert proposal.fact_ids == ["f1"]

    ctx = ValidationContext(resume=resume, facts=[])
    fact = Fact(
        id="f1",
        text="Python experience",
        risk_tier="low",
        verification_status=Verification.SOURCE_BACKED,
    )
    ctx.facts = [fact]

    result = run_validators(proposal, ctx)
    assert result.status == ProposalStatus.PENDING, result.blocked_reason


def test_generate_r1_proposal_normal() -> None:
    resume = Resume(
        id="res_1",
        profile_id="prof_1",
        version=2,
        items=[ResumeItem(id="i1", text="Backend dev", fact_ids=["f1"])],
    )
    item = resume.items[0]

    proposal = generate_r1_proposal(
        run_id="run_1",
        resume=resume,
        item=item,
        chosen_variant="Senior Backend Engineer with Python and FastAPI",
        requirement_ids=["req_1"],
        fact_ids=["f1"],
    )

    assert proposal.operation == Operation.PICK_VARIANT
    assert proposal.risk_tier == RiskTier.R1
    assert proposal.target_id == "i1"
    assert proposal.expected_version == 2
    assert proposal.after == "Senior Backend Engineer with Python and FastAPI"
    assert proposal.status == ProposalStatus.PENDING

    fact = Fact(
        id="f1",
        text="Senior Backend Engineer with Python and FastAPI",
        risk_tier="low",
        verification_status=Verification.SOURCE_BACKED,
        approved_variants=["Senior Backend Engineer with Python and FastAPI"],
    )
    ctx = ValidationContext(resume=resume, facts=[fact])

    result = run_validators(proposal, ctx)
    assert result.status == ProposalStatus.PENDING, result.blocked_reason


def test_proposal_idempotency_and_dedupe() -> None:
    resume = Resume(
        id="res_1",
        profile_id="prof_1",
        version=1,
        items=[ResumeItem(id="i1", text="Dev", fact_ids=["f1"])],
    )
    item = resume.items[0]

    p1 = generate_r0_proposal("run_1", resume, item, 1, ["req_1"], ["f1"])
    p2 = generate_r0_proposal("run_1", resume, item, 1, ["req_1"], ["f1"])

    assert p1.dedupe_key == p2.dedupe_key
    assert p1.id == p2.id
