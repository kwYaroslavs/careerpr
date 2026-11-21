"""Unit tests for the requirement-to-fact evidence mapping pipeline (T-012).

Tests normal, edge, and adversarial cases (no percentages, direct/transferable
citing facts, potential producing clarification questions, genuine gap citing no facts).
"""

import pytest
from pydantic import ValidationError

from app.domain.schemas import (
    Fact,
    JobRequirement,
    MatchCategory,
    RequirementKind,
    RiskTier,
    TransferableFinding,
    Verification,
)
from app.pipeline.evidence import map_requirements_to_facts


def test_evidence_mapping_normal_direct_and_genuine_gap() -> None:
    reqs = [
        JobRequirement(
            id="jreq_python",
            text="Python development experience",
            kind=RequirementKind.MUST,
            normalized_skill_ids=["python"],
            evidence_ids=["fact_python"],
        ),
        JobRequirement(
            id="jreq_cobol",
            text="Legacy COBOL programming",
            kind=RequirementKind.MUST,
            normalized_skill_ids=["cobol"],
        ),
    ]

    facts = [
        Fact(
            id="fact_python",
            text="Developed backend microservices in Python for 3 years",
            normalized_claim="Python backend development",
            category="experience",
            risk_tier=RiskTier.R0,
            verification_status=Verification.SOURCE_BACKED,
        )
    ]

    result = map_requirements_to_facts(job_id="job_1", requirements=reqs, facts=facts)

    assert result.job_id == "job_1"
    assert len(result.findings) == 2

    f_py = next(f for f in result.findings if f.requirement_id == "jreq_python")
    assert f_py.category == MatchCategory.DIRECT
    assert f_py.fact_ids == ["fact_python"]

    f_co = next(f for f in result.findings if f.requirement_id == "jreq_cobol")
    assert f_co.category == MatchCategory.GENUINE_GAP
    assert f_co.fact_ids == []


def test_evidence_mapping_transferable_and_potential() -> None:
    reqs = [
        JobRequirement(
            id="jreq_docker",
            text="Containerization with Docker",
            kind=RequirementKind.MUST,
            normalized_skill_ids=["docker"],
        ),
        JobRequirement(
            id="jreq_kubernetes",
            text="Orchestration with Kubernetes",
            kind=RequirementKind.NICE,
            normalized_skill_ids=["kubernetes"],
        ),
    ]

    facts = [
        Fact(
            id="fact_podman",
            text="Managed container deployments using Podman and container runtime",
            normalized_claim="Container management",
            category="experience",
            risk_tier=RiskTier.R0,
            verification_status=Verification.SOURCE_BACKED,
        )
    ]

    skill_aliases = {"docker": "podman"}

    result = map_requirements_to_facts(
        job_id="job_2", requirements=reqs, facts=facts, skill_aliases=skill_aliases
    )

    f_dock = next(f for f in result.findings if f.requirement_id == "jreq_docker")
    assert f_dock.category in (MatchCategory.DIRECT, MatchCategory.TRANSFERABLE)
    assert "fact_podman" in f_dock.fact_ids

    f_k8s = next(f for f in result.findings if f.requirement_id == "jreq_kubernetes")
    assert f_k8s.category == MatchCategory.POTENTIAL
    assert f_k8s.fact_ids == []

    assert len(result.clarification_questions) == 1
    assert result.clarification_questions[0].requirement_id == "jreq_kubernetes"


def test_adversarial_validation_no_percentages_and_constraints() -> None:
    """Ensure no percentage references and strict fact citation enforcement."""
    reqs = [
        JobRequirement(
            id="jreq_test",
            text="Testing skill",
            kind=RequirementKind.MUST,
            normalized_skill_ids=["testing"],
        )
    ]
    result = map_requirements_to_facts(job_id="job_3", requirements=reqs, facts=[])

    finding = result.findings[0]
    assert finding.category == MatchCategory.GENUINE_GAP
    assert finding.fact_ids == []

    # No percentages anywhere in the serialized output
    assert "%" not in result.model_dump_json()

    # genuine_gap must not cite facts
    with pytest.raises(ValidationError):
        TransferableFinding(
            id="tf_bad",
            requirement_id="jreq_test",
            category=MatchCategory.GENUINE_GAP,
            competence="Testing skill",
            fact_ids=["fact_invalid"],
            rationale="should fail",
        )

    # direct/transferable must cite facts
    with pytest.raises(ValidationError):
        TransferableFinding(
            id="tf_bad2",
            requirement_id="jreq_test",
            category=MatchCategory.DIRECT,
            competence="Testing skill",
            fact_ids=[],
            rationale="should fail",
        )
