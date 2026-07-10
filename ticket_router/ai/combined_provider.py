from ticket_router.ai.groq_provider import GroqProvider
from ticket_router.ai.openai_provider import OpenAIProvider
from ticket_router.errors import AIUnavailableError
from ticket_router.logger import logger


class CombinedProvider:
    """The application's default AI provider: OpenAI first, Groq's full
    model chain as backup.

    `OPENAI_API_KEY` is the default key - every request tries OpenAI first.
    If OpenAI is unavailable for any reason (no key configured, invalid
    key, rate limit, outage, or a malformed response), this falls back to
    GroqProvider, which itself tries every configured Groq model in turn.
    So there are two independent layers of fallback: provider-level (OpenAI
    -> Groq) and, within Groq, model-level (see groq_provider.py).
    """

    def __init__(self) -> None:
        self._openai = OpenAIProvider()
        self._groq = GroqProvider()
        self.last_model_used: str | None = None

    def route_ticket(self, message: str, retry_context: str | None = None) -> str:
        try:
            raw = self._openai.route_ticket(message, retry_context)
            self.last_model_used = f"openai/{self._openai.last_model_used}"
            return raw
        except AIUnavailableError as error:
            logger.warning(
                "OpenAI unavailable, falling back to the Groq model chain",
                {"error": str(error)},
            )

        raw = self._groq.route_ticket(message, retry_context)
        self.last_model_used = self._groq.last_model_used
        return raw
