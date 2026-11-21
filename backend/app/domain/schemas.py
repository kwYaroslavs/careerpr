"""Single source of truth for contracts. Docs: docs/DATA_MODEL.md, docs/LLM_CONTRACTS.md."""

import re
from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, Field, model_validator

SCHEMA_VERSION = 1

ID_REGEX = re.compile(r"^[a-z0-9]+_[0-9A-HJKMNP-TV-Z]{26}$", re.IGNORECASE)


def is_valid_id(id_str: str) -> bool:
    """Validate stable string ID format (<kind>_<ulid>)."""
    return bool(ID_REGEX.match(id_str))


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
    USER_STRETCH = "user_stretch"


class CandidateProfile(BaseModel):
    schema_version: int = SCHEMA_VERSION
    id: str
    name: str
    contacts: dict[str, str] = Field(default_factory=dict)
    locale_prefs: list[str] = Field(default_factory=list)
    hard_constraints: dict[str, Any] = Field(default_factory=dict)


class Fact(BaseModel):
    schema_version: int = SCHEMA_VERSION
    id: str
    text: str
    normalized_claim: str | None = None
    category: str = "general"
    tags: list[str] = Field(default_factory=list)
    risk_tier: str = "low"  # low | high
    verification_status: Verification = Verification.UNVERIFIED
    source_reference: str | None = None
    evidence_ref: str | None = None
    approved_variants: list[str] = Field(default_factory=list)
    version: int = 1
    created_at: str | None = None
    confidence: float | None = Field(
        default=None, ge=0.0, le=1.0
    )  # informational only, never a gate
    interview_note: str | None = None

    @model_validator(mode="after")
    def _check_user_stretch(self) -> Self:
        if self.verification_status is Verification.USER_STRETCH:
            if self.risk_tier != "low":
                msg = "user_stretch verification status is only allowed for low-risk tier"
                raise ValueError(msg)
            if not self.interview_note or not self.interview_note.strip():
                msg = "user_stretch verification status requires non-empty interview_note"
                raise ValueError(msg)
        return self


CandidateFact = Fact


class FactAlias(BaseModel):
    schema_version: int = SCHEMA_VERSION
    canonical_skill_id: str
    alias: str
    locale: str = "en"
    source: str = "user"
    reviewed: bool = False


class ResumeItem(BaseModel):
    id: str
    text: str
    fact_ids: list[str] = Field(default_factory=list)
    priority: int = 0


class MasterResume(BaseModel):
    schema_version: int = SCHEMA_VERSION
    id: str
    profile_id: str
    items: list[ResumeItem] = Field(default_factory=list)
    fact_references: list[str] = Field(default_factory=list)
    protected: dict[str, str] = Field(default_factory=dict)


class BaseResume(BaseModel):
    schema_version: int = SCHEMA_VERSION
    id: str
    profile_id: str = ""
    version: int = 1
    items: list[ResumeItem] = Field(default_factory=list)
    priority: int = 0
    approved_variants: list[str] = Field(default_factory=list)
    fact_ids: list[str] = Field(default_factory=list)
    protected: dict[str, str] = Field(default_factory=dict)  # name, email, phone, dates, companies


Resume = BaseResume


class ResumeVersion(BaseModel):
    schema_version: int = SCHEMA_VERSION
    id: str
    base_resume_id: str
    version: int
    content_hash: str
    items: list[ResumeItem] = Field(default_factory=list)


class ExtractionMetadata(BaseModel):
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)
    unparsed: list[str] = Field(default_factory=list)


class RewriteResult(BaseModel):
    schema_version: int = SCHEMA_VERSION
    rewritten_text: str
    fact_ids: list[str] = Field(min_length=1)
    requirement_ids: list[str] = Field(min_length=1)
    stretch_candidate: bool = False
    warnings: list[str] = Field(default_factory=list)


class JobPosting(BaseModel):
    schema_version: int = SCHEMA_VERSION
    id: str
    url_normalized: str | None = None
    raw_job_description: str
    extraction_metadata: ExtractionMetadata = Field(default_factory=ExtractionMetadata)
    source: str = "raw"


class RequirementKind(StrEnum):
    MUST = "must"
    NICE = "nice"
    HARD = "hard_constraint"


