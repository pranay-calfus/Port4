import psycopg
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.supabase_client import client as supabase_client
from ticket_router.config import config

# Every table the app writes to. Truncated before each test since there's no
# separate test database - tests run against the same Supabase project used
# for dev (see ticket_router/config.py: DIRECT_URL). Order doesn't matter -
# CASCADE handles the FKs (tickets -> ticket_messages/ticket_activity).
_TABLES = ["users", "tickets", "ticket_messages", "ticket_activity"]

# DIRECT_URL uses SQLAlchemy's "postgresql+psycopg://" dialect+driver syntax
# (for backend/db.py's create_engine()) - plain psycopg.connect() below
# doesn't understand the "+psycopg" driver suffix, so it's stripped here.
_RAW_DIRECT_URL = config.DIRECT_URL.replace("postgresql+psycopg://", "postgresql://")


@pytest.fixture(autouse=True)
def _reset_database():
    """Wipes the shared Supabase project's tables before every test. This
    is more destructive than a rollback: there's no per-test transaction to
    discard (supabase-py talks to Postgres over HTTPS through PostgREST,
    which commits every request immediately - there's no connection/
    transaction a test could hold open and roll back). RESTART IDENTITY
    resets the autoincrement sequences too, so ticket ids/numbers are
    deterministic again within a run.
    """
    with psycopg.connect(_RAW_DIRECT_URL, autocommit=True) as conn:
        conn.execute(f"TRUNCATE {', '.join(_TABLES)} RESTART IDENTITY CASCADE")
    yield


@pytest.fixture
def db_session():
    """The shared Supabase client, for tests that need to seed data (e.g.
    an admin account) or call ticket_service functions directly - the API
    itself has no self-service endpoint for some of these. Named
    `db_session` for continuity with existing test call sites; it's the
    same client the app itself uses, not a SQLAlchemy session.
    """
    return supabase_client


@pytest.fixture
def client():
    # Intentionally NOT used as a context manager, so the app's lifespan -
    # which runs `alembic upgrade head` against the real DIRECT_URL - never
    # fires during tests. The schema is already at head from prior real
    # deploys/dev runs; tests only need the (now-truncated) tables to exist.
    return TestClient(app)
