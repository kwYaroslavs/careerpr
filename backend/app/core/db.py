"""Database core setup: SQLAlchemy 2 engine, session, Base and immutable tables enforcement."""

from collections.abc import Generator
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATABASE_URL = "sqlite:///./careerpr.db"

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
