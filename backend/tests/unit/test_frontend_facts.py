"""Tests for Fact Base API endpoints supporting frontend Fact management (T-027)."""

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


def test_fact_management_api_flow(client: TestClient) -> None:
    # 1. Create fact (simulating frontend submission)
    fact_id = "test_fe_fact_1"
    response = client.post(
        "/facts",
        json={
            "id": fact_id,
            "text": "Developed high-throughput microservices in Python",
            "category": "experience",
            "risk_tier": "low",
            "verification_status": "source_backed",
            "evidence_ref": "git-commit-abcdef",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == fact_id
    assert data["text"] == "Developed high-throughput microservices in Python"
    assert data["verification_status"] == "source_backed"

    # 2. List facts (simulating frontend fetch)
    list_response = client.get("/facts")
    assert list_response.status_code == 200
    facts = list_response.json()
    assert any(f["id"] == fact_id for f in facts)

    # 3. Retrieve specific fact
    get_response = client.get(f"/facts/{fact_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == fact_id


def test_fact_management_adversarial_validation(client: TestClient) -> None:
    # Missing required fields
    response = client.post(
        "/facts",
        json={
            "id": "invalid_fact",
            # missing text
        },
    )
    assert response.status_code == 422
