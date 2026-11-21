"""Deterministic R0 and R1 proposal generation (T-018).

Generates ChangeProposals for R0 (reorder) and R1 (pick approved variant)
operations strictly adhering to the tailoring policy and validators.
"""

import hashlib

from app.domain.schemas import (
    ChangeProposal,
    Operation,
    ProposalStatus,
    Resume,
    ResumeItem,
    RiskTier,
)


def generate_r0_proposal(
    run_id: str,
    resume: Resume,
    item: ResumeItem,
    new_priority: int,
    requirement_ids: list[str],
    fact_ids: list[str],
    change_reason: str = "Reordering resume item to match target requirement priority",
) -> ChangeProposal:
    """Generate an R0 (reorder) change proposal for a resume item."""
    dedupe_payload = f"{run_id}:{item.id}:reorder:{new_priority}"
    dedupe_key = hashlib.sha256(dedupe_payload.encode("utf-8")).hexdigest()[:16]
    proposal_id = f"prop_{hashlib.sha256(dedupe_payload.encode('utf-8')).hexdigest()[:12]}"

    return ChangeProposal(
        id=proposal_id,
        run_id=run_id,
        target_id=item.id,
        operation=Operation.REORDER,
        risk_tier=RiskTier.R0,
        before=item.text,
        after=item.text,
        change_reason=change_reason,
        requirement_ids=requirement_ids,
        fact_ids=fact_ids or item.fact_ids,
        dedupe_key=dedupe_key,
        expected_version=resume.version,
        status=ProposalStatus.PENDING,
    )


def generate_r1_proposal(
    run_id: str,
    resume: Resume,
    item: ResumeItem,
    chosen_variant: str,
    requirement_ids: list[str],
    fact_ids: list[str],
    change_reason: str = "Picking approved variant matching target requirement",
) -> ChangeProposal:
    """Generate an R1 (pick approved variant) change proposal for a resume item."""
    dedupe_payload = f"{run_id}:{item.id}:pick_variant:{chosen_variant}"
    dedupe_key = hashlib.sha256(dedupe_payload.encode("utf-8")).hexdigest()[:16]
    proposal_id = f"prop_{hashlib.sha256(dedupe_payload.encode('utf-8')).hexdigest()[:12]}"

    return ChangeProposal(
        id=proposal_id,
        run_id=run_id,
        target_id=item.id,
        operation=Operation.PICK_VARIANT,
        risk_tier=RiskTier.R1,
        before=item.text,
        after=chosen_variant,
        change_reason=change_reason,
        requirement_ids=requirement_ids,
        fact_ids=fact_ids or item.fact_ids,
        dedupe_key=dedupe_key,
        expected_version=resume.version,
        status=ProposalStatus.PENDING,
    )
