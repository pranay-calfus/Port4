"""SQLAlchemy engine/session setup for the backend API.

Everything above this module is written against the ORM, not raw SQL or a
specific database - swapping ticket_router.config.config.DATABASE_URL from
SQLite to Postgres later is a connection-string change, not a rewrite.
"""

from collections.abc import Iterator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from ticket_router.config import config

# check_same_thread=False is required for SQLite + FastAPI's threaded
# request handling; it's a no-op connect_arg for every other backend.
_connect_args = {"check_same_thread": False} if config.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(config.DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def _add_missing_columns() -> None:
    """Best-effort, additive-only schema sync for an existing database
    file: adds any model column that doesn't exist in the actual table yet
    (e.g. a column added during development against a DB file created
    before it existed). create_all() only creates missing *tables*, never
    alters existing ones, so without this a stale local DB starts raising
    "no such column" errors the moment the model gains a field.

    This is not a substitute for real migrations (Alembic, due before the
    eventual Postgres move) - it only ever ADDs nullable columns, never
    renames/drops/alters existing ones - but it keeps local SQLite files
    usable across schema tweaks without needing to delete them.
    """
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if not inspector.has_table(table.name):
                continue
            existing_columns = {col["name"] for col in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing_columns:
                    continue
                col_type = column.type.compile(dialect=engine.dialect)
                conn.execute(
                    text(f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {col_type}')
                )


def init_db() -> None:
    """Creates all tables if they don't already exist, then patches any
    missing columns onto tables that already existed. Safe to call on
    every process start (mirrors ticket_router.db.init_db()'s old
    behavior) - both steps are idempotent no-ops once the schema is current.
    """
    from backend import models  # noqa: F401 - registers tables on Base.metadata

    Base.metadata.create_all(bind=engine)
    _add_missing_columns()


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding one Session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
