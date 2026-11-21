"""Unit tests for skills normalization, multilingual aliases, and review status enforcement."""

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.db import Base
from app.domain.schemas import FactAlias
from app.domain.services.skills import SkillService


def make_engine():
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest.fixture
def db_session() -> Iterator[Session]:
    engine = make_engine()
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()
    Base.metadata.drop_all(engine)


def test_skills_normalization_and_reviewed_aliases(
    db_session: Session,
) -> None:
    """Test standard normalisation, multilingual aliases (RU/UA/EN), and reviewed flag filtering."""
    # 1. Create reviewed EN alias
    alias_en = FactAlias(
        canonical_skill_id="skill_k8s",
        alias="Kubernetes",
        locale="en",
        reviewed=True,
    )
    SkillService.create_alias(db_session, alias_en)

    # 2. Create reviewed RU alias
    alias_ru = FactAlias(
        canonical_skill_id="skill_k8s",
        alias="Кубернетес",
        locale="ru",
        reviewed=True,
    )
    SkillService.create_alias(db_session, alias_ru)

    # 3. Create unreviewed UA alias
    alias_ua = FactAlias(
        canonical_skill_id="skill_k8s",
        alias="Кубернет",
        locale="ua",
        reviewed=False,
    )
    db_ua_model = SkillService.create_alias(db_session, alias_ua)

    # Test resolving reviewed aliases
    assert (
        SkillService.get_canonical_skill_id(db_session, "Kubernetes", require_reviewed=True)
        == "skill_k8s"
    )
    assert (
        SkillService.get_canonical_skill_id(
            db_session, "Кубернетес", locale="ru", require_reviewed=True
        )
        == "skill_k8s"
    )

    # Test that unreviewed alias is NOT used by default (require_reviewed=True)
    assert (
        SkillService.get_canonical_skill_id(db_session, "Кубернет", require_reviewed=True) is None
    )

    # Test that unreviewed alias CAN be accessed if require_reviewed=False
    assert (
        SkillService.get_canonical_skill_id(db_session, "Кубернет", require_reviewed=False)
        == "skill_k8s"
    )

    # Review the UA alias and test again
    SkillService.set_alias_reviewed(db_session, db_ua_model.id, reviewed=True)
    assert (
        SkillService.get_canonical_skill_id(db_session, "Кубернет", require_reviewed=True)
        == "skill_k8s"
    )


def test_list_aliases_filtering(db_session: Session) -> None:
    """Test listing aliases with filtering by canonical skill ID and review status."""
    SkillService.create_alias(
        db_session,
        FactAlias(
            canonical_skill_id="skill_docker",
            alias="Docker",
            locale="en",
            reviewed=True,
        ),
    )
    SkillService.create_alias(
        db_session,
        FactAlias(
            canonical_skill_id="skill_docker",
            alias="Докер",
            locale="ru",
            reviewed=False,
        ),
    )

    all_docker = SkillService.list_aliases(db_session, canonical_skill_id="skill_docker")
    assert len(all_docker) == 2

    reviewed_docker = SkillService.list_aliases(
        db_session, canonical_skill_id="skill_docker", reviewed=True
    )
    assert len(reviewed_docker) == 1
    assert reviewed_docker[0].alias == "Docker"
