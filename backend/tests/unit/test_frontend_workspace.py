"""Tests for Frontend Vacancy, Proposal and Stretch workspace flow (T-028)."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.db import Base, get_db
from app.main import app


def make_engine():
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest.fixture
def client() -> Iterator[TestClient]:
    engine = make_engine()
    Base.metadata.create_all(engine)
    session_local = Session(engine)

    def override_get_db() -> Iterator[Session]:
        yield session_local

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    session_local.close()
    Base.metadata.drop_all(engine)


def test_frontend_vacancy_proposal_stretch_workflow(client: TestClient) -> None:
    # 1. Create Fact for evidence map
    fact_resp = client.post(
        "/facts",
        json={
            "id": "fact_python_senior",
            "text": "Senior Python developer with 6+ years experience in FastAPI & PostgreSQL",
            "category": "experience",
            "risk_tier": "low",
            "verification_status": "source_backed",
            "evidence_ref": "git-commit-12345",
        },
    )
    assert fact_resp.status_code == 201

    # 2. Create Job Posting (simulating frontend submission)
    job_resp = client.post(
        "/jobs",
        json={
            "id": "jobp_01HNG58J2V4B80R6C32G5J8W1A",
            "raw_job_description": "Looking for Senior Python Engineer with FastAPI experience.",
        },
    )
    assert job_resp.status_code == 201
    job_data = job_resp.json()
    job_id = job_data["id"]

    # 3. Save batch requirements & evidence mapping
    req_resp = client.post(
        "/requirements/batch",
        json={
            "job_id": job_id,
            "requirements": [
                {
                    "id": "jreq_01ARZ3NDEKTSV4RRFFQ69G5FAV",
                    "job_id": job_id,
                    "text": "FastAPI experience required",
                    "kind": "must",
                    "user_confirmed": True,
                }
            ],
        },
    )
    assert req_resp.status_code == 201
    reqs = req_resp.json()
    assert len(reqs) > 0

    # 4. List proposals
    prop_list_resp = client.get("/proposals")
    assert prop_list_resp.status_code == 200
    proposals = prop_list_resp.json()
    assert isinstance(proposals, list)


def test_frontend_adversarial_snapshot_export(client: TestClient) -> None:
    # Attempt snapshot export with non-existent job/proposal
    response = client.post(
        "/applications/snapshots",
        json={"job_id": "nonexistent_job", "proposal_id": "nonexistent_proposal"},
    )
    assert response.status_code in (400, 404, 422)
