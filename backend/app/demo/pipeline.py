"""One-shot demo pipeline: CV text + vacancy text -> everything the system can return.

Uses the real domain pieces (triage, gaps, roles, transferable, validators V1-V10) in memory.
Facts come ONLY from the CV; rewrites that fail validators are discarded (original text kept).
"""

import base64
import re
import uuid
from typing import Any

from pydantic import BaseModel, Field

from app.career.gaps import analyze_gaps
from app.career.roles import suggest_roles
from app.career.transferable import discover_transferable_skills
from app.demo.render import (
    html_to_pdf,
    letter_html,
    resume_html,
    resume_markdown,
)
from app.domain.schemas import (
    BaseResume,
    CandidateProfile,
    ChangeProposal,
    CoverLetterResult,
    Fact,
    JobRequirement,
    MatchCategory,
    Operation,
    RequirementKind,
    ResumeItem,
    RewriteResult,
    RiskTier,
    SearchMode,
)
from app.gateway.base import LLMError
from app.gateway.prompt_loader import LoggedLLMGateway
from app.pipeline.cover_letter import generate_cover_letter
from app.pipeline.triage import triage_job
from app.validators.core import ValidationContext, run_validators


class CvFactDraft(BaseModel):
    text: str
    category: str = "experience"
    tags: list[str] = Field(default_factory=list)


class CvParseResult(BaseModel):
    name: str = ""
    contacts: dict[str, str] = Field(default_factory=dict)
    summary: str = ""
    facts: list[CvFactDraft] = Field(default_factory=list)


class ReqDraft(BaseModel):
    text: str
    kind: str = "must"
    normalized_skill_ids: list[str] = Field(default_factory=list)


class ReqDraftResult(BaseModel):
    requirements: list[ReqDraft] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


_TOK = re.compile(r"[A-Za-zА-Яа-я0-9+#.]{3,}")


def _kind(raw: str) -> RequirementKind:
    raw = raw.lower().strip()
    if raw.startswith("hard"):
        return RequirementKind.HARD
    return RequirementKind.NICE if raw.startswith("nice") else RequirementKind.MUST


