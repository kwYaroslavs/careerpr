"""SQLAlchemy 2 database models reflecting domain entities in docs/DATA_MODEL.md."""

from typing import Any

from sqlalchemy import JSON, Boolean, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, ImmutableModelMixin


class CandidateProfileModel(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    schema_version: Mapped[int] = mapped_column(Integer, default=1)
    name: Mapped[str] = mapped_column(String, nullable=False)
    contacts: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    locale_prefs: Mapped[list[str]] = mapped_column(JSON, default=list)
    hard_constraints: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class CandidateFactModel(Base):
    __tablename__ = "candidate_facts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    schema_version: Mapped[int] = mapped_column(Integer, default=1)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_claim: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String, default="general")
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    risk_tier: Mapped[str] = mapped_column(String, default="low")
    verification_status: Mapped[str] = mapped_column(String, default="unverified")
    source_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_variants: Mapped[list[str]] = mapped_column(JSON, default=list)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[str | None] = mapped_column(String, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    interview_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class FactAliasModel(Base):
    __tablename__ = "fact_aliases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    schema_version: Mapped[int] = mapped_column(Integer, default=1)
    canonical_skill_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    alias: Mapped[str] = mapped_column(String, nullable=False)
    locale: Mapped[str] = mapped_column(String, default="en")
    source: Mapped[str] = mapped_column(String, default="user")
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)


class MasterResumeModel(Base):
    __tablename__ = "master_resumes"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    schema_version: Mapped[int] = mapped_column(Integer, default=1)
    profile_id: Mapped[str] = mapped_column(String, nullable=False)
    items: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    fact_references: Mapped[list[str]] = mapped_column(JSON, default=list)
    protected: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class BaseResumeModel(Base):
    __tablename__ = "base_resumes"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    schema_version: Mapped[int] = mapped_column(Integer, default=1)
    profile_id: Mapped[str] = mapped_column(String, default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    items: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    approved_variants: Mapped[list[str]] = mapped_column(JSON, default=list)
    fact_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    protected: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class ResumeVersionModel(ImmutableModelMixin, Base):
    __tablename__ = "resume_versions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    schema_version: Mapped[int] = mapped_column(Integer, default=1)
    base_resume_id: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    items: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)


class JobPostingModel(Base):
    __tablename__ = "job_postings"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    schema_version: Mapped[int] = mapped_column(Integer, default=1)
    url_normalized: Mapped[str | None] = mapped_column(String, nullable=True)
    raw_job_description: Mapped[str] = mapped_column(Text, nullable=False)
    extraction_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    source: Mapped[str] = mapped_column(String, default="raw")


class JobRequirementModel(Base):
    __tablename__ = "job_requirements"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    schema_version: Mapped[int] = mapped_column(Integer, default=1)
    job_id: Mapped[str | None] = mapped_column(String, nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    normalized_skill_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    evidence_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    user_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)


class MatchReportModel(Base):
    __tablename__ = "match_reports"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    schema_version: Mapped[int] = mapped_column(Integer, default=1)
    job_id: Mapped[str] = mapped_column(String, nullable=False)
    resume_version: Mapped[str] = mapped_column(String, nullable=False)
    requirements: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    hard_constraint_pass: Mapped[bool] = mapped_column(Boolean, default=True)
    bucket: Mapped[str] = mapped_column(String, default="possible")
    inputs_hash: Mapped[str] = mapped_column(String, nullable=False)


class SkillEdgeModel(Base):
    __tablename__ = "skill_edges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    schema_version: Mapped[int] = mapped_column(Integer, default=1)
    source_skill_id: Mapped[str] = mapped_column(String, nullable=False)
    target_skill_id: Mapped[str] = mapped_column(String, nullable=False)
    relation: Mapped[str] = mapped_column(String, default="evidences")
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)