class JobRequirement(BaseModel):
    schema_version: int = SCHEMA_VERSION
    id: str
    job_id: str | None = None
    text: str
    kind: RequirementKind
    normalized_skill_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    user_confirmed: bool = False


class RequirementsExtractionResult(BaseModel):
    schema_version: int = SCHEMA_VERSION
    requirements: list[JobRequirement] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class MatchBucket(StrEnum):
    STRONG = "strong"
    POSSIBLE = "possible"
    STRETCH = "stretch"
    BLOCKED = "blocked"


class MatchReportRequirement(BaseModel):
    requirement_id: str
    category: "MatchCategory"
    fact_ids: list[str] = Field(default_factory=list)


class MatchReport(BaseModel):
    schema_version: int = SCHEMA_VERSION
    job_id: str
    resume_version: int | str
    requirements: list[MatchReportRequirement] = Field(default_factory=list)
    hard_constraint_pass: bool = True
    bucket: MatchBucket = MatchBucket.POSSIBLE
    inputs_hash: str


class ChangeProposal(BaseModel):
    schema_version: int = SCHEMA_VERSION
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
    dedupe_key: str | None = None
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
    schema_version: int = SCHEMA_VERSION
    id: str
    title: str
    level: int = Field(ge=1, le=4)
    skill_ids: list[str] = Field(default_factory=list)


class SkillEdge(BaseModel):
    """Reviewed relation in the Skill Graph (relational, no vector DB)."""

    schema_version: int = SCHEMA_VERSION
    source_skill_id: str
    target_skill_id: str  # competence / skill the source is evidence for
    relation: str = "evidences"  # evidences | part_of | adjacent_to
    reviewed: bool = False  # LLM-suggested edges stay unreviewed and are never proof


class TransferableFinding(BaseModel):
    """A transferable competence found in existing facts. It is NOT confirmed experience."""

    schema_version: int = SCHEMA_VERSION
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

    schema_version: int = SCHEMA_VERSION
    role_id: str
    level: int = Field(ge=1, le=4)
    why: str
    supporting_fact_ids: list[str] = Field(min_length=1)
    gap_skill_ids: list[str] = Field(default_factory=list)


class ApplicationStatus(StrEnum):
    DRAFT = "draft"
    APPLIED = "applied"
    INTERVIEW = "interview"
    REJECTED = "rejected"
    OFFER = "offer"


class Application(BaseModel):
    schema_version: int = SCHEMA_VERSION
    id: str
    job_id: str
    status: ApplicationStatus = ApplicationStatus.DRAFT
    next_action_date: str | None = None
    contacts: dict[str, str] = Field(default_factory=dict)


class JobOverlay(BaseModel):
    schema_version: int = SCHEMA_VERSION
    application_id: str
    base_resume_version: int
    approved_patches: list[dict[str, Any]] = Field(default_factory=list)


class ClarificationQuestionStatus(StrEnum):
    PENDING = "pending"
    ANSWERED = "answered"
    DISMISSED = "dismissed"


class ClarificationQuestion(BaseModel):
    schema_version: int = SCHEMA_VERSION
    id: str
    requirement_id: str
    question: str
    status: ClarificationQuestionStatus = ClarificationQuestionStatus.PENDING
    answer: str | None = None
    resulting_fact_id: str | None = None


class AnswerBank(BaseModel):
    schema_version: int = SCHEMA_VERSION
    key: str
    locale: str = "en"
    value: str
    kind: str = "general"


class ApplicationSnapshot(BaseModel):
    schema_version: int = SCHEMA_VERSION
    id: str
    application_id: str
    frozen_approved_docs: dict[str, Any] = Field(default_factory=dict)
    content_hash: str
    pdf_hash: str | None = None
    template_version: str = "1.0"
    renderer_version: str = "1.0"


class LLMRun(BaseModel):
    schema_version: int = SCHEMA_VERSION
    id: str
    run_id: str
    step: str
    prompt_id: str
    input_hash: str
    model: str
    tokens: int = 0
    latency_ms: float = 0.0
    error_class: str | None = None


class AuditEvent(BaseModel):
    schema_version: int = SCHEMA_VERSION
    id: str
    actor: str
    action: str
    entity: str
    before_hash: str | None = None
    after_hash: str | None = None
    ts: str | None = None
