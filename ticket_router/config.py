import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Anchored to the repo root (not the process's current working directory) -
# same reasoning as SAMPLE_TICKETS_PATH/SKILLS_DIR elsewhere in this
# codebase. A cwd-relative path would resolve to a different file depending
# on where `streamlit run` (or an IDE's runner) happens to be launched from,
# silently pointing app.py and the admin dashboard at two different, mostly
# empty databases.
_DEFAULT_DB_PATH = str(Path(__file__).resolve().parent.parent / "tickets.db")


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

    # Path to the SQLite database file that stores routed tickets and teams.
    TICKET_DB_PATH: str = os.getenv("TICKET_DB_PATH", _DEFAULT_DB_PATH)

    # Shared password gating the admin dashboard (pages/🛠️_Admin_Dashboard.py).
    # Left empty by default - the dashboard refuses to unlock until this is
    # explicitly set, so it's never accidentally exposed unauthenticated.
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "")


config = Config()
