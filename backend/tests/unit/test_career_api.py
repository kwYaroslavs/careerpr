"""Unit tests for career API endpoints (roles, transferable, gaps, resolution) - T-041."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.career.skill_graph import SkillGraphService
from app.core.db import Base, get_db
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def db_session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = Session(engine)
    SkillGraphService.seed_database(session)
    app.dependency_overrides[get_db] = lambda: session
    yield session
    app.dependency_overrides.clear()
    session.close()
    Base.metadata.drop_all(engine)


def test_career_roles_endpoint() -> None:
    payload = {
        "facts": [
            {
                "id": "fact_01HJKMNPTVDW00000000000001",
                "text": "Senior Python Backend Developer with FastAPI experience",
                "normalized_claim": "Python developer",
                "tags": ["python", "backend"],
                "category": "experience",
                "risk_tier": "low",
                "verification_status": "source_backed",
            }
        ],
        "search_mode": "expanded",
    }
    response = client.post("/career/roles", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "suggestions" in data
    assert data["search_mode"] == "expanded"


def test_career_transferable_endpoint() -> None:
    payload = {
        "job_id": "job_123",
        "requirement": {
            "id": "jreq_1",
            "kind": "must",
            "text": "Experience building Python services",
            "normalized_skill_ids": ["python"],
            "evidence_ids": ["fact_01HJKMNPTVDW00000000000001"],
        },
        "facts": [
            {
                "id": "fact_01HJKMNPTVDW00000000000001",
                "text": "Built scalable Python microservices",
                "normalized_claim": "Python services",
                "tags": ["python"],
                "category": "experience",
                "risk_tier": "low",
                "verification_status": "source_backed",
            }
        ],
    }
    response = client.post("/career/transferable", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "findings" in data
    assert len(data["findings"]) > 0


def test_career_gaps_and_resolution_endpoints() -> None:
    # 1. Analyze gaps
    payload = {
        "job_id": "job_123",
        "requirements": [
            {
                "id": "jreq_2",
                "kind": "nice",
                "text": "Experience with Kubernetes deployment",
                "normalized_skill_ids": ["kubernetes"],
                "evidence_ids": [],
            }
        ],
        "facts": [
            {
                "id": "fact_01HJKMNPTVDW00000000000001",
                "text": "Python developer",
                "tags": ["python"],
                "category": "experience",
                "risk_tier": "low",
                "verification_status": "source_backed",
            }
        ],
    }
    response = client.post("/career/gaps", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "clarification_questions" in data
    assert len(data["clarification_questions"]) > 0

    # 2. Resolve clarification question
    resolve_payload = {
        "question_id": "cq_jreq_2",
        "answer_text": "Deployed applications using Kubernetes and Docker in production.",
        "fact_id": "fact_01HJKMNPTVDW00000000000002",
        "tags": ["clarification", "verified", "kubernetes"],
    }
    res_response = client.post("/career/gaps/resolve", json=resolve_payload)
    assert res_response.status_code == 201
    res_data = res_response.json()
    assert res_data["id"] == "fact_01HJKMNPTVDW00000000000002"
    assert "Kubernetes" in res_data["text"]
