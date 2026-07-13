import os

from dotenv import load_dotenv

load_dotenv()


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

    # Optional comma-separated override, e.g. "gpt-4o,gpt-4-turbo". When
    # unset, OpenAIProvider falls back to its own curated default chain of
    # other OpenAI models if OPENAI_MODEL fails.
    OPENAI_FALLBACK_MODELS: str = os.getenv("OPENAI_FALLBACK_MODELS", "")

    # Postgres connection string for persisting routed tickets - see
    # ticket_router.db. Persistence is best-effort, so the app still works
    # if this points at a database that isn't running.
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://ticket_router:ticket_router@localhost:5432/ticket_router"
    )


config = Config()
