from typing import Any

from openai import OpenAI

from ticket_router.config import config
from ticket_router.errors import AIResponseError, AIUnavailableError
from ticket_router.logger import logger
from ticket_router.models import ASSIGNED_TEAMS, CATEGORIES, PRIORITIES
from ticket_router.prompts import SYSTEM_PROMPT

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
ROUTE_TICKET_TOOL_NAME = "route_ticket"

# Forcing the model to call this tool is our primary structured-output
# guarantee (Layer 2 of JSON reliability, see docs/AI-Concepts.md). Groq
# exposes an OpenAI-compatible Chat Completions API, so we talk to it with
# the official `openai` SDK, just pointed at a different base URL.
ROUTE_TICKET_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": ROUTE_TICKET_TOOL_NAME,
        "description": "Classify a support ticket and return the routing decision.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "enum": list(CATEGORIES)},
                "priority": {"type": "string", "enum": list(PRIORITIES)},
                "assignedTeam": {"type": "string", "enum": list(ASSIGNED_TEAMS)},
                "reasoning": {
                    "type": "string",
                    "description": "One sentence justifying the decision, citing a specific signal from the ticket.",
                },
                "confidence": {"type": "number", "description": "A number between 0 and 1."},
            },
            "required": ["category", "priority", "assignedTeam", "reasoning", "confidence"],
            "additionalProperties": False,
        },
    },
}


class GroqProvider:
    """The application's only AI provider, talking to Groq's OpenAI-compatible
    Chat Completions API via the official `openai` SDK, just pointed at a
    different base URL.
    """

    def __init__(self) -> None:
        self._client: OpenAI | None = None

    def _get_client(self) -> OpenAI:
        if not config.GROQ_API_KEY:
            raise AIUnavailableError(
                "AI service unavailable: GROQ_API_KEY is not configured. Set it in .env."
            )
        if self._client is None:
            self._client = OpenAI(api_key=config.GROQ_API_KEY, base_url=GROQ_BASE_URL)
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

        try:
            response = client.chat.completions.create(
                model=config.GROQ_MODEL,
                max_tokens=1024,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                tools=[ROUTE_TICKET_TOOL],
                tool_choice={"type": "function", "function": {"name": ROUTE_TICKET_TOOL_NAME}},
            )
        except Exception as error:  # noqa: BLE001 - any SDK/network failure maps to a clean error
            logger.error("Groq API call failed", {"error": str(error)})
            raise AIUnavailableError(
                "AI service is currently unavailable.", {"cause": str(error)}
            ) from error

        tool_calls = response.choices[0].message.tool_calls if response.choices else None
        if not tool_calls:
            raise AIResponseError("The AI response did not include a structured tool call.")

        return tool_calls[0].function.arguments
