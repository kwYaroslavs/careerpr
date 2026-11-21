"""Unit tests for hard-constraint gate and fit bucket triage pipeline (T-013)."""

from app.domain.schemas import (
    CandidateProfile,
    Fact,
    JobRequirement,
    MatchBucket,
    RequirementKind,
    Verification,
)
from app.pipeline.triage import (
    evaluate_hard_constraints,
    triage_job,
)


def test_hard_constraints_pass_normal() -> None:
    profile = CandidateProfile(
        id="prof_1",
        name="Alice",
        hard_constraints={"visa": "US Citizen", "location": "Remote / US"},
    )
    reqs = [
        JobRequirement(
            id="req_1",
            text="Must be authorized to work in the US",
            kind=RequirementKind.HARD,
        ),
        JobRequirement(
            id="req_2",
            text="Python development",
            kind=RequirementKind.MUST,
        ),
    ]
    passed, reasons = evaluate_hard_constraints(profile, reqs)
    assert passed is True
    assert reasons == []


def test_hard_constraints_fail_blocked() -> None:
    profile = CandidateProfile(
        id="prof_1",
        name="Bob",
        hard_constraints={"visa": "EU Citizen - requires sponsorship"},
    )
    reqs = [
        JobRequirement(
            id="req_1",
            text="Must be authorized to work in the US without visa sponsorship",
            kind=RequirementKind.HARD,
        ),
    ]
    passed, reasons = evaluate_hard_constraints(profile, reqs)
    assert passed is False
    assert len(reasons) > 0


def test_fit_bucket_strong() -> None:
    profile = CandidateProfile(
        id="prof_1",
        name="Alice",
        hard_constraints={"location": "US", "visa": "US Citizen"},
    )
    reqs = [
        JobRequirement(
            id="req_1",
            text="Python programming",
            kind=RequirementKind.MUST,
            evidence_ids=["fact_1"],
        ),
    ]
    facts = [
        Fact(
            id="fact_1",
            text="Extensive Python programming experience",
            verification_status=Verification.SOURCE_BACKED,
        ),
    ]
    result = triage_job("job_1", 1, profile, reqs, facts)
    assert result.hard_constraint_pass is True
    assert result.bucket == MatchBucket.STRONG
    assert "Strong fit" in result.bucket_explanation


def test_fit_bucket_blocked_due_to_genuine_gap() -> None:
    profile = CandidateProfile(
        id="prof_1",
        name="Alice",
        hard_constraints={"location": "US", "visa": "US Citizen"},
    )
    reqs = [
        JobRequirement(id="req_1", text="Kubernetes infrastructure", kind=RequirementKind.MUST),
    ]
    facts = [
        Fact(
            id="fact_1",
            text="Python development",
            verification_status=Verification.SOURCE_BACKED,
        ),
    ]
    result = triage_job("job_1", 1, profile, reqs, facts)
    assert result.hard_constraint_pass is True
    assert result.bucket == MatchBucket.BLOCKED
    assert "genuine gap" in result.bucket_explanation.lower()


def test_fit_bucket_stretch_and_potential() -> None:
    profile = CandidateProfile(
        id="prof_1",
        name="Alice",
        hard_constraints={"location": "US", "visa": "US Citizen"},
    )
    reqs = [
        JobRequirement(id="req_1", text="Advanced Rust programming", kind=RequirementKind.NICE),
    ]
    facts = [
        Fact(
            id="fact_1",
            text="Python development",
            verification_status=Verification.SOURCE_BACKED,
        ),
    ]
    result = triage_job("job_1", 1, profile, reqs, facts)
    assert result.hard_constraint_pass is True
    assert result.bucket == MatchBucket.STRONG


def test_adversarial_hard_constraint_cannot_be_stretched() -> None:
    """Acceptance criteria: Hard constraints can never be stretched."""
    profile = CandidateProfile(
        id="prof_1",
        name="Charlie",
        hard_constraints={"location": "Europe", "visa": "No US work auth"},
    )
    reqs = [
        JobRequirement(
            id="req_hard",
            text="Must be US citizen located in New York",
            kind=RequirementKind.HARD,
        ),
    ]
    facts = [
        Fact(
            id="fact_1",
            text="Great engineer",
            verification_status=Verification.USER_STRETCH,
            interview_note="Willing to relocate",
        ),
    ]
    result = triage_job("job_1", 1, profile, reqs, facts)
    assert result.hard_constraint_pass is False
    assert result.bucket == MatchBucket.BLOCKED
    assert "hard constraints cannot be stretched" in result.bucket_explanation.lower()
