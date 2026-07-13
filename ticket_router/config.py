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

    # Optional comma-separated list of other OpenAI models to fall back to
    # if OPENAI_MODEL fails, e.g. "gpt-4o,gpt-4-turbo". Fallback only
    # happens when this is explicitly set - see
    # ticket_router.ai.openai_provider.build_model_chain.
    OPENAI_FALLBACK_MODELS: str = os.getenv("OPENAI_FALLBACK_MODELS", "")


config = Config()