def run_demo(
    llm: Any,
    model_name: str,
    cv_text: str,
    job_text: str,
    company_hook: str = "",
    mode: str = "expanded",
    max_pages: int = 2,
    work_authorization: str = "",
    location: str = "",
    effort: str = "min",
) -> dict[str, Any]:
    run_id = f"demo_{uuid.uuid4().hex[:8]}"
    gw = LoggedLLMGateway(llm, None, model_name)
    warnings: list[str] = []
    job_id = "job_demo"

    def call(
        task: str, schema: type[BaseModel], inputs: dict[str, object], pid: str, ver: str
    ) -> Any:
        return gw.complete(
            task, schema, inputs, prompt_id=pid, version=ver, run_id=run_id, step=task
        )

    # 1. CV -> facts
    cv = call("demo_parse_cv", CvParseResult, {"cv_text": cv_text}, "demo_parse_cv", "1")
    facts = [
        Fact(
            id=f"fact_{i}",
            text=d.text.strip(),
            category=d.category if d.category in ("experience", "skill", "education") else "other",
            tags=[t.lower() for t in d.tags],
        )
        for i, d in enumerate(cv.facts, 1)
        if d.text.strip()
    ]
    if not facts:
        raise ValueError("No facts could be extracted from the CV text.")
    name = cv.name.strip() or "Candidate"

    # 2. vacancy -> requirements
    rd = call(
        "extract_requirements",
        ReqDraftResult,
        {"job_description": job_text},
        "extract_requirements",
        "1",
    )
    warnings += rd.warnings
    reqs: list[JobRequirement] = []
    for i, r in enumerate(rd.requirements, 1):
        skills = [s.lower() for s in r.normalized_skill_ids] or [
            w.lower().strip(".") for w in _TOK.findall(r.text)
        ][:4]
        reqs.append(
            JobRequirement(
                id=f"req_{i}",
                job_id=job_id,
                text=r.text,
                kind=_kind(r.kind),
                normalized_skill_ids=skills,
                user_confirmed=True,
            )
        )
    if not reqs:
        raise ValueError("No requirements could be extracted from the vacancy text.")

    # 3. triage (evidence map + hard constraints + fit bucket)
    hc = {
        k: v
        for k, v in (("work_authorization", work_authorization), ("location", location))
        if v.strip()
    }
    profile = CandidateProfile(
        id="profile_demo", name=name, contacts=cv.contacts, hard_constraints=hc
    )
    triage = triage_job(job_id, 1, profile, reqs, facts)
    cat_by_req = {f.requirement_id: f for f in triage.findings}

    # 4. gaps + transferable skills (LLM, best effort)
    gaps = analyze_gaps(job_id, reqs, facts)
    transferable: list[Any] = []
    weak = [
        r
        for r in reqs
        if cat_by_req.get(r.id) is None or cat_by_req[r.id].category is not MatchCategory.DIRECT
    ]
    n_transfer = {"min": 0, "balanced": 0, "full": 3}.get(effort, 0)
    for r in weak[:n_transfer]:
        try:
            t = discover_transferable_skills(job_id, r, facts, llm_gateway=gw, run_id=run_id)
            transferable += t.findings
            warnings += t.warnings
        except (LLMError, ValueError) as e:
            warnings.append(f"transferable skipped for {r.id}: {e}")
            break

    # 5. role directions
    try:
        smode = SearchMode(mode)
    except ValueError:
        smode = SearchMode.EXPANDED
    roles = suggest_roles(facts, smode, {}, run_id=run_id)

    # 6. resume items (relevance order) + R2 rewrites validated by V1-V10
    links: dict[str, list[str]] = {}
    for f in triage.findings:
        if f.category in (MatchCategory.DIRECT, MatchCategory.TRANSFERABLE):
            for fid in f.fact_ids:
                links.setdefault(fid, []).append(f.requirement_id)
    items = [
        ResumeItem(
            id=f"item_{f.id}", text=f.text, fact_ids=[f.id], priority=len(links.get(f.id, []))
        )
        for f in facts
    ]
    base = BaseResume(
        id="resume_demo",
        profile_id=profile.id,
        items=items,
        fact_ids=[f.id for f in facts],
        protected={"name": name, **cv.contacts},
    )
    ctx = ValidationContext(resume=base, facts=facts)
    req_by_id = {r.id: r for r in reqs}
    fact_by_id = {f.id: f for f in facts}
    changes: list[dict[str, Any]] = []
    final_text = {i.id: i.text for i in items}
    n_rewrite = {"min": 0, "balanced": 3, "full": 6}.get(effort, 0)
    top = sorted(links, key=lambda k: -len(links[k]))[:n_rewrite]
    for fid in top:
        item = next(i for i in items if i.fact_ids == [fid])
        rids = links[fid][:3]
        rec: dict[str, Any] = {
            "item_id": item.id,
            "before": item.text,
            "after": item.text,
            "status": "kept",
            "reason": "",
            "requirements": rids,
        }
        try:
            rw = call(
                "rewrite_item",
                RewriteResult,
                {
                    "resume_item": item.text,
                    "linked_facts": f"{fid}: {fact_by_id[fid].text}",
                    "requirements": "\n".join(f"{r}: {req_by_id[r].text}" for r in rids),
                },
                "rewrite_item",
                "1",
            )
            prop = ChangeProposal(
                id=f"prop_{fid}",
                run_id=run_id,
                target_id=item.id,
                operation=Operation.REWRITE,
                risk_tier=RiskTier.R2,
                before=item.text,
                after=rw.rewritten_text,
                change_reason="; ".join(rw.warnings) or "tailor wording to vacancy",
                requirement_ids=[r for r in rw.requirement_ids if r in req_by_id] or rids,
                fact_ids=[f for f in rw.fact_ids if f in fact_by_id] or [fid],
                expected_version=1,
            )
            res = run_validators(prop, ctx)
            rec["validators_passed"] = res.validators_passed
            if res.blocked_reason:
                rec.update(status="blocked", reason=res.blocked_reason)
            elif rw.rewritten_text.strip() != item.text:
                rec.update(
                    status="applied", after=rw.rewritten_text.strip(), reason=prop.change_reason
                )
                final_text[item.id] = rw.rewritten_text.strip()
            else:
                rec["reason"] = "no change needed"
        except LLMError as e:
            rec["reason"] = f"rewrite skipped: {e}"
        changes.append(rec)

    out_items: list[dict[str, Any]] = sorted(
        [
            {
                "id": i.id,
                "text": final_text[i.id],
                "priority": i.priority,
                "category": fact_by_id[i.fact_ids[0]].category,
            }
            for i in items
        ],
        key=lambda x: (-x["priority"], x["id"]),
    )
    # keep the document short: drop zero-priority experience beyond 12 items total
    out_items = [x for n, x in enumerate(out_items) if n < 14 or x["priority"] > 0]

    # 7. cover letter (LLM, deterministic fallback)
    hook = company_hook.strip() or "the role described in your job posting"
    letter_facts = sorted(facts, key=lambda f: -len(links.get(f.id, [])))[:3]
    try:
        letter: CoverLetterResult = call(
            "cover_letter",
            CoverLetterResult,
            {
                "job_description": job_text,
                "approved_facts": "\n".join(f"{f.id}: {f.text}" for f in letter_facts),
                "company_hook": hook,
            },
            "cover_letter",
            "1",
        )
        if not letter.cover_letter.strip():
            raise LLMError("invalid_json", "empty cover letter")
    except LLMError as e:
        warnings.append(f"cover letter fallback template used ({e.error_class})")
        letter = generate_cover_letter(job_id, job_text, letter_facts, hook)
        letter.cover_letter = letter.cover_letter.replace("Candidate", name)

    # 8. render
    md = resume_markdown(name, cv.contacts, cv.summary, out_items)
    cl_text = letter.cover_letter
    resume_pdf, resume_pages = html_to_pdf(
        resume_html(name, cv.contacts, cv.summary, out_items), max_pages
    )
    letter_pdf, _ = html_to_pdf(letter_html(name, cl_text), 1)

    def dump(x: Any) -> Any:
        return x.model_dump(mode="json") if hasattr(x, "model_dump") else x

    return {
        "run_id": run_id,
        "provider": model_name,
        "candidate": {"name": name, "contacts": cv.contacts, "summary": cv.summary},
        "facts": [dump(f) for f in facts],
        "requirements": [dump(r) for r in reqs],
        "triage": {
            "bucket": triage.bucket.value,
            "explanation": triage.bucket_explanation,
            "hard_constraint_pass": triage.hard_constraint_pass,
            "hard_constraint_failure_reasons": triage.hard_constraint_failure_reasons,
            "findings": [dump(f) for f in triage.findings],
        },
        "gaps": dump(gaps),
        "transferable": [dump(t) for t in transferable],
        "roles": dump(roles),
        "changes": changes,
        "resume_markdown": md,
        "cover_letter": dump(letter),
        "resume_pdf_b64": base64.b64encode(resume_pdf).decode(),
        "resume_pages": resume_pages,
        "cover_letter_pdf_b64": base64.b64encode(letter_pdf).decode(),
        "warnings": warnings,
        "trace": getattr(llm, "trace", []),
    }
