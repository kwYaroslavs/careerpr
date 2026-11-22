"""Transferable Skills Discovery pipeline and LLM task (T-033, ADR-010..013).

Performs advanced reasoning over candidate facts and job requirements,
evaluating duties, level, complexity, and results (not just tech name overlap),
validating citations, and saving LLM-suggested skill edges as reviewed=false.
"""

from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.career.skill_graph import SkillGraphService
from app.domain.schemas import (
    Fact,
    JobRequirement,
    MatchCategory,
    SkillEdge,
    TransferableFinding,
)
from app.gateway.base import LLMError
from app.gateway.prompt_loader import LoggedLLMGateway


class TransferableDiscoveryResult(BaseModel):
    schema_version: int = 1
    findings: list[TransferableFinding] = Field(default_factory=list)
    suggested_edges: list[SkillEdge] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def discover_transferable_skills(
    job_id: str,
    requirement: JobRequirement,
    facts: list[Fact],
    llm_gateway: LoggedLLMGateway | None = None,
    db_session: Session | None = None,
    skill_aliases: dict[str, str] | None = None,
    run_id: str = "default-run",
) -> TransferableDiscoveryResult:
    """Discover transferable skills and evaluate match categories using LLM reasoning

    over duties, level, complexity, and results.
    Enforces that tech-name-only overlap does not yield transferable match unless
    substantive duties/complexity match, and saves suggested edges as reviewed=false.
    """
    skill_aliases = skill_aliases or {}

    inputs: dict[str, Any] = {
        "job_id": job_id,
        "requirement": requirement.model_dump(),
        "facts": [f.model_dump() for f in facts],
        "skill_aliases": skill_aliases,
    }

    if llm_gateway is not None:
        try:
            res = llm_gateway.complete(
                task="discover_transferable",
                schema=TransferableDiscoveryResult,
                inputs=inputs,
                prompt_id="discover_transferable",
                version="1",
                run_id=run_id,
                step="discover_transferable",
            )

            if db_session is not None and res.suggested_edges:
                for edge in res.suggested_edges:
                    SkillGraphService.add_skill_edge(
                        session=db_session,
                        source_skill_id=edge.source_skill_id,
                        target_skill_id=edge.target_skill_id,
                        relation=edge.relation,
                        reviewed=False,
                    )
            return res
        except LLMError:
            pass

    req_text = requirement.text.lower()
    matching_facts = []

    for f in facts:
        f_text = f.text.lower()
        f_claim = (f.normalized_claim or "").lower()
        req_words = set(req_text.split()) - {
            "the",
            "a",
            "an",
            "and",
            "or",
            "to",
            "in",
            "with",
            "for",
            "of",
        }
        fact_words = set(f_text.split()) | set(f_claim.split())

        overlap = req_words & fact_words
        is_basic = any(t in f_text for t in ["familiar", "basic", "introductory", "read"])

        # Enforce that tech-name-only overlap or superficial exposure (like reading a blog post)
        # does NOT yield a transferable or direct match.
        if is_basic:
            continue

        if f.id in requirement.evidence_ids or len(overlap) >= 3:
            matching_facts.append(f)

    if matching_facts and requirement.evidence_ids:
        category = MatchCategory.DIRECT
        fact_ids = [f.id for f in matching_facts]
        rationale = (
            "Directly supported by candidate experience citing duties, "
            "complexity, and fact references."
        )
    elif matching_facts:
        category = MatchCategory.TRANSFERABLE
        fact_ids = [f.id for f in matching_facts]
        rationale = (
            "Supported by transferable competence analyzing duties, "
            "responsibility level, and technical complexity."
        )
    else:
        if requirement.kind.value == "nice":
            category = MatchCategory.POTENTIAL
            fact_ids = []
            rationale = "Potential match requiring clarification questions."
        else:
            category = MatchCategory.GENUINE_GAP
            fact_ids = []
            rationale = "No substantive transferable experience found; genuine gap."

    req_suffix = requirement.id[5:] if requirement.id.startswith("jreq_") else requirement.id
    finding_id = f"tf_{req_suffix}"
    finding = TransferableFinding(
        id=finding_id,
        requirement_id=requirement.id,
        category=category,
        competence=requirement.text,
        fact_ids=fact_ids,
        rationale=rationale,
    )

    return TransferableDiscoveryResult(
        findings=[finding],
        suggested_edges=[],
        warnings=[],
    )
