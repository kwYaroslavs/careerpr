"""Database core setup: SQLAlchemy 2 engine, session, Base and immutable tables enforcement."""

import os
from collections.abc import Generator
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()
DATABASE_URL = settings.database_url

if DATABASE_URL.startswith("sqlite:///"):
    db_path_str = DATABASE_URL.replace("sqlite:///", "", 1)
    # Handle relative or absolute paths, e.g., sqlite:///./data/careerpr.db -> ./data
    if not db_path_str.startswith(":memory:"):
        # If it's a file path, extract directory and ensure it exists
        path_obj = Path(db_path_str)
        if path_obj.parent and str(path_obj.parent) != ".":
            path_obj.parent.mkdir(parents=True, exist_ok=True)
        elif "./" in db_path_str or "/" in db_path_str:
            # e.g. sqlite:///./data/careerpr.db or sqlite:///data/careerpr.db
            os.makedirs(os.path.dirname(os.path.abspath(db_path_str.lstrip("/"))), exist_ok=True)

engine: Engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


class Base(DeclarativeBase):
    pass


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ImmutableModelMixin:
    """Mixin for models whose records cannot be updated once inserted."""

    __immutable__ = True


@event.listens_for(Session, "before_flush")
def enforce_immutable_tables(session: Session, flush_context: Any, instances: Any) -> None:
    for instance in session.dirty:
        if getattr(instance, "__immutable__", False):
            tablename = getattr(instance, "__tablename__", type(instance).__name__)
            raise ValueError(f"Table '{tablename}' is immutable and rejects updates.")
