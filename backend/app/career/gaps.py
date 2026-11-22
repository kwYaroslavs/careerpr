"""Gap analysis and clarification question generation pipeline (T-034, ADR-010..013).

Turns potential matches into ClarificationQuestions (one per requirement, idempotent),
lists genuine gaps honestly with no fact links, and ensures answered questions
become new versioned facts exclusively through domain services.
"""

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.domain.schemas import (
    ClarificationQuestion,
    ClarificationQuestionStatus,
    Fact,
    JobRequirement,
    MatchCategory,
    TransferableFinding,
    Verification,
)
from app.domain.services.facts import FactService


class GapAnalysisResult(BaseModel):
    schema_version: int = 1
    job_id: str
    findings: list[TransferableFinding] = Field(default_factory=list)
    clarification_questions: list[ClarificationQuestion] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def analyze_gaps(
    job_id: str,
    requirements: list[JobRequirement],
    facts: list[Fact],
    existing_questions: list[ClarificationQuestion] | None = None,
    skill_aliases: dict[str, str] | None = None,
) -> GapAnalysisResult:
    """Analyze gaps between job requirements and candidate facts.

    - Potential matches generate exactly one idempotent ClarificationQuestion per requirement.
    - Genuine gaps have no fact links (fact_ids = []).
    - No auto-filling or fabricating facts.
    """
    skill_aliases = skill_aliases or {}
    existing_questions = existing_questions or []
    existing_cq_req_ids = {cq.requirement_id for cq in existing_questions if cq.requirement_id}

    findings: list[TransferableFinding] = []
    clarification_questions: list[ClarificationQuestion] = list(existing_questions)

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

        is_basic = any(
            any(t in f.text.lower() for t in ["familiar", "basic", "introductory", "read"])
            for f in matching_facts
        )

        if matching_facts and req.evidence_ids and not is_basic:
            category = MatchCategory.DIRECT
            fact_ids = [f.id for f in matching_facts]
            rationale = "Directly supported by candidate experience."
        elif matching_facts and not is_basic:
            category = MatchCategory.TRANSFERABLE
            fact_ids = [f.id for f in matching_facts]
            rationale = "Supported by transferable competence."
        else:
            if req.kind.value == "nice":
                category = MatchCategory.POTENTIAL
                fact_ids = []
                rationale = "Potential match requiring clarification."
            else:
                category = MatchCategory.GENUINE_GAP
                fact_ids = []
                rationale = "No substantive experience found; genuine gap."

        if category is MatchCategory.GENUINE_GAP:
            fact_ids = []

        req_suffix = req.id[5:] if req.id.startswith("jreq_") else req.id
        finding_id = f"tf_{req_suffix}"
        finding = TransferableFinding(
            id=finding_id,
            requirement_id=req.id,
            category=category,
            competence=req.text,
            fact_ids=fact_ids,
            rationale=rationale,
        )
        findings.append(finding)

        if category is MatchCategory.POTENTIAL and req.id not in existing_cq_req_ids:
            cq_id = f"cq_{req_suffix}"
            cq = ClarificationQuestion(
                id=cq_id,
                requirement_id=req.id,
                question=f"Do you have experience related to: {req.text}?",
                status=ClarificationQuestionStatus.PENDING,
            )
            clarification_questions.append(cq)
            existing_cq_req_ids.add(req.id)

    return GapAnalysisResult(
        job_id=job_id,
        findings=findings,
        clarification_questions=clarification_questions,
        warnings=[],
    )


def resolve_clarification_question_to_fact(
    session: Session,
    question_id: str,
    answer_text: str,
    fact_id: str,
    tags: list[str] | None = None,
) -> Fact:
    """Turn an answered clarification question into a new versioned fact

    exclusively via domain service (FactService).
    """
    tags = tags or ["clarification", "verified"]
    new_fact = Fact(
        id=fact_id,
        text=answer_text,
        normalized_claim=answer_text,
        tags=tags,
    )
    db_fact = FactService.create_fact(session=session, fact_in=new_fact)
    v_status = (
        Verification(db_fact.verification_status)
        if isinstance(db_fact.verification_status, str)
        else db_fact.verification_status
    )
    return Fact(
        id=db_fact.id,
        schema_version=db_fact.schema_version,
        text=db_fact.text,
        normalized_claim=db_fact.normalized_claim,
        category=db_fact.category,
        tags=db_fact.tags,
        risk_tier=db_fact.risk_tier,
        verification_status=v_status,
        source_reference=db_fact.source_reference,
        evidence_ref=db_fact.evidence_ref,
        approved_variants=db_fact.approved_variants,
        version=db_fact.version,
        created_at=db_fact.created_at,
        confidence=db_fact.confidence,
        interview_note=db_fact.interview_note,
    )
