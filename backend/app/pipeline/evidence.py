"""Requirement-to-fact evidence mapping pipeline (T-012).

Maps job requirements to candidate facts, categorizing them into:
- direct: confirmed experience with exact skill/duty (cites Fact IDs)
- transferable: related/transferable experience (cites Fact IDs)
- potential: plausible match, producing clarification questions
- genuine_gap: skill absent, cites no facts

Adheres strictly to ADR-011, ADR-013, ADR-007 (no percentages anywhere).
"""

from pydantic import BaseModel, Field

from app.domain.schemas import (
    ClarificationQuestion,
    Fact,
    JobRequirement,
    MatchCategory,
    TransferableFinding,
)


class EvidenceMappingResult(BaseModel):
    schema_version: int = 1
    job_id: str
    findings: list[TransferableFinding] = Field(default_factory=list)
    clarification_questions: list[ClarificationQuestion] = Field(default_factory=list)


def map_requirements_to_facts(
    job_id: str,
    requirements: list[JobRequirement],
    facts: list[Fact],
    skill_aliases: dict[str, str] | None = None,
) -> EvidenceMappingResult:
    """Map job requirements to candidate facts, determining match categories

    and generating necessary findings/questions. No percentages are used.
    """
    skill_aliases = skill_aliases or {}
    findings: list[TransferableFinding] = []
    clarification_questions: list[ClarificationQuestion] = []

    for req in requirements:
        req_skills = {s.lower() for s in req.normalized_skill_ids}
        expanded_req_skills = set(req_skills)
        for s in req_skills:
            if s in skill_aliases:
                expanded_req_skills.add(skill_aliases[s].lower())

        matching_facts: list[Fact] = []
        for f in facts:
            f_text = f.text.lower()
            f_claim = (f.normalized_claim or "").lower()
            f_tags = {t.lower() for t in f.tags}

            matched = False
            for rs in expanded_req_skills:
                if rs in f_text or rs in f_claim or rs in f_tags:
                    matched = True
                    break

            if f.id in req.evidence_ids:
                matched = True

            if matched:
                matching_facts.append(f)

        if matching_facts and req.evidence_ids:
            category = MatchCategory.DIRECT
            fact_ids = [f.id for f in matching_facts]
            rationale = "Directly supported by fact(s)."
        elif matching_facts:
            category = MatchCategory.TRANSFERABLE
            fact_ids = [f.id for f in matching_facts]
            rationale = "Supported by transferable competence from related experience."
        else:
            if req.kind.value == "nice":
                category = MatchCategory.POTENTIAL
                fact_ids = []
                rationale = "Potential match; requires clarification."
            else:
                category = MatchCategory.GENUINE_GAP
                fact_ids = []
                rationale = "No matching evidence found; genuine gap."

        finding_id = f"tf_{req.id[5:] if req.id.startswith('jreq_') else req.id}"
        finding = TransferableFinding(
            id=finding_id,
            requirement_id=req.id,
            category=category,
            competence=req.text,
            fact_ids=fact_ids,
            rationale=rationale,
        )
        findings.append(finding)

        if category is MatchCategory.POTENTIAL:
            cq_id = f"cq_{req.id[5:] if req.id.startswith('jreq_') else req.id}"
            cq = ClarificationQuestion(
                id=cq_id,
                requirement_id=req.id,
                question=f"Do you have experience related to: {req.text}?",
                status="pending",
            )
            clarification_questions.append(cq)

    return EvidenceMappingResult(
        job_id=job_id,
        findings=findings,
        clarification_questions=clarification_questions,
    )
