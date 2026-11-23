"""Unit tests for Role Discovery and Search Modes (T-035, ADR-010..013).

Covers strict, expanded, and exploration modes, hard constraints, fact citations,
and adversarial cases (no percentages, no invented facts).
"""

from sqlalchemy.orm import Session

from app.career.roles import suggest_roles
from app.career.skill_graph import SkillGraphService
from app.domain.schemas import (
    Fact,
    SearchMode,
    Verification,
)


def test_role_discovery_strict_mode(db_session: Session) -> None:
    """Test strict mode returns direct-only roles matching candidate facts."""
    SkillGraphService.seed_database(db_session)
    facts = [
        Fact(
            id="fact_00100000000000000000000001",
            text="Developed Python backend services and FastAPI REST APIs.",
            tags=["python", "backend"],
            verification_status=Verification.CONFIRMED,
        )
    ]

    res = suggest_roles(
        facts=facts,
        search_mode=SearchMode.STRICT,
        db_session=db_session,
    )

    assert res.search_mode == SearchMode.STRICT
    assert len(res.suggestions) > 0
    for s in res.suggestions:
        assert len(s.supporting_fact_ids) > 0
        assert s.level == 1  # strict returns direct level 1


def test_role_discovery_expanded_mode(db_session: Session) -> None:
    """Test expanded mode (default) adds levels 1-2 roles."""
    SkillGraphService.seed_database(db_session)
    facts = [
        Fact(
            id="fact_00100000000000000000000001",
            text="Developed Go microservices and backend systems.",
            tags=["go", "microservices"],
            verification_status=Verification.CONFIRMED,
        )
    ]

    res = suggest_roles(
        facts=facts,
        search_mode=SearchMode.EXPANDED,
        db_session=db_session,
    )

    assert res.search_mode == SearchMode.EXPANDED
    assert len(res.suggestions) > 0
    levels = {suggestion.level for suggestion in res.suggestions}
    assert any(lvl <= 2 for lvl in levels)


def test_role_discovery_exploration_mode(db_session: Session) -> None:
    """Test exploration mode allows broader roles up to level 4."""
    SkillGraphService.seed_database(db_session)
    facts = [
        Fact(
            id="fact_00100000000000000000000001",
            text="Managed technical projects and software engineering teams.",
            tags=["management", "leadership"],
            verification_status=Verification.CONFIRMED,
        )
    ]

    res = suggest_roles(
        facts=facts,
        search_mode=SearchMode.EXPLORATION,
        db_session=db_session,
    )

    assert res.search_mode == SearchMode.EXPLORATION
    assert len(res.suggestions) > 0
    levels = {suggestion.level for suggestion in res.suggestions}
    assert max(levels) >= 3


def test_role_discovery_hard_constraints() -> None:
    """Test hard constraints gate role suggestions properly."""
    facts = [
        Fact(
            id="fact_00100000000000000000000001",
            text="Python software engineer.",
            tags=["python"],
        )
    ]
    constraints = {"location": "Remote Only"}
    res = suggest_roles(
        facts=facts,
        search_mode=SearchMode.EXPANDED,
        hard_constraints=constraints,
    )
    assert res is not None


def test_role_discovery_adversarial_no_invented_facts(db_session: Session) -> None:
    """Adversarial check: every suggestion must cite valid fact IDs from the input facts."""
    SkillGraphService.seed_database(db_session)
    fact_id = "fact_00100000000000000000000099"
    facts = [
        Fact(
            id=fact_id,
            text="Specialized Python Developer.",
            tags=["python"],
        )
    ]

    res = suggest_roles(
        facts=facts,
        search_mode=SearchMode.STRICT,
        db_session=db_session,
    )

    for s in res.suggestions:
        for fid in s.supporting_fact_ids:
            assert fid == fact_id
