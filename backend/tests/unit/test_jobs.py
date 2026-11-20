"""Unit tests for job description intake, URL normalization, and duplicate detection (T-008)."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.db import Base, get_db
from app.domain.services.jobs import JobService
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


@pytest.fixture
def db_session() -> Iterator[Session]:
    engine = make_engine()
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()
    Base.metadata.drop_all(engine)


def test_url_normalization() -> None:
    """Test URL normalization: strips UTM params, www, trailing slashes, fragments."""
    url1 = "https://www.Example.com/jobs/123/?utm_source=linkedin&utm_medium=cpc#apply"
    norm1 = JobService.normalize_url(url1)
    assert norm1 == "https://example.com/jobs/123"

    url2 = "http://example.com/jobs/456/"
    norm2 = JobService.normalize_url(url2)
    assert norm2 == "http://example.com/jobs/456"

    assert JobService.normalize_url(None) is None
    assert JobService.normalize_url("  ") is None


def test_job_intake_and_duplicate_detection(client: TestClient) -> None:
    """Test creating a job posting and verifying duplicate URL detection."""
    # 1. Create first job posting with URL
    response = client.post(
        "/jobs",
        json={
            "id": "jobp_01HNG58J2V4B80R6C32G5J8W1A",
            "url_normalized": ("https://example.com/careers/backend-eng?utm_source=email"),
            "raw_job_description": (
                "We are looking for a Backend Engineer with Python and FastAPI experience."
            ),
            "source": "paste",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "jobp_01HNG58J2V4B80R6C32G5J8W1A"
    assert data["url_normalized"] == "https://example.com/careers/backend-eng"

    # 2. Try creating duplicate job with same normalized URL (different UTM params)
    dup_response = client.post(
        "/jobs",
        json={
            "id": "jobp_01HNG58J2V4B80R6C32G5J8W1B",
            "url_normalized": (
                "https://www.example.com/careers/backend-eng/?utm_campaign=winter#top"
            ),
            "raw_job_description": "Duplicate posting text.",
            "source": "paste",
        },
    )
    assert dup_response.status_code == 400
    assert "Duplicate job posting URL detected" in dup_response.json()["detail"]


def test_get_job_posting(client: TestClient) -> None:
    """Test retrieving an existing job posting."""
    client.post(
        "/jobs",
        json={
            "id": "jobp_01HNG58J2V4B80R6C32G5J8W1C",
            "raw_job_description": "Standalone job description text.",
        },
    )
    resp = client.get("/jobs/jobp_01HNG58J2V4B80R6C32G5J8W1C")
    assert resp.status_code == 200
    assert resp.json()["raw_job_description"] == "Standalone job description text."

    # 404 test
    not_found = client.get("/jobs/jobp_nonexistent")
    assert not_found.status_code == 404
