import pytest
from pydantic import ValidationError

from app.domain.role_taxonomy import ROLE_TAXONOMY
from app.domain.schemas import (
    DEFAULT_SEARCH_MODE,
    MatchCategory,
    RoleSuggestion,
    SearchMode,
    TransferableFinding,
)


def _f(cat: MatchCategory, fact_ids: list[str]) -> TransferableFinding:
    return TransferableFinding(
        id="t1", requirement_id="req1", category=cat, competence="Platform Engineering",
        fact_ids=fact_ids, rationale="Ran Docker + CI/CD in production",
    )


def test_default_mode_is_expanded() -> None:
    assert DEFAULT_SEARCH_MODE is SearchMode.EXPANDED


def test_transferable_requires_facts() -> None:
    assert _f(MatchCategory.TRANSFERABLE, ["f1"]).fact_ids == ["f1"]
    with pytest.raises(ValidationError):
        _f(MatchCategory.TRANSFERABLE, [])


def test_direct_requires_facts() -> None:
    with pytest.raises(ValidationError):
        _f(MatchCategory.DIRECT, [])


def test_genuine_gap_cannot_cite_facts() -> None:
    assert _f(MatchCategory.GENUINE_GAP, []).fact_ids == []
    with pytest.raises(ValidationError):
        _f(MatchCategory.GENUINE_GAP, ["f1"])


def test_potential_may_have_no_facts() -> None:
    assert _f(MatchCategory.POTENTIAL, []).category is MatchCategory.POTENTIAL


def test_role_suggestion_needs_support() -> None:
    with pytest.raises(ValidationError):
        RoleSuggestion(role_id="role_sre", level=3, why="x", supporting_fact_ids=[])


def test_taxonomy_levels_and_unique_ids() -> None:
    assert {e.level for e in ROLE_TAXONOMY} == {1, 2, 3, 4}
    assert len({e.id for e in ROLE_TAXONOMY}) == len(ROLE_TAXONOMY)
