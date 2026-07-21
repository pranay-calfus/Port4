"""Schema management for the backend API's Supabase Postgres database.

The app itself never opens its own database connection - all runtime
queries go through backend/supabase_client.py's Supabase client instead.
This module exists purely so Alembic has a `Base.metadata` to diff against
(see backend/models.py, alembic/env.py) and so the app can auto-apply
pending migrations on startup via run_migrations().
"""

from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase

from ticket_router.config import config

REPO_ROOT = Path(__file__).resolve().parent.parent


class Base(DeclarativeBase):
    pass


# Arbitrary constant, just needs to be the same across every process that
# might call run_migrations() concurrently (e.g. multiple uvicorn/gunicorn
# workers booting at once). Postgres advisory locks are keyed by this
# integer across the whole database, not tied to any table.
_MIGRATION_LOCK_KEY = 727271


def run_migrations() -> None:
    """Applies any pending Alembic migrations against DIRECT_URL. Safe to
    call on every process start (mirrors this module's old init_db()
    behavior) - a no-op once the schema is already at head. Held behind a
    Postgres advisory lock so multiple workers booting at the same time
    don't race applying migrations against each other.
    """
    from alembic.config import Config as AlembicConfig

    from alembic import command

    direct_engine = create_engine(config.DIRECT_URL)
    try:
        with direct_engine.connect() as conn:
            conn.execute(text("SELECT pg_advisory_lock(:key)"), {"key": _MIGRATION_LOCK_KEY})
            try:
                cfg = AlembicConfig(str(REPO_ROOT / "alembic.ini"))
                cfg.set_main_option("script_location", str(REPO_ROOT / "alembic"))
                cfg.set_main_option("sqlalchemy.url", config.DIRECT_URL)
                command.upgrade(cfg, "head")
            finally:
                conn.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": _MIGRATION_LOCK_KEY})
    finally:
        direct_engine.dispose()
