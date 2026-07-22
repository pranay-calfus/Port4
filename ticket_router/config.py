import os

from dotenv import load_dotenv

load_dotenv()


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"{name} is not set. Copy .env.example to .env and fill in your "
            "Supabase connection strings (Project Settings -> Database)."
        )
    return value


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

    # Supabase project URL and secret (service_role) key - the app's only
    # runtime connection to the database, via backend/supabase_client.py.
    # The secret key is used (not the publishable/anon key) because the
    # backend is a trusted server with no Row-Level Security policies in
    # place; it needs unrestricted table access.
    SUPABASE_URL: str = _require_env("SUPABASE_URL")
    SUPABASE_SECRET_KEY: str = _require_env("SUPABASE_SECRET_KEY")

    # Raw Postgres connection to the same Supabase project, used exclusively
    # by Alembic (see backend/db.py: run_migrations()) and the test suite's
    # table-truncation fixture (tests/backend/conftest.py) - the app itself
    # never opens its own database connection, it goes through the Supabase
    # client above. Point this at Supabase's session-pooler connection
    # (or true direct connection, if your network has IPv6) - the
    # transaction-mode pooler can't run all DDL.
    DIRECT_URL: str = _require_env("DIRECT_URL")

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

    # Optional fixed dev accounts, created once at startup by
    # backend/seed.py if both the email and password for a given account
    # are set - see that module's docstring. Left empty by default so
    # nothing is seeded unless explicitly configured.
    SUPER_ADMIN_EMAIL: str = os.getenv("SUPER_ADMIN_EMAIL", "")
    SUPER_ADMIN_PASSWORD: str = os.getenv("SUPER_ADMIN_PASSWORD", "")
    PRODUCT_CX_EMAIL: str = os.getenv("PRODUCT_CX_EMAIL", "")
    PRODUCT_CX_PASSWORD: str = os.getenv("PRODUCT_CX_PASSWORD", "")


config = Config()
