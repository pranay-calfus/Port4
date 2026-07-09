import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Loads and exposes environment configuration.

    GROQ_API_KEY is intentionally allowed to be empty here so the app can
    still boot without a key configured. A missing key is only surfaced
    when a request actually needs the AI provider, as a clean error - see
    ticket_router.ai.groq_provider.GroqProvider.
    """

    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    # Optional comma-separated override, e.g. "llama-3.1-8b-instant,qwen/qwen3-32b".
    # When unset, GroqProvider falls back to its own curated default chain.
    GROQ_FALLBACK_MODELS: str = os.getenv("GROQ_FALLBACK_MODELS", "")


config = Config()
