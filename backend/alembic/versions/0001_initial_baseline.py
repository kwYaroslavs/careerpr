"""Initial database baseline.

Revision ID: 0001
Revises:
Create Date: 2026-11-20

"""

from collections.abc import Sequence

from alembic import op
from app.core.db import Base
from app.domain import models  # noqa: F401

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind)
