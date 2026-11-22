"""Unit tests for Gap Analysis and Clarification Questions (T-034).

Tests potential → clarification question (idempotent, one per requirement),
genuine_gap shown honestly with no fact links, and answers becoming new versioned facts
exclusively via domain service.
"""

from sqlalchemy.orm import Session

from app.career.gaps import (
    analyze_gaps,
    resolve_clarification_question_to_fact,
)
from app.domain.schemas import (
    Fact,
    JobRequirement,
    MatchCategory,
    RequirementKind,
)


def test_analyze_gaps_potential_generates_question_idempotent() -> None:
    """Test that potential matches generate exactly one question per requirement

    and that repeated analysis is idempotent (no duplicate questions).
    """
    req = JobRequirement(
        id="jreq_pot01",
        text="Knowledge of Kubernetes orchestration.",
        kind=RequirementKind.NICE,
    )
    facts: list[Fact] = []

    res1 = analyze_gaps(job_id="job_1", requirements=[req], facts=facts)
    assert len(res1.findings) == 1
    assert res1.findings[0].category == MatchCategory.POTENTIAL
    assert len(res1.clarification_questions) == 1
    cq = res1.clarification_questions[0]
    assert cq.requirement_id == req.id

    res2 = analyze_gaps(
        job_id="job_1",
        requirements=[req],
        facts=facts,
        existing_questions=res1.clarification_questions,
    )
    assert len(res2.clarification_questions) == 1
    assert res2.clarification_questions[0].id == cq.id


def test_analyze_gaps_genuine_gap_no_fact_links() -> None:
    """Test that genuine gaps have no fact links and are shown honestly."""
    req = JobRequirement(
        id="jreq_gap01",
        text="10+ years COBOL mainframe maintenance.",
        kind=RequirementKind.MUST,
    )
    facts = [
        Fact(
            id="fact_python1",
            text="Built Python web apps.",
            tags=["python"],
        )
    ]

    res = analyze_gaps(job_id="job_2", requirements=[req], facts=facts)
    assert len(res.findings) == 1
    finding = res.findings[0]
    assert finding.category == MatchCategory.GENUINE_GAP
    assert finding.fact_ids == []


def test_resolve_clarification_question_to_fact(db_session: Session) -> None:
    """Test that answering a clarification question creates a new versioned fact

    exclusively via domain service.
    """
    fact_id = "fact_01HXXXXXXXXXXXXXXXXXXXXXXXXX"
    answer = "Led Kubernetes migration project for 3 microservices in 2024."

    resolved_fact = resolve_clarification_question_to_fact(
        session=db_session,
        question_id="cq_pot01",
        answer_text=answer,
        fact_id=fact_id,
        tags=["kubernetes", "migration"],
    )

    assert resolved_fact.id == fact_id
    assert resolved_fact.text == answer
    assert "kubernetes" in resolved_fact.tags
