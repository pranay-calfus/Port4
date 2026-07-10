from openai import OpenAI

from ticket_router.ai.tool_schema import ROUTE_TICKET_TOOL, ROUTE_TICKET_TOOL_NAME
from ticket_router.config import config
from ticket_router.errors import AIUnavailableError
from ticket_router.logger import logger
from ticket_router.prompts import SYSTEM_PROMPT


class OpenAIProvider:
    """The application's default AI provider - OpenAI's own Chat Completions
    API, called via the official `openai` SDK.

    Unlike GroqProvider, this provider does not maintain its own internal
    model fallback chain: it makes one attempt against `OPENAI_MODEL`. Any
    failure at all (missing/invalid key, rate limit, outage, or a response
    without a structured tool call) is raised as AIUnavailableError, which
    CombinedProvider catches to fall back to the entire Groq model chain -
    a different provider, not just a different model.
    """

    def __init__(self) -> None:
        self._client: OpenAI | None = None
        # Which model actually answered the most recent successful call -
        # read by the routing service so the UI can show it.
        self.last_model_used: str | None = None

    def _get_client(self) -> OpenAI:
        if not config.OPENAI_API_KEY:
            raise AIUnavailableError(
                "AI service unavailable: OPENAI_API_KEY is not configured. Set it in .env."
            )
        if self._client is None:
            self._client = OpenAI(api_key=config.OPENAI_API_KEY)
        return self._client

    def route_ticket(self, message: str, retry_context: str | None = None) -> str:
        client = self._get_client()

        user_content = message
        if retry_context:
            user_content = (
                f"{message}\n\n[SYSTEM NOTICE] Your previous response failed validation: "
                f"{retry_context}. Re-emit strictly valid arguments via the "
                f"{ROUTE_TICKET_TOOL_NAME} tool only."
            )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        model = config.OPENAI_MODEL
        try:
            response = client.chat.completions.create(
                model=model,
                max_tokens=1024,
                messages=messages,
                tools=[ROUTE_TICKET_TOOL],
                tool_choice={"type": "function", "function": {"name": ROUTE_TICKET_TOOL_NAME}},
            )
        except (
            Exception
        ) as error:  # noqa: BLE001 - any failure means "let CombinedProvider fall back to Groq"
            logger.warning(
                "OpenAI call failed, falling back to Groq", {"model": model, "error": str(error)}
            )
            raise AIUnavailableError(
                "OpenAI request failed.", {"cause": str(error), "model": model}
            ) from error

        tool_calls = response.choices[0].message.tool_calls if response.choices else None
        if not tool_calls:
            logger.warning("OpenAI returned no tool call, falling back to Groq", {"model": model})
            raise AIUnavailableError(
                "OpenAI response did not include a structured tool call.", {"model": model}
            )

        self.last_model_used = model
        return tool_calls[0].function.arguments
