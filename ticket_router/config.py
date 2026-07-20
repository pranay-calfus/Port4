import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Anchored to the repo root (not the process's current working directory) -
# same reasoning as SKILLS_DIR elsewhere in this codebase. A cwd-relative
# path would resolve to a different file depending on where `uvicorn`
# (or backend.create_admin, or an IDE's runner) happens to be launched
# from, silently pointing them at two different, mostly empty databases.
_DEFAULT_DATABASE_URL = "sqlite:///" + str(Path(__file__).resolve().parent.parent / "port4.db")


class Config:
    """Loads and exposes environment configuration.

    The API key is intentionally allowed to be empty here so the app can
    still boot without it configured. A missing key is only surfaced when a
    request actually needs it, as a clean error - see
    ticket_router.ai.openai_provider.OpenAIProvider.
    """

    # OpenAI is the only AI provider.
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Optional comma-separated list of other OpenAI models to fall back to
    # if OPENAI_MODEL fails, e.g. "gpt-4o,gpt-4-turbo". Fallback only
    # happens when this is explicitly set - see
    # ticket_router.ai.openai_provider.build_model_chain.
    OPENAI_FALLBACK_MODELS: str = os.getenv("OPENAI_FALLBACK_MODELS", "")

    # SQLAlchemy connection URL for the backend API's database (users,
    # tickets, ticket_messages, ticket_activity - see backend/models.py).
    # Defaults to a SQLite file so the app runs with zero setup; swapping to
    # Postgres later is a matter of changing this URL, not the code, since
    # everything above this is SQLAlchemy.
    DATABASE_URL: str = os.getenv("DATABASE_URL", _DEFAULT_DATABASE_URL)

    # Secret key signing JWT access tokens issued by backend/auth.py. Must
    # be set explicitly in production - see backend.auth for the startup
    # check that refuses the insecure default outside local dev.
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "insecure-dev-secret-change-me-32bytes+")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))

    # Comma-separated list of origins allowed to call this API (see
    # backend/main.py's CORSMiddleware). Defaults to the React frontend's
    # Vite dev server origin.
    CORS_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
        if origin.strip()
    ]


config = Config()
