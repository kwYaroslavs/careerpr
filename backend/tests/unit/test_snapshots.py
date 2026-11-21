"""Unit tests for Readiness Gate G4 and immutable application snapshots (T-024)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.domain.models import ApplicationSnapshotModel, CandidateFactModel, ChangeProposalModel
from app.domain.schemas import (
    BaseResume,
    Operation,
    ProposalStatus,
    ResumeItem,
    RiskTier,
)
from app.main import app

client = TestClient(app)


def test_g4_refuses_snapshot_when_proposal_pending(db_session: Session) -> None:
    """Acceptance criterion: Red gate refuses snapshot if any proposal is not approved."""
    # Create a pending proposal
    prop = ChangeProposalModel(
        id="prop_01ARZ3NDEKTSV4RRFFQ69G5FA1",
        schema_version=1,
        run_id="run_01ARZ3NDEKTSV4RRFFQ69G5FA1",
        target_id="item_01ARZ3NDEKTSV4RRFFQ69G5FA1",
        operation=Operation.REWRITE,
        risk_tier=RiskTier.R2,
        before="old text",
        after="new text",
        change_reason="better fit",
        requirement_ids=["req_01ARZ3NDEKTSV4RRFFQ69G5FA1"],
        fact_ids=["fact_01ARZ3NDEKTSV4RRFFQ69G5FA1"],
        expected_version=1,
        status=ProposalStatus.PENDING,
        validators_passed=["v1", "v2", "v3"],
    )
    db_session.add(prop)
    db_session.commit()

    br = BaseResume(
        id="bres_01ARZ3NDEKTSV4RRFFQ69G5FA1",
        profile_id="prof_01ARZ3NDEKTSV4RRFFQ69G5FA1",
        version=1,
        items=[
            ResumeItem(
                id="item_01ARZ3NDEKTSV4RRFFQ69G5FA1",
                text="new text",
                fact_ids=["fact_01ARZ3NDEKTSV4RRFFQ69G5FA1"],
            )
        ],
    )

    response = client.post(
        "/applications/snapshots",
        json={
            "application_id": "app_01ARZ3NDEKTSV4RRFFQ69G5FA1",
            "base_resume": br.model_dump(),
            "run_id": "run_01ARZ3NDEKTSV4RRFFQ69G5FA1",
        },
    )
    assert response.status_code == 400
    assert "has status 'pending'" in response.json()["detail"]


def test_g4_success_and_stretch_claims_collection(db_session: Session) -> None:
    """Acceptance criterion: G4 passes when approved, freezes hashes, and lists stretch claims."""
    # Create approved proposal
    prop = ChangeProposalModel(
        id="prop_01ARZ3NDEKTSV4RRFFQ69G5FA2",
        schema_version=1,
        run_id="run_01ARZ3NDEKTSV4RRFFQ69G5FA2",
        target_id="item_01ARZ3NDEKTSV4RRFFQ69G5FA2",
        operation=Operation.REWRITE,
        risk_tier=RiskTier.R2,
        before="old text",
        after="stretched text",
        change_reason="stretch fit",
        requirement_ids=["req_01ARZ3NDEKTSV4RRFFQ69G5FA2"],
        fact_ids=["fact_01ARZ3NDEKTSV4RRFFQ69G5FA2"],
        expected_version=1,
        status=ProposalStatus.APPROVED,
        validators_passed=["v1", "v2", "v3"],
    )
    db_session.add(prop)

    # Add stretch fact
    fact = CandidateFactModel(
        id="fact_01ARZ3NDEKTSV4RRFFQ69G5FA2",
        schema_version=1,
        text="Experience with Kubernetes",
        category="tech",
        risk_tier="low",
        verification_status="user_stretch",
        interview_note="Used in staging environment / personal cluster",
    )
    db_session.add(fact)
    db_session.commit()

    br = BaseResume(
        id="bres_01ARZ3NDEKTSV4RRFFQ69G5FA2",
        profile_id="prof_01ARZ3NDEKTSV4RRFFQ69G5FA2",
        version=1,
        items=[
            ResumeItem(
                id="item_01ARZ3NDEKTSV4RRFFQ69G5FA2",
                text="stretched text",
                fact_ids=["fact_01ARZ3NDEKTSV4RRFFQ69G5FA2"],
            )
        ],
    )

    response = client.post(
        "/applications/snapshots",
        json={
            "application_id": "app_01ARZ3NDEKTSV4RRFFQ69G5FA2",
            "base_resume": br.model_dump(),
            "run_id": "run_01ARZ3NDEKTSV4RRFFQ69G5FA2",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["application_id"] == "app_01ARZ3NDEKTSV4RRFFQ69G5FA2"
    assert data["content_hash"] is not None
    assert data["pdf_hash"] is not None
    assert len(data["frozen_approved_docs"]["stretch_claims"]) == 1
    assert (
        data["frozen_approved_docs"]["stretch_claims"][0]["id"] == "fact_01ARZ3NDEKTSV4RRFFQ69G5FA2"
    )
    assert (
        data["frozen_approved_docs"]["stretch_claims"][0]["interview_note"]
        == "Used in staging environment / personal cluster"
    )


def test_immutable_application_snapshot_rejection(db_session: Session) -> None:
    """Acceptance criterion: ApplicationSnapshot is immutable and rejects updates."""
    snap = ApplicationSnapshotModel(
        id="snap_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        schema_version=1,
        application_id="app_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        frozen_approved_docs={},
        content_hash="testhash",
    )
    db_session.add(snap)
    db_session.commit()

    snap.content_hash = "newhash"
    with pytest.raises(ValueError, match="immutable and rejects updates"):
        db_session.commit()
