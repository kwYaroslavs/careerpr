"""Unit tests for MasterResume, BaseResume, and ResumeVersion services."""

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.db import Base
from app.domain.schemas import BaseResume, MasterResume, ResumeItem
from app.domain.services.resume import ResumeService


@pytest.fixture
def db_session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()
    Base.metadata.drop_all(engine)


def test_master_and_base_resume_crud(db_session: Session) -> None:
    """Test creating and retrieving MasterResume and BaseResume."""
    item1 = ResumeItem(
        id="item_01ARZ3NDEKTSV4RRFFQ69G5FA1",
        text="Built core platform",
        fact_ids=["fact_01HNG58J2V4B80R6C32G5J8W1A"],
    )

    mr = MasterResume(
        id="mres_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        profile_id="prof_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        items=[item1],
        fact_references=["fact_01HNG58J2V4B80R6C32G5J8W1A"],
    )
    db_mr = ResumeService.create_master_resume(db_session, mr)
    assert db_mr.id == mr.id
    assert len(db_mr.items) == 1

    fetched_mr = ResumeService.get_master_resume(db_session, mr.id)
    assert fetched_mr is not None
    assert fetched_mr.profile_id == mr.profile_id

    br = BaseResume(
        id="bres_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        profile_id="prof_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        items=[item1],
        fact_ids=["fact_01HNG58J2V4B80R6C32G5J8W1A"],
    )
    db_br = ResumeService.create_base_resume(db_session, br)
    assert db_br.id == br.id
    assert db_br.version == 1

    fetched_br = ResumeService.get_base_resume(db_session, br.id)
    assert fetched_br is not None
    assert fetched_br.version == 1


def test_base_resume_edits_never_alter_existing_versions(
    db_session: Session,
) -> None:
    """Acceptance criterion: Base edits never alter existing versions/snapshots."""
    item1 = ResumeItem(id="item_01ARZ3NDEKTSV4RRFFQ69G5FA1", text="v1 item")
    br = BaseResume(
        id="bres_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        profile_id="prof_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        items=[item1],
    )
    ResumeService.create_base_resume(db_session, br)

    # Create immutable version snapshot
    rv = ResumeService.create_resume_version(db_session, "rver_01ARZ3NDEKTSV4RRFFQ69G5FAV", br.id)
    assert rv.version == 1
    assert rv.items[0]["text"] == "v1 item"
    original_hash = rv.content_hash

    # Now update base resume
    item2 = ResumeItem(id="item_01ARZ3NDEKTSV4RRFFQ69G5FA1", text="v2 updated item")
    updated_br = ResumeService.update_base_resume(db_session, br.id, {"items": [item2]})
    assert updated_br.version == 2

    # Verify existing ResumeVersion is completely unchanged
    fetched_rv = ResumeService.get_resume_version(db_session, rv.id)
    assert fetched_rv.version == 1
    assert fetched_rv.items[0]["text"] == "v1 item"
    assert fetched_rv.content_hash == original_hash


def test_content_hash_determinism_and_sorting(db_session: Session) -> None:
    """Acceptance criterion: content_hash computed deterministically regardless of item order."""
    item1 = ResumeItem(
        id="item_01ARZ3NDEKTSV4RRFFQ69G5FA1",
        text="First",
        fact_ids=["b", "a"],
        priority=1,
    )
    item2 = ResumeItem(
        id="item_01ARZ3NDEKTSV4RRFFQ69G5FA2",
        text="Second",
        fact_ids=["x"],
        priority=2,
    )

    hash1 = ResumeService.compute_content_hash(
        [item1.model_dump(), item2.model_dump()], profile_id="prof_1", version=1
    )
    hash2 = ResumeService.compute_content_hash(
        [item2.model_dump(), item1.model_dump()], profile_id="prof_1", version=1
    )

    assert hash1 == hash2
    assert isinstance(hash1, str)
    assert len(hash1) == 64


def test_optimistic_concurrency_conflict(db_session: Session) -> None:
    """Test that unexpected version during base resume update raises conflict error."""
    br = BaseResume(
        id="bres_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        profile_id="prof_01ARZ3NDEKTSV4RRFFQ69G5FAV",
        items=[],
    )
    ResumeService.create_base_resume(db_session, br)

    # Update with correct expected version
    ResumeService.update_base_resume(db_session, br.id, {"priority": 10}, expected_version=1)

    # Update with stale expected version should raise ValueError
    with pytest.raises(
        ValueError,
        match="Conflict: expected version 1, but current version is 2",
    ):
        ResumeService.update_base_resume(db_session, br.id, {"priority": 20}, expected_version=1)
