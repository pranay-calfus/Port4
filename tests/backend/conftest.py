import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.db import Base, get_db
from backend.main import app


@pytest.fixture
def client(tmp_path):
    """A TestClient wired to a throwaway, per-test SQLite file - completely
    isolated from the real port4.db. Intentionally does NOT use TestClient
    as a context manager, so the app's lifespan (which calls init_db()
    against the real configured database) never runs during tests.
    """
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    from backend import models  # noqa: F401 - registers tables on Base.metadata

    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def db_session(client):  # noqa: ARG001 - depends on client purely to reuse its engine setup
    """A raw Session against the same per-test database as `client`, for
    tests that need to seed data (e.g. an admin account) the API itself
    has no self-service endpoint for.
    """
    from backend.db import get_db

    override = app.dependency_overrides[get_db]
    gen = override()
    session = next(gen)
    try:
        yield session
    finally:
        gen.close()
