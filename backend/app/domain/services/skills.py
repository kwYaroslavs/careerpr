"""Domain services for managing skills, aliases, normalization, and review status."""

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.domain.models import FactAliasModel
from app.domain.schemas import FactAlias


class SkillService:
    """Service for managing skill aliases, terms normalization, and reviewed flags."""

    @staticmethod
    def create_alias(session: Session, alias_in: FactAlias) -> FactAliasModel:
        """Create a new skill alias entry in the database."""
        db_alias = FactAliasModel(
            schema_version=alias_in.schema_version,
            canonical_skill_id=alias_in.canonical_skill_id,
            alias=alias_in.alias,
            locale=alias_in.locale,
            source=alias_in.source,
            reviewed=alias_in.reviewed,
        )
        session.add(db_alias)
        session.commit()
        session.refresh(db_alias)
        return db_alias

    @staticmethod
    def get_canonical_skill_id(
        session: Session,
        term: str,
        locale: str | None = None,
        require_reviewed: bool = True,
    ) -> str | None:
        """Resolve a term to its canonical skill ID using alias mappings.

        If require_reviewed is True (default), only reviewed aliases are used.
        Unreviewed aliases are ignored by validators/normalizers unless explicitly allowed.
        """
        query = session.query(FactAliasModel).filter(FactAliasModel.alias == term)
        if locale:
            query = query.filter(FactAliasModel.locale == locale)
        if require_reviewed:
            query = query.filter(FactAliasModel.reviewed.is_(True))

        match = query.first()
        if match:
            return match.canonical_skill_id

        return None

    @staticmethod
    def list_aliases(
        session: Session,
        canonical_skill_id: str | None = None,
        reviewed: bool | None = None,
    ) -> Sequence[FactAliasModel]:
        """List aliases with optional filtering by canonical skill ID and review status."""
        query = session.query(FactAliasModel)
        if canonical_skill_id:
            query = query.filter(FactAliasModel.canonical_skill_id == canonical_skill_id)
        if reviewed is not None:
            query = query.filter(FactAliasModel.reviewed.is_(reviewed))
        return query.all()

    @staticmethod
    def set_alias_reviewed(
        session: Session, alias_id: int, reviewed: bool
    ) -> FactAliasModel | None:
        """Update the review status of a skill alias."""
        db_alias = session.get(FactAliasModel, alias_id)
        if not db_alias:
            return None
        db_alias.reviewed = reviewed
        session.commit()
        session.refresh(db_alias)
        return db_alias
