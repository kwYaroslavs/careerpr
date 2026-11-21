"""Unit tests for requirement confirmation, editing, and addition API (T-010, Gate G2)."""

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


def test_requirements_workflow_and_gate_g2(client: TestClient) -> None:
    """Test normal workflow, confirmation, editing, addition, adversarial cases."""
    # 1. Create a job posting first
    job_resp = client.post(
        "/jobs",
        json={
            "id": "jobp_01HNG58J2V4B80R6C32G5J8W1A",
            "raw_job_description": "We need Python and FastAPI experience.",
            "source": "paste",
        },
    )
    assert job_resp.status_code == 201

    # 2. Batch save requirements extracted by LLM (unconfirmed by default)
    batch_resp = client.post(
        "/requirements/batch",
        json={
            "job_id": "jobp_01HNG58J2V4B80R6C32G5J8W1A",
            "requirements": [
                {
                    "id": "jreq_01ARZ3NDEKTSV4RRFFQ69G5FAV",
                    "job_id": "jobp_01HNG58J2V4B80R6C32G5J8W1A",
                    "text": "Python programming",
                    "kind": "must",
                    "user_confirmed": False,
                },
                {
                    "id": "jreq_01ARZ3NDEKTSV4RRFFQ69G5FBW",
                    "job_id": "jobp_01HNG58J2V4B80R6C32G5J8W1A",
                    "text": "FastAPI framework",
                    "kind": "must",
                    "user_confirmed": False,
                },
            ],
        },
    )
    assert batch_resp.status_code == 201
    saved_reqs = batch_resp.json()
    assert len(saved_reqs) == 2
    assert saved_reqs[0]["user_confirmed"] is False

    # 3. Retrieve requirements for the job
    get_resp = client.get("/requirements/job/jobp_01HNG58J2V4B80R6C32G5J8W1A")
    assert get_resp.status_code == 200
    assert len(get_resp.json()) == 2

    # 4. Explicit user action: confirm requirement (Gate G2)
    patch_resp = client.patch(
        "/requirements/jreq_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        json={"user_confirmed": True, "text": "Advanced Python programming"},
    )
    assert patch_resp.status_code == 200
    updated = patch_resp.json()
    assert updated["user_confirmed"] is True
    assert updated["text"] == "Advanced Python programming"

    # 5. User adds a new requirement manually (defaults to user_confirmed=True)
    add_resp = client.post(
        "/requirements",
        json={
            "job_id": "jobp_01HNG58J2V4B80R6C32G5J8W1A",
            "id": "jreq_01ARZ3NDEKTSV4RRFFQ69G5FCX",
            "text": "Docker containerization",
            "kind": "nice",
            "user_confirmed": True,
        },
    )
    assert add_resp.status_code == 201
    added = add_resp.json()
    assert added["user_confirmed"] is True
    assert added["kind"] == "nice"

    # 6. Adversarial / Edge cases
    bad_patch = client.patch(
        "/requirements/jreq_nonexistent",
        json={"user_confirmed": True},
    )
    assert bad_patch.status_code == 404

    bad_batch = client.post(
        "/requirements/batch",
        json={
            "job_id": "jobp_nonexistent",
            "requirements": [],
        },
    )
    assert bad_batch.status_code == 400

    dup_add = client.post(
        "/requirements",
        json={
            "job_id": "jobp_01HNG58J2V4B80R6C32G5J8W1A",
            "id": "jreq_01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "text": "Duplicate ID test",
        },
    )
    assert dup_add.status_code == 400
