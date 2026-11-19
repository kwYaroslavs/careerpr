"""Single source of truth for contracts. Docs: docs/DATA_MODEL.md, docs/LLM_CONTRACTS.md."""

from enum import StrEnum
from typing import Self

from pydantic import BaseModel, Field, model_validator

SCHEMA_VERSION = 1


class RiskTier(StrEnum):
    R0 = "R0"  # select/reorder
    R1 = "R1"  # pick approved variant
    R2 = "R2"  # rewrite without new data
    # R3 (introduce new data) is forbidden and has no member on purpose


class Operation(StrEnum):
    REORDER = "reorder"
    PICK_VARIANT = "pick_variant"
    REWRITE = "rewrite"


class ProposalStatus(StrEnum):
    PENDING = "pending"
    BLOCKED = "blocked"
    APPROVED = "approved"
    REJECTED = "rejected"
    EDITED = "edited"
    APPLIED = "applied"
    CONFLICT = "conflict"


class Verification(StrEnum):
    SOURCE_BACKED = "source_backed"
    CONFIRMED = "confirmed"
    UNVERIFIED = "unverified"


class Fact(BaseModel):
    id: str
    text: str
    tags: list[str] = Field(default_factory=list)
    risk_tier: str = "low"  # low | high
    verification_status: Verification = Verification.UNVERIFIED
    source_reference: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)  # informational only, never a gate


class ResumeItem(BaseModel):
    id: str
    text: str
    fact_ids: list[str] = Field(default_factory=list)
    priority: int = 0


class Resume(BaseModel):
    schema_version: int = SCHEMA_VERSION
    id: str
    version: int = 1
    items: list[ResumeItem] = Field(default_factory=list)
    protected: dict[str, str] = Field(default_factory=dict)  # name, email, phone, dates, companies


class RequirementKind(StrEnum):
    MUST = "must"
    NICE = "nice"
    HARD = "hard_constraint"


class JobRequirement(BaseModel):
    id: str
    text: str
    kind: RequirementKind
    user_confirmed: bool = False


class ChangeProposal(BaseModel):
    id: str
    run_id: str
    target_id: str
    operation: Operation
    risk_tier: RiskTier
    before: str
    after: str
    change_reason: str
    requirement_ids: list[str] = Field(default_factory=list)
    fact_ids: list[str] = Field(default_factory=list)
    expected_version: int
    status: ProposalStatus = ProposalStatus.PENDING
    validators_passed: list[str] = Field(default_factory=list)
    blocked_reason: str | None = None


# --- Career adaptation layer (ADR-010..013) ---------------------------------


class MatchCategory(StrEnum):
    """Per-requirement evidence category. No percentages anywhere (ADR-007)."""

    DIRECT = "direct"  # confirmed experience with the same skill/duty
    TRANSFERABLE = "transferable"  # experience from another area applies to the requirement
    POTENTIAL = "potential"  # likely relevant experience, needs a clarification question
    GENUINE_GAP = "genuine_gap"  # competence is really absent


class SearchMode(StrEnum):
    STRICT = "strict"  # direct matches only
    EXPANDED = "expanded"  # adjacent roles + transferable skills (default)
    EXPLORATION = "exploration"  # widest search, incl. distant IT directions


DEFAULT_SEARCH_MODE = SearchMode.EXPANDED


class RoleTaxonomyEntry(BaseModel):
    id: str
    title: str
    level: int = Field(ge=1, le=4)
    skill_ids: list[str] = Field(default_factory=list)


class SkillEdge(BaseModel):
    """Reviewed relation in the Skill Graph (relational, no vector DB)."""

    source_skill_id: str
    target_skill_id: str  # competence / skill the source is evidence for
    relation: str = "evidences"  # evidences | part_of | adjacent_to
    reviewed: bool = False  # LLM-suggested edges stay unreviewed and are never proof


class TransferableFinding(BaseModel):
    """A transferable competence found in existing facts. It is NOT confirmed experience."""

    id: str
    requirement_id: str
    category: MatchCategory
    competence: str
    fact_ids: list[str] = Field(default_factory=list)
    rationale: str  # duties / level / complexity / results, not just tech-name overlap

    @model_validator(mode="after")
    def _check_evidence(self) -> Self:
        needs_facts = self.category in (MatchCategory.DIRECT, MatchCategory.TRANSFERABLE)
        if needs_facts and not self.fact_ids:
            raise ValueError("direct/transferable findings must cite fact_ids")
        if self.category is MatchCategory.GENUINE_GAP and self.fact_ids:
            raise ValueError("genuine_gap cannot cite facts")
        return self


class RoleSuggestion(BaseModel):
    """A role direction proposed by Role Discovery, with an honest explanation."""

    role_id: str
    level: int = Field(ge=1, le=4)
    why: str
    supporting_fact_ids: list[str] = Field(min_length=1)
    gap_skill_ids: list[str] = Field(default_factory=list)
