"""Unit tests for domain schemas and contracts (T-002)."""

import pytest
from pydantic import ValidationError

from app.domain.schemas import (
    SCHEMA_VERSION,
    AnswerBank,
    Application,
    ApplicationSnapshot,
    ApplicationStatus,
    AuditEvent,
    BaseResume,
    CandidateFact,
    CandidateProfile,
    ChangeProposal,
    ClarificationQuestion,
    ClarificationQuestionStatus,
    ExtractionMetadata,
    Fact,
    FactAlias,
    JobOverlay,
    JobPosting,
    JobRequirement,
    LLMRun,
    MasterResume,
    MatchBucket,
    MatchCategory,
    MatchReport,
    MatchReportRequirement,
    Operation,
    ProposalStatus,
    RequirementKind,
    Resume,
    ResumeItem,
    ResumeVersion,
    RiskTier,
    RoleSuggestion,
    RoleTaxonomyEntry,
    SearchMode,
    SkillEdge,
    TransferableFinding,
    Verification,
    is_valid_id,
)


def test_schema_version_default() -> None:
    assert SCHEMA_VERSION == 1
    assert SearchMode.EXPANDED == "expanded"


def test_risk_tier_r3_has_no_enum_member() -> None:
    tier_members = [t.value for t in RiskTier]
    assert "R0" in tier_members
    assert "R1" in tier_members
    assert "R2" in tier_members
    assert "R3" not in tier_members
    with pytest.raises(ValueError):
        RiskTier("R3")


def test_is_valid_id_format() -> None:
    # 26 Crockford Base32 characters
    valid_ulid = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
    valid_id = f"fact_{valid_ulid}"
    assert is_valid_id(valid_id) is True

    # Invalid cases
    assert is_valid_id("invalidid") is False
    assert is_valid_id(f"fact_{valid_ulid[:20]}") is False  # too short
    assert is_valid_id(f"fact_{valid_ulid}extra") is False  # too long
    assert is_valid_id(f"fact_{valid_ulid[:-1]}a") is True  # ULID characters (case-insensitive)
    assert is_valid_id(f"fact_{valid_ulid[:-1]}U") is False  # 'U' is excluded in Crockford Base32
    assert is_valid_id(f"fact_{valid_ulid[:-1]}!") is False  # illegal character


def test_candidate_fact_user_stretch_validation() -> None:
    # Valid user_stretch
    f_valid = Fact(
        id="fact_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        text="Basic exposure to Kubernetes",
        risk_tier="low",
        verification_status=Verification.USER_STRETCH,
        interview_note="Used minikube in personal project",
    )
    assert f_valid.verification_status == Verification.USER_STRETCH
    assert CandidateFact is Fact

    # Invalid: user_stretch with high risk tier
    with pytest.raises(ValidationError, match="low-risk tier"):
        Fact(
            id="fact_01ARZ3NDEKTSV4RRFFQ69G5FAV",
            text="Led team of 10",
            risk_tier="high",
            verification_status=Verification.USER_STRETCH,
            interview_note="Managed project",
        )

    # Invalid: user_stretch without interview_note
    with pytest.raises(ValidationError, match="interview_note"):
        Fact(
            id="fact_01ARZ3NDEKTSV4RRFFQ69G5FAV",
            text="Basic exposure to Docker",
            risk_tier="low",
            verification_status=Verification.USER_STRETCH,
            interview_note="",
        )


