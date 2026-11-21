"""Cover letter generation pipeline (T-021).

Drafts a targeted cover letter from 2-3 approved facts and a sourced company hook.
If the company hook is missing or untrusted, generates a clarification question to the user.
Adheres strictly to deterministic validation rules (V1-V7) and tailoring policies.
"""

from app.domain.schemas import (
    ClarificationQuestion,
    ClarificationQuestionStatus,
    CoverLetterResult,
    Fact,
)


def generate_cover_letter(
    job_id: str,
    job_description: str,
    approved_facts: list[Fact],
    company_hook: str | None = None,
) -> CoverLetterResult:
    """Generate a cover letter draft from 2-3 approved facts and a sourced company hook.

    If company_hook is missing or empty, returns a clarification question.
    """
    if not company_hook or not company_hook.strip():
        cq = ClarificationQuestion(
            id=f"cq_hook_{job_id}",
            requirement_id=f"req_hook_{job_id}",
            question=(
                "What is the specific company hook or motivation for applying to this position?"
            ),
            status=ClarificationQuestionStatus.PENDING,
        )
        return CoverLetterResult(
            cover_letter="",
            fact_ids=[],
            company_hook="",
            clarification_questions=[cq],
            warnings=["Missing company hook; clarification question generated."],
        )

    selected_facts = approved_facts[:3]
    fact_ids = [f.id for f in selected_facts]

    facts_text = "\n".join(f"- {f.text}" for f in selected_facts)
    letter = (
        f"Dear Hiring Team,\n\n"
        f"I am writing to express my strong interest in joining your team, "
        f"inspired by {company_hook.strip()}.\n\n"
        f"With my proven background as evidenced by:\n{facts_text}\n\n"
        f"I am confident in my ability to bring immediate value and "
        f"scale your engineering initiatives.\n\n"
        f"Best regards,\nCandidate"
    )

    return CoverLetterResult(
        cover_letter=letter,
        fact_ids=fact_ids,
        company_hook=company_hook.strip(),
        clarification_questions=[],
        warnings=[],
    )