class RoleTaxonomyEntryModel(Base):
    __tablename__ = "role_taxonomy_entries"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    schema_version: Mapped[int] = mapped_column(Integer, default=1)
    title: Mapped[str] = mapped_column(String, nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    skill_ids: Mapped[list[str]] = mapped_column(JSON, default=list)


class TransferableFindingModel(Base):
    __tablename__ = "transferable_findings"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    schema_version: Mapped[int] = mapped_column(Integer, default=1)
    requirement_id: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    competence: Mapped[str] = mapped_column(String, nullable=False)
    fact_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)


class RoleSuggestionModel(Base):
    __tablename__ = "role_suggestions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    schema_version: Mapped[int] = mapped_column(Integer, default=1)
    role_id: Mapped[str] = mapped_column(String, nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    why: Mapped[str] = mapped_column(Text, nullable=False)
    supporting_fact_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    gap_skill_ids: Mapped[list[str]] = mapped_column(JSON, default=list)


class ApplicationModel(Base):
    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    schema_version: Mapped[int] = mapped_column(Integer, default=1)
    job_id: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="draft")
    next_action_date: Mapped[str | None] = mapped_column(String, nullable=True)
    contacts: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class JobOverlayModel(Base):
    __tablename__ = "job_overlays"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    schema_version: Mapped[int] = mapped_column(Integer, default=1)
    application_id: Mapped[str] = mapped_column(String, nullable=False)
    base_resume_version: Mapped[int] = mapped_column(Integer, nullable=False)
    approved_patches: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)


class ChangeProposalModel(Base):
    __tablename__ = "change_proposals"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    schema_version: Mapped[int] = mapped_column(Integer, default=1)
    run_id: Mapped[str] = mapped_column(String, nullable=False)
    target_id: Mapped[str] = mapped_column(String, nullable=False)
    operation: Mapped[str] = mapped_column(String, nullable=False)
    risk_tier: Mapped[str] = mapped_column(String, nullable=False)
    before: Mapped[str] = mapped_column(Text, nullable=False)
    after: Mapped[str] = mapped_column(Text, nullable=False)
    change_reason: Mapped[str] = mapped_column(Text, nullable=False)
    requirement_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    fact_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    dedupe_key: Mapped[str | None] = mapped_column(String, unique=True, index=True, nullable=True)
    expected_version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending")
    validators_passed: Mapped[list[str]] = mapped_column(JSON, default=list)
    blocked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class ClarificationQuestionModel(Base):
    __tablename__ = "clarification_questions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    schema_version: Mapped[int] = mapped_column(Integer, default=1)
    requirement_id: Mapped[str] = mapped_column(String, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending")
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    resulting_fact_id: Mapped[str | None] = mapped_column(String, nullable=True)


class AnswerBankModel(Base):
    __tablename__ = "answer_banks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    schema_version: Mapped[int] = mapped_column(Integer, default=1)
    key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    locale: Mapped[str] = mapped_column(String, default="en")
    value: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(String, default="general")


class ApplicationSnapshotModel(ImmutableModelMixin, Base):
    __tablename__ = "application_snapshots"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    schema_version: Mapped[int] = mapped_column(Integer, default=1)
    application_id: Mapped[str] = mapped_column(String, nullable=False)
    frozen_approved_docs: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    pdf_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    template_version: Mapped[str] = mapped_column(String, default="1.0")
    renderer_version: Mapped[str] = mapped_column(String, default="1.0")


class LLMRunModel(ImmutableModelMixin, Base):
    __tablename__ = "llm_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    schema_version: Mapped[int] = mapped_column(Integer, default=1)
    run_id: Mapped[str] = mapped_column(String, nullable=False)
    step: Mapped[str] = mapped_column(String, nullable=False)
    prompt_id: Mapped[str] = mapped_column(String, nullable=False)
    input_hash: Mapped[str] = mapped_column(String, nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    error_class: Mapped[str | None] = mapped_column(String, nullable=True)


class AuditEventModel(ImmutableModelMixin, Base):
    """Note: Audit events are append-only/immutable."""

    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    schema_version: Mapped[int] = mapped_column(Integer, default=1)
    actor: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)
    entity: Mapped[str] = mapped_column(String, nullable=False)
    before_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    after_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    ts: Mapped[str | None] = mapped_column(String, nullable=True)
