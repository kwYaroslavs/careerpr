"""Unit tests for Fact services and API endpoints."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.db import Base, get_db
from app.domain.schemas import Fact, Verification
from app.domain.services.facts import FactService
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


def test_create_and_get_fact(client: TestClient) -> None:
    """Test creating and retrieving a fact via API."""
    response = client.post(
        "/facts",
        json={
            "id": "fact_01HNG58J2V4B80R6C32G5J8W1A",
            "text": "Developed microservices with FastAPI",
            "category": "backend",
            "tags": ["python", "fastapi"],
            "verification_status": "source_backed",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "fact_01HNG58J2V4B80R6C32G5J8W1A"
    assert data["version"] == 1
    assert data["verification_status"] == "source_backed"

    # Get fact
    get_resp = client.get("/facts/fact_01HNG58J2V4B80R6C32G5J8W1A")
    assert get_resp.status_code == 200
    assert get_resp.json()["text"] == "Developed microservices with FastAPI"


def test_fact_versioning_on_update(db_session: Session) -> None:
    """Test that updating a fact increments its version."""
    fact = Fact(
        id="fact_01HNG58J2V4B80R6C32G5J8W1B",
        text="Initial text",
        verification_status=Verification.CONFIRMED,
    )
    created = FactService.create_fact(db_session, fact)
    assert created.version == 1

    updated = FactService.update_fact(
        db_session, "fact_01HNG58J2V4B80R6C32G5J8W1B", {"text": "Updated text"}
    )
    assert updated.version == 2
    assert updated.text == "Updated text"


def test_confidence_never_changes_verification_status(db_session: Session) -> None:
    """Rule check: confidence does not alter verification status automatically."""
    fact = Fact(
        id="fact_01HNG58J2V4B80R6C32G5J8W1C",
        text="Some fact",
        verification_status=Verification.UNVERIFIED,
        confidence=0.99,
    )
    created = FactService.create_fact(db_session, fact)
    assert created.verification_status == Verification.UNVERIFIED.value
    assert created.confidence == 0.99

    # Update confidence to 0.2, verification status must remain unverified
    updated = FactService.update_fact(
        db_session, "fact_01HNG58J2V4B80R6C32G5J8W1C", {"confidence": 0.2}
    )
    assert updated.verification_status == Verification.UNVERIFIED.value
    assert updated.confidence == 0.2


def test_user_stretch_validation_rules(db_session: Session) -> None:
    """Adversarial/Edge case: user_stretch requires low-risk and interview_note."""
    # High risk with user_stretch should fail
    with pytest.raises(
        ValueError,
        match=("user_stretch verification status is only allowed for low-risk tier"),
    ):
        fact = Fact(
            id="fact_01HNG58J2V4B80R6C32G5J8W1D",
            text="Stretch fact",
            risk_tier="high",
            verification_status=Verification.USER_STRETCH,
            interview_note="Discussed in interview",
        )
        FactService.create_fact(db_session, fact)

    # Missing interview_note should fail
    with pytest.raises(
        ValueError,
        match=("user_stretch verification status requires non-empty interview_note"),
    ):
        fact2 = Fact(
            id="fact_01HNG58J2V4B80R6C32G5J8W1E",
            text="Stretch fact",
            risk_tier="low",
            verification_status=Verification.USER_STRETCH,
            interview_note="",
        )
        FactService.create_fact(db_session, fact2)


def test_list_facts_filtering(client: TestClient) -> None:
    """Test filtering facts by category and verification status."""
    client.post(
        "/facts",
        json={
            "id": "fact_01HNG58J2V4B80R6C32G5J8W1F",
            "text": "Fact 1",
            "category": "frontend",
            "verification_status": "confirmed",
        },
    )
    client.post(
        "/facts",
        json={
            "id": "fact_01HNG58J2V4B80R6C32G5J8W1G",
            "text": "Fact 2",
            "category": "backend",
            "verification_status": "unverified",
        },
    )

    resp = client.get("/facts", params={"category": "frontend"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == "fact_01HNG58J2V4B80R6C32G5J8W1F"
