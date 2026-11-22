"""Unit tests for Skill Graph and Role Taxonomy storage (T-032)."""

from sqlalchemy.orm import Session

from app.career.skill_graph import SkillGraphService


def test_seed_idempotency(db_session: Session) -> None:
    """Test that seeding role taxonomy entries is idempotent."""
    SkillGraphService.seed_database(db_session)
    roles_1 = SkillGraphService.get_role_entries(db_session)
    assert len(roles_1) > 0

    SkillGraphService.seed_database(db_session)
    roles_2 = SkillGraphService.get_role_entries(db_session)
    assert len(roles_2) == len(roles_1)


def test_skill_edges_query_and_reviewed_flag(db_session: Session) -> None:
    """Test adding skill edges, querying by skill ID,

    and filtering out unreviewed edges for proof.
    """
    SkillGraphService.add_skill_edge(
        db_session,
        source_skill_id="python",
        target_skill_id="fastapi",
        reviewed=True,
    )
    SkillGraphService.add_skill_edge(
        db_session,
        source_skill_id="python",
        target_skill_id="django",
        reviewed=False,
    )

    all_python_edges = SkillGraphService.get_skill_edges(
        db_session, skill_id="python", reviewed_only=False
    )
    assert len(all_python_edges) == 2

    reviewed_edges = SkillGraphService.get_skill_edges(
        db_session, skill_id="python", reviewed_only=True
    )
    assert len(reviewed_edges) == 1
    assert reviewed_edges[0].target_skill_id == "fastapi"
    assert reviewed_edges[0].reviewed is True


def test_role_taxonomy_filtering(db_session: Session) -> None:
    """Test querying role taxonomy entries by level and ID."""
    SkillGraphService.seed_database(db_session)

    level_1_roles = SkillGraphService.get_role_entries(db_session, level=1)
    assert len(level_1_roles) > 0
    for r in level_1_roles:
        assert r.level == 1

    backend_dev = SkillGraphService.get_role_entry(db_session, "role_backend_developer")
    assert backend_dev is not None
    assert backend_dev.title == "Backend Developer"
    assert backend_dev.level == 1

    non_existent = SkillGraphService.get_role_entry(db_session, "non_existent_role")
    assert non_existent is None


def test_adversarial_or_edge_cases(db_session: Session) -> None:
    """Test adversarial or edge cases:

    empty skill queries, invalid relation strings, etc.
    """
    edges = SkillGraphService.get_skill_edges(db_session, skill_id="non_existent_skill")
    assert len(edges) == 0

    edge = SkillGraphService.add_skill_edge(
        db_session,
        source_skill_id="docker",
        target_skill_id="kubernetes",
        relation="part_of",
        reviewed=False,
    )
    assert edge.relation == "part_of"
    assert edge.reviewed is False

    reviewed = SkillGraphService.get_skill_edges(db_session, skill_id="docker", reviewed_only=True)
    assert len(reviewed) == 0
