"""Skill Graph and Role Taxonomy persistence, seed loading,

and reviewed flag filtering (ADR-010, ADR-013).
"""

from sqlalchemy.orm import Session

from app.domain.models import RoleTaxonomyEntryModel, SkillEdgeModel
from app.domain.role_taxonomy import ROLE_TAXONOMY


class SkillGraphService:
    """Service for managing skill edges, role taxonomy entries,

    seed loading, and verified proof filtering.
    """

    @staticmethod
    def seed_database(session: Session) -> None:
        """Idempotently seed RoleTaxonomyEntryModel from ROLE_TAXONOMY."""
        for entry in ROLE_TAXONOMY:
            existing = session.get(RoleTaxonomyEntryModel, entry.id)
            if not existing:
                db_entry = RoleTaxonomyEntryModel(
                    id=entry.id,
                    schema_version=entry.schema_version,
                    title=entry.title,
                    level=entry.level,
                    skill_ids=entry.skill_ids,
                )
                session.add(db_entry)
        session.commit()

    @staticmethod
    def add_skill_edge(
        session: Session,
        source_skill_id: str,
        target_skill_id: str,
        relation: str = "evidences",
        reviewed: bool = False,
    ) -> SkillEdgeModel:
        """Add a skill graph edge."""
        edge = SkillEdgeModel(
            source_skill_id=source_skill_id,
            target_skill_id=target_skill_id,
            relation=relation,
            reviewed=reviewed,
        )
        session.add(edge)
        session.commit()
        session.refresh(edge)
        return edge

    @staticmethod
    def get_skill_edges(
        session: Session,
        skill_id: str | None = None,
        reviewed_only: bool = False,
    ) -> list[SkillEdgeModel]:
        """Query skill edges by skill (source or target)

        and optionally require reviewed=True.
        """
        query = session.query(SkillEdgeModel)
        if skill_id:
            query = query.filter(
                (SkillEdgeModel.source_skill_id == skill_id)
                | (SkillEdgeModel.target_skill_id == skill_id)
            )
        if reviewed_only:
            query = query.filter(SkillEdgeModel.reviewed)
        return query.all()

    @staticmethod
    def get_role_entries(
        session: Session, level: int | None = None
    ) -> list[RoleTaxonomyEntryModel]:
        """Query role taxonomy entries, optionally filtered by level."""
        query = session.query(RoleTaxonomyEntryModel)
        if level is not None:
            query = query.filter(RoleTaxonomyEntryModel.level == level)
        return query.all()

    @staticmethod
    def get_role_entry(session: Session, role_id: str) -> RoleTaxonomyEntryModel | None:
        """Retrieve a single role taxonomy entry by ID."""
        return session.get(RoleTaxonomyEntryModel, role_id)
