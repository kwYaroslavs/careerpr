"""Hard-constraint gate and fit bucket calculation pipeline (T-013).

Evaluates hard constraints (visa, location, language, work authorization) against
candidate profile and determines the match bucket (Strong / Possible / Stretch / Blocked)
with a clear explanation.

Adheres strictly to ADR-011, ADR-013, ADR-007 (no percentages anywhere).
Hard constraints can never be stretched.
"""

import hashlib
import json
import re

from pydantic import BaseModel, Field

from app.domain.schemas import (
    CandidateProfile,
    Fact,
    JobRequirement,
    MatchBucket,
    MatchCategory,
    MatchReportRequirement,
    RequirementKind,
    TransferableFinding,
)
from app.pipeline.evidence import map_requirements_to_facts


class TriageResult(BaseModel):
    schema_version: int = 1
    job_id: str
    resume_version: int | str
    hard_constraint_pass: bool
    hard_constraint_failure_reasons: list[str] = Field(default_factory=list)
    bucket: MatchBucket
    bucket_explanation: str
    requirements_report: list[MatchReportRequirement] = Field(default_factory=list)
    findings: list[TransferableFinding] = Field(default_factory=list)
    inputs_hash: str = ""


_AUTH_TERMS = {
    "authorized",
    "authorization",
    "visa",
    "sponsorship",
    "citizen",
    "citizenship",
    "permit",
}
_LOCATION_TERMS = {"located", "location", "based", "onsite", "hybrid"}
_STOP = {"must", "be", "in", "a", "an", "the", "to", "work", "without", "with", "and", "or", "of"}
_NEGATIVE_AUTH = re.compile(
    r"requires?\s+(visa\s+)?sponsorship|needs?\s+sponsorship|\bno\b[^,;]*\bauth|not\s+authorized|unauthorized"
)


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z]+", text.lower()))


def _values_for(profile: CandidateProfile, key_hints: tuple[str, ...]) -> str:
    return " ".join(
        str(v).lower()
        for k, v in profile.hard_constraints.items()
        if any(h in k.lower() for h in key_hints)
    )


def evaluate_hard_constraints(
    profile: CandidateProfile, requirements: list[JobRequirement]
) -> tuple[bool, list[str]]:
    """Fail-closed hard-constraint gate. Hard constraints can never be stretched."""
    reasons: list[str] = []
    auth_vals = _values_for(profile, ("visa", "auth", "citizen"))
    loc_vals = _values_for(profile, ("location", "residen"))

    for req in (r for r in requirements if r.kind == RequirementKind.HARD):
        words = _words(req.text)
        problems: list[str] = []

        if words & _AUTH_TERMS:
            if not auth_vals:
                problems.append("profile has no work-authorization information")
            elif _NEGATIVE_AUTH.search(auth_vals):
                problems.append(f"profile work authorization is '{auth_vals}'")
            elif words & {"us", "united"} and not re.search(
                r"\bus\b|united states|\busa\b", auth_vals
            ):
                problems.append(f"profile work authorization '{auth_vals}' does not cover the US")

        if words & _LOCATION_TERMS and "remote" not in words:
            place = words - _STOP - _LOCATION_TERMS - _AUTH_TERMS
            if not loc_vals:
                problems.append("profile has no location information")
            elif not (place & _words(loc_vals)) and "relocat" not in loc_vals:
                problems.append(f"profile location '{loc_vals}' does not match the requirement")

        if problems:
            reasons.append(f"Hard constraint unmet: '{req.text}' ({'; '.join(problems)}).")

    return not reasons, reasons


def determine_fit_bucket(
    hard_constraint_pass: bool,
    findings: list[TransferableFinding],
    requirements: list[JobRequirement],
) -> tuple[MatchBucket, str]:
    """Determine fit bucket (Strong / Possible / Stretch / Blocked) with explanation."""
    if not hard_constraint_pass:
        return (
            MatchBucket.BLOCKED,
            (
                "Blocked: Candidate does not satisfy mandatory hard constraints "
                "(visa, location, or work authorization). Hard constraints cannot be stretched."
            ),
        )

    must_reqs = [r for r in requirements if r.kind == RequirementKind.MUST]
    finding_map = {f.requirement_id: f for f in findings}

    must_categories = [
        finding_map[r.id].category if r.id in finding_map else MatchCategory.GENUINE_GAP
        for r in must_reqs
    ]

    genuine_gaps_in_must = sum(1 for cat in must_categories if cat == MatchCategory.GENUINE_GAP)
    potential_in_must = sum(1 for cat in must_categories if cat == MatchCategory.POTENTIAL)
    transferable_in_must = sum(1 for cat in must_categories if cat == MatchCategory.TRANSFERABLE)
    direct_in_must = sum(1 for cat in must_categories if cat == MatchCategory.DIRECT)

    total_must = len(must_reqs)

    if total_must == 0:
        return (
            MatchBucket.STRONG,
            "Strong fit: No mandatory requirements specified; profile is a broad match.",
        )

    if genuine_gaps_in_must > 0:
        return (
            MatchBucket.BLOCKED,
            (
                f"Blocked: Candidate has {genuine_gaps_in_must} genuine gap(s) "
                "on mandatory requirements. Critical competencies are absent."
            ),
        )

    if potential_in_must > total_must / 2 or (direct_in_must == 0 and transferable_in_must == 0):
        return (
            MatchBucket.STRETCH,
            (
                "Stretch fit: Several mandatory requirements are potential matches "
                "or require clarification questions and interview preparation."
            ),
        )

    if transferable_in_must > 0 or potential_in_must > 0:
        return (
            MatchBucket.POSSIBLE,
            (
                "Possible fit: Mandatory requirements are met via direct "
                "or transferable experience with some adjacent skills."
            ),
        )

    return (
        MatchBucket.STRONG,
        (
            "Strong fit: All mandatory requirements are directly supported "
            "by candidate evidence in the Fact Base."
        ),
    )


def triage_job(
    job_id: str,
    resume_version: int | str,
    profile: CandidateProfile,
    requirements: list[JobRequirement],
    facts: list[Fact],
    skill_aliases: dict[str, str] | None = None,
) -> TriageResult:
    """Run full triage: evidence mapping, hard constraint evaluation, and fit bucket assignment."""
    evidence_res = map_requirements_to_facts(job_id, requirements, facts, skill_aliases)
    findings = evidence_res.findings

    hc_pass, hc_reasons = evaluate_hard_constraints(profile, requirements)
    bucket, explanation = determine_fit_bucket(hc_pass, findings, requirements)

    report_reqs = [
        MatchReportRequirement(
            requirement_id=f.requirement_id,
            category=f.category,
            fact_ids=f.fact_ids,
        )
        for f in findings
    ]

    inputs_signature = json.dumps(
        {
            "job_id": job_id,
            "profile_id": profile.id,
            "hard_constraints": profile.hard_constraints,
            "requirement_ids": [r.id for r in requirements],
            "fact_ids": [f.id for f in facts],
        },
        sort_keys=True,
        default=str,
    )
    inputs_hash = hashlib.sha256(inputs_signature.encode("utf-8")).hexdigest()

    return TriageResult(
        job_id=job_id,
        resume_version=resume_version,
        hard_constraint_pass=hc_pass,
        hard_constraint_failure_reasons=hc_reasons,
        bucket=bucket,
        bucket_explanation=explanation,
        requirements_report=report_reqs,
        findings=findings,
        inputs_hash=inputs_hash,
    )
