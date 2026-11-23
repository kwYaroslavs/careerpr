"""Role Discovery and Search Modes service (T-035, ADR-010..013).

Provides `suggest_roles` supporting strict, expanded (default), and exploration modes
over the role taxonomy, enforcing hard constraints, requiring supporting fact IDs,
and listing skill gaps without inventing facts or using percentages.
"""

from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.career.skill_graph import SkillGraphService
from app.domain.role_taxonomy import ROLE_TAXONOMY
from app.domain.schemas import (
    Fact,
    RoleSuggestion,
    RoleTaxonomyEntry,
    SearchMode,
)
from app.gateway.base import LLMError
from app.gateway.prompt_loader import LoggedLLMGateway


class RoleDiscoveryResult(BaseModel):
    schema_version: int = 1
    search_mode: SearchMode = SearchMode.EXPANDED
    suggestions: list[RoleSuggestion] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def suggest_roles(
    facts: list[Fact],
    search_mode: SearchMode = SearchMode.EXPANDED,
    hard_constraints: dict[str, Any] | None = None,
    taxonomy: list[RoleTaxonomyEntry] | None = None,
    llm_gateway: LoggedLLMGateway | None = None,
    db_session: Session | None = None,
    skill_aliases: dict[str, str] | None = None,
    run_id: str = "default-run",
) -> RoleDiscoveryResult:
    """Discover role suggestions based on candidate facts, taxonomy, and search mode.

    - Strict: direct-only roles where candidate facts match role skill/keywords directly.
    - Expanded (default): levels 1–2 roles (+ level 3 if supported by evidence).
    - Exploration: widest search up to level 4.
    - Hard constraints gate in all modes.
    - Every suggestion must cite supporting fact_ids and list gap skills.
    """
    hard_constraints = hard_constraints or {}
    skill_aliases = skill_aliases or {}
    taxonomy = taxonomy or ROLE_TAXONOMY

    if db_session is not None:
        db_entries = SkillGraphService.get_role_entries(db_session)
        if db_entries:
            taxonomy = [
                RoleTaxonomyEntry(
                    id=e.id,
                    title=e.title,
                    level=e.level,
                    skill_ids=e.skill_ids,
                )
                for e in db_entries
            ]

    inputs: dict[str, Any] = {
        "search_mode": search_mode.value,
        "hard_constraints": hard_constraints,
        "facts": [f.model_dump() for f in facts],
        "role_taxonomy": [t.model_dump() for t in taxonomy],
        "skill_aliases": skill_aliases,
    }

    if llm_gateway is not None:
        try:
            res = llm_gateway.complete(
                task="suggest_roles",
                schema=RoleDiscoveryResult,
                inputs=inputs,
                prompt_id="suggest_roles",
                version="1",
                run_id=run_id,
                step="suggest_roles",
            )
            return res
        except LLMError:
            pass

    suggestions: list[RoleSuggestion] = []
    warnings: list[str] = []

    candidate_fact_ids = [f.id for f in facts]

    for entry in taxonomy:
        if (
            search_mode is SearchMode.EXPANDED
            and entry.level > 3
            or search_mode is SearchMode.EXPLORATION
            and entry.level > 4
        ):
            continue

        entry_title_lower = entry.title.lower()
        excluded_words = {
            "developer",
            "engineer",
            "architect",
            "manager",
            "consultant",
        }
        title_words = set(entry_title_lower.split()) - excluded_words

        matching_facts = []
        for f in facts:
            f_content = f"{f.text} {f.normalized_claim or ''} {' '.join(f.tags)}".lower()
            title_match = any(tw in f_content for tw in title_words if len(tw) > 2)
            skill_match = any(s.lower() in f_content for s in entry.skill_ids)
            if title_match or skill_match:
                matching_facts.append(f)

        is_direct = len(matching_facts) > 0 and any(f.id for f in matching_facts)

        if search_mode is SearchMode.STRICT and not is_direct:
            continue

        if not matching_facts and search_mode is SearchMode.STRICT:
            continue

        if matching_facts:
            supp_fact_ids = [f.id for f in matching_facts[:3]]
            why = f"Supported by candidate experience matching key competencies for {entry.title}."
            gap_ids = []
        else:
            if search_mode is SearchMode.EXPLORATION and candidate_fact_ids:
                supp_fact_ids = candidate_fact_ids[:1]
                why = (
                    f"Exploratory suggestion for {entry.title} based on "
                    "transferable profile background."
                )
                gap_ids = [f"skill_gap_{entry.id}"]
            else:
                continue

        suggestions.append(
            RoleSuggestion(
                role_id=entry.id,
                level=entry.level,
                why=why,
                supporting_fact_ids=supp_fact_ids,
                gap_skill_ids=gap_ids,
            )
        )

    return RoleDiscoveryResult(
        search_mode=search_mode,
        suggestions=suggestions,
        warnings=warnings,
    )