def test_round_trip_serialization_all_entities() -> None:
    # 1. CandidateProfile
    cp = CandidateProfile(
        id="prof_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        name="Alice Doe",
        contacts={"email": "alice@example.com"},
        locale_prefs=["en-US"],
        hard_constraints={"visa": "US Citizen"},
    )
    cp_json = cp.model_dump_json()
    cp_restored = CandidateProfile.model_validate_json(cp_json)
    assert cp_restored == cp
    assert cp_restored.schema_version == 1

    # 2. Fact / CandidateFact
    fact = Fact(
        id="fact_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        text="Designed REST APIs with Python",
        category="engineering",
        tags=["python", "rest"],
        risk_tier="low",
        verification_status=Verification.SOURCE_BACKED,
    )
    fact_json = fact.model_dump_json()
    assert Fact.model_validate_json(fact_json) == fact

    # 3. FactAlias
    alias = FactAlias(
        canonical_skill_id="skill_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        alias="Py3",
        locale="en",
        reviewed=True,
    )
    assert FactAlias.model_validate_json(alias.model_dump_json()) == alias

    # 4. MasterResume & BaseResume
    item = ResumeItem(id="item_01ARZ3NDEKTSV4RRFFQ69G5FAV", text="Built backend services")
    mr = MasterResume(
        id="mres_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        profile_id="prof_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        items=[item],
        fact_references=["fact_01ARZ3NDEKTSV4RRFFQ69G5FAV"],
    )
    assert MasterResume.model_validate_json(mr.model_dump_json()) == mr

    br = BaseResume(
        id="bres_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        profile_id="prof_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        version=1,
        items=[item],
        protected={"name": "Alice Doe"},
    )
    assert BaseResume.model_validate_json(br.model_dump_json()) == br
    assert Resume is BaseResume

    # 5. ResumeVersion
    rv = ResumeVersion(
        id="rver_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        base_resume_id=br.id,
        version=1,
        content_hash="abc123hash",
        items=[item],
    )
    assert ResumeVersion.model_validate_json(rv.model_dump_json()) == rv

    # 6. JobPosting
    jp = JobPosting(
        id="jobp_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        raw_job_description="We need a Python developer",
        extraction_metadata=ExtractionMetadata(confidence=0.95),
    )
    assert JobPosting.model_validate_json(jp.model_dump_json()) == jp

    # 7. JobRequirement
    jr = JobRequirement(
        id="jreq_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        job_id=jp.id,
        text="3+ years Python experience",
        kind=RequirementKind.MUST,
    )
    assert JobRequirement.model_validate_json(jr.model_dump_json()) == jr

    # 8. MatchReport
    mreq = MatchReportRequirement(
        requirement_id=jr.id,
        category=MatchCategory.DIRECT,
        fact_ids=["fact_01ARZ3NDEKTSV4RRFFQ69G5FAV"],
    )
    mrpt = MatchReport(
        job_id=jp.id,
        resume_version=1,
        requirements=[mreq],
        hard_constraint_pass=True,
        bucket=MatchBucket.STRONG,
        inputs_hash="hashxyz",
    )
    assert MatchReport.model_validate_json(mrpt.model_dump_json()) == mrpt

    # 9. SkillEdge & RoleTaxonomyEntry
    se = SkillEdge(
        source_skill_id="skill_1",
        target_skill_id="skill_2",
        relation="evidences",
        reviewed=True,
    )
    assert SkillEdge.model_validate_json(se.model_dump_json()) == se

    rte = RoleTaxonomyEntry(id="role_1", title="Backend Engineer", level=2, skill_ids=["skill_1"])
    assert RoleTaxonomyEntry.model_validate_json(rte.model_dump_json()) == rte

    # 10. TransferableFinding & RoleSuggestion
    tf = TransferableFinding(
        id="tf_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        requirement_id=jr.id,
        category=MatchCategory.TRANSFERABLE,
        competence="Backend Architecture",
        fact_ids=["fact_01ARZ3NDEKTSV4RRFFQ69G5FAV"],
        rationale="Built equivalent microservices in Go",
    )
    assert TransferableFinding.model_validate_json(tf.model_dump_json()) == tf

    rs = RoleSuggestion(
        role_id="role_1",
        level=2,
        why="Strong backend foundation",
        supporting_fact_ids=["fact_01ARZ3NDEKTSV4RRFFQ69G5FAV"],
    )
    assert RoleSuggestion.model_validate_json(rs.model_dump_json()) == rs

    # 11. Application & JobOverlay
    app = Application(
        id="appl_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        job_id=jp.id,
        status=ApplicationStatus.APPLIED,
    )
    assert Application.model_validate_json(app.model_dump_json()) == app

    jo = JobOverlay(
        application_id=app.id,
        base_resume_version=1,
        approved_patches=[{"op": "replace", "path": "/items/0/text", "value": "New text"}],
    )
    assert JobOverlay.model_validate_json(jo.model_dump_json()) == jo

    # 12. ChangeProposal
    cp_prop = ChangeProposal(
        id="prop_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        run_id="run_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        target_id=item.id,
        operation=Operation.REWRITE,
        risk_tier=RiskTier.R2,
        before="Built backend services",
        after="Architected resilient backend services",
        change_reason="Impact emphasis",
        expected_version=1,
        status=ProposalStatus.PENDING,
    )
    assert ChangeProposal.model_validate_json(cp_prop.model_dump_json()) == cp_prop

    # 13. ClarificationQuestion & AnswerBank
    cq = ClarificationQuestion(
        id="cq_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        requirement_id=jr.id,
        question="Have you managed Kubernetes clusters?",
        status=ClarificationQuestionStatus.PENDING,
    )
    assert ClarificationQuestion.model_validate_json(cq.model_dump_json()) == cq

    ab = AnswerBank(
        key="k8s_exp",
        locale="en",
        value="Managed GKE for 2 years",
        kind="experience",
    )
    assert AnswerBank.model_validate_json(ab.model_dump_json()) == ab

    # 14. ApplicationSnapshot
    snap = ApplicationSnapshot(
        id="snap_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        application_id=app.id,
        frozen_approved_docs={"resume": "pdf_content"},
        content_hash="contenthash123",
        pdf_hash="pdfhash123",
    )
    assert ApplicationSnapshot.model_validate_json(snap.model_dump_json()) == snap

    # 15. LLMRun & AuditEvent
    run = LLMRun(
        id="llmr_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        run_id="run_1",
        step="extract",
        prompt_id="prompt@v1",
        input_hash="hash",
        model="gemini-flash",
    )
    assert LLMRun.model_validate_json(run.model_dump_json()) == run

    audit = AuditEvent(
        id="audt_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        actor="user_1",
        action="approve_proposal",
        entity=cp_prop.id,
    )
    assert AuditEvent.model_validate_json(audit.model_dump_json()) == audit
