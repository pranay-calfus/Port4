import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Loads and exposes environment configuration.

    Both API keys are intentionally allowed to be empty here so the app can
    still boot without either configured. A missing key is only surfaced
    when a request actually needs that provider, as a clean error - see
    ticket_router.ai.openai_provider.OpenAIProvider and
    ticket_router.ai.groq_provider.GroqProvider.
    """

    # OpenAI is the default provider - tried first on every request.
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Groq is the backup provider, used only if OpenAI is unavailable.
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    # Optional comma-separated override, e.g. "llama-3.1-8b-instant,qwen/qwen3-32b".
    # When unset, GroqProvider falls back to its own curated default chain.
    GROQ_FALLBACK_MODELS: str = os.getenv("GROQ_FALLBACK_MODELS", "")


config = Config()
