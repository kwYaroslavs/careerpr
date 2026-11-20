"""Unit tests for database models."""

import os
import tempfile

import pytest
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from alembic import command
from app.core.db import Base, enforce_immutable_tables
from app.domain.models import (
    ApplicationSnapshotModel,
    AuditEventModel,
    CandidateFactModel,
    CandidateProfileModel,
    ChangeProposalModel,
    LLMRunModel,
    ResumeVersionModel,
)


@pytest.fixture
def db_session() -> pytest.FixtureRequest:
    """Fixture creating an in-memory database session."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    session = Session(engine)

    from sqlalchemy import event

    event.listen(session, "before_flush", enforce_immutable_tables)

    yield session  # type: ignore[misc]

    session.close()
    Base.metadata.drop_all(engine)


def test_candidate_profile_crud(db_session: Session) -> None:
    """Normal CRUD test for CandidateProfileModel."""
    profile = CandidateProfileModel(
        id="profile_01HNG58J2V4B80R6C32G5J8W1A",
        name="John Doe",
        contacts={"email": "john@example.com"},
        locale_prefs=["en"],
        hard_constraints={"work_authorization": "US"},
    )
    db_session.add(profile)
    db_session.commit()

    fetched = db_session.get(CandidateProfileModel, "profile_01HNG58J2V4B80R6C32G5J8W1A")
    assert fetched is not None
    assert fetched.name == "John Doe"
    assert fetched.contacts["email"] == "john@example.com"

    # Update
    fetched.name = "John Smith"
    db_session.commit()
    updated = db_session.get(CandidateProfileModel, "profile_01HNG58J2V4B80R6C32G5J8W1A")
    assert updated is not None
    assert updated.name == "John Smith"


def test_candidate_fact_crud(db_session: Session) -> None:
    """Test CandidateFactModel creation and query."""
    fact = CandidateFactModel(
        id="fact_01HNG58J2V4B80R6C32G5J8W1B",
        text="Built a real-time data streaming pipeline with Kafka",
        normalized_claim="Experience with Kafka streaming",
        category="backend",
        tags=["kafka", "python"],
        risk_tier="low",
        verification_status="confirmed",
        version=1,
    )
    db_session.add(fact)
    db_session.commit()

    fetched = db_session.get(CandidateFactModel, "fact_01HNG58J2V4B80R6C32G5J8W1B")
    assert fetched is not None
    assert fetched.category == "backend"
    assert "kafka" in fetched.tags


def test_dedupe_key_uniqueness_enforced(db_session: Session) -> None:
    """Adversarial test: Duplicate non-null dedupe_key must raise IntegrityError."""
    p1 = ChangeProposalModel(
        id="prop_01HNG58J2V4B80R6C32G5J8W1C",
        run_id="run_01HNG58J2V4B80R6C32G5J8W1D",
        target_id="item_1",
        operation="rewrite",
        risk_tier="R2",
        before="old text",
        after="new text",
        change_reason="improve flow",
        dedupe_key="unique_key_123",
        expected_version=1,
    )
    db_session.add(p1)
    db_session.commit()

    p2 = ChangeProposalModel(
        id="prop_01HNG58J2V4B80R6C32G5J8W1E",
        run_id="run_01HNG58J2V4B80R6C32G5J8W1D",
        target_id="item_2",
        operation="reorder",
        risk_tier="R0",
        before="old text 2",
        after="new text 2",
        change_reason="reorder items",
        dedupe_key="unique_key_123",  # Duplicate key
        expected_version=1,
    )
    db_session.add(p2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_immutable_resume_version_rejects_update(db_session: Session) -> None:
    """Test that updating an immutable ResumeVersionModel instance raises ValueError."""
    rv = ResumeVersionModel(
        id="rv_01HNG58J2V4B80R6C32G5J8W1F",
        base_resume_id="br_01HNG58J2V4B80R6C32G5J8W1G",
        version=1,
        content_hash="abc123hash",
        items=[{"id": "1", "text": "Python dev"}],
    )
    db_session.add(rv)
    db_session.commit()

    # Attempt to update immutable record
    rv.content_hash = "modified_hash"
    with pytest.raises(ValueError, match="is immutable and rejects updates"):
        db_session.commit()
    db_session.rollback()


def test_immutable_application_snapshot_rejects_update(db_session: Session) -> None:
    """Test that updating an ApplicationSnapshotModel instance raises ValueError."""
    snap = ApplicationSnapshotModel(
        id="snap_01HNG58J2V4B80R6C32G5J8W1H",
        application_id="app_01HNG58J2V4B80R6C32G5J8W1I",
        frozen_approved_docs={"resume": "..."},
        content_hash="hash_snap_1",
    )
    db_session.add(snap)
    db_session.commit()

    snap.content_hash = "new_hash"
    with pytest.raises(ValueError, match="is immutable and rejects updates"):
        db_session.flush()


def test_immutable_llm_run_and_audit_event_reject_update(db_session: Session) -> None:
    """Test that LLMRunModel and AuditEventModel instances reject updates."""
    llm_run = LLMRunModel(
        id="run_01HNG58J2V4B80R6C32G5J8W1J",
        run_id="run_1",
        step="G1",
        prompt_id="prompt@1",
        input_hash="hash_in",
        model="fake",
    )
    audit = AuditEventModel(
        id="audit_01HNG58J2V4B80R6C32G5J8W1K",
        actor="user",
        action="approve",
        entity="proposal",
    )
    db_session.add_all([llm_run, audit])
    db_session.commit()

    llm_run.tokens = 500
    with pytest.raises(ValueError, match="is immutable and rejects updates"):
        db_session.flush()
    db_session.rollback()

    audit.action = "reject"
    with pytest.raises(ValueError, match="is immutable and rejects updates"):
        db_session.flush()


def test_alembic_upgrade_head_on_empty_db() -> None:
    """Test running Alembic migration upgrade head on an empty database file."""
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
        db_path = tmp.name

    try:
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")

        # Run migration upgrade head
        command.upgrade(alembic_cfg, "head")

        # Verify tables created
        engine = create_engine(f"sqlite:///{db_path}")
        from sqlalchemy import inspect

        inspector = inspect(engine)
        tables = inspector.get_table_names()
        assert "candidate_profiles" in tables
        assert "change_proposals" in tables
        assert "resume_versions" in tables
        engine.dispose()
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
