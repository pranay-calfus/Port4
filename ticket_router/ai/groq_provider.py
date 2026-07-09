from typing import Any

import openai
from openai import OpenAI

from ticket_router.config import config
from ticket_router.errors import AIUnavailableError
from ticket_router.logger import logger
from ticket_router.models import ASSIGNED_TEAMS, CATEGORIES, PRIORITIES
from ticket_router.prompts import SYSTEM_PROMPT

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
ROUTE_TICKET_TOOL_NAME = "route_ticket"

# Every model currently available on Groq, listed explicitly so each one is
# tried in turn until one succeeds. Order matters: general-purpose
# instruct/chat models known to support function calling come first: the
# more likely a model is to actually classify the ticket correctly, the
# earlier it's tried. The moderation-only models (meta-llama/llama-prompt-
# guard-2-*, openai/gpt-oss-safeguard-20b) and the agentic pipelines
# (groq/compound, groq/compound-mini) are included last for completeness -
# they aren't plain chat models, so they're expected to fail fast and fall
# through, but they're still in the chain rather than silently skipped.
# Override with GROQ_FALLBACK_MODELS in .env (comma-separated) if you want a
# different chain.
DEFAULT_FALLBACK_MODELS: tuple[str, ...] = (
    "llama-3.1-8b-instant",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3-32b",
    "qwen/qwen3.6-27b",
    "allam-2-7b",
    "openai/gpt-oss-safeguard-20b",
    "groq/compound",
    "groq/compound-mini",
    "meta-llama/llama-prompt-guard-2-22m",
    "meta-llama/llama-prompt-guard-2-86m",
)

# Auth failures are a property of the API key, not the model - retrying
# with a different model would just fail the same way, so we fail fast
# instead of burning the whole fallback chain on a bad key.
_NON_RETRYABLE_EXCEPTIONS = (openai.AuthenticationError, openai.PermissionDeniedError)

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


def _build_model_chain() -> list[str]:
    """The configured primary model first, then fallbacks (deduplicated,
    order preserved). GROQ_FALLBACK_MODELS in .env overrides the built-in
    default chain if set.
    """
    if config.GROQ_FALLBACK_MODELS.strip():
        fallbacks = [m.strip() for m in config.GROQ_FALLBACK_MODELS.split(",") if m.strip()]
    else:
        fallbacks = list(DEFAULT_FALLBACK_MODELS)

    chain = [config.GROQ_MODEL, *fallbacks]
    seen: set[str] = set()
    deduped = []
    for model in chain:
        if model not in seen:
            seen.add(model)
            deduped.append(model)
    return deduped


class GroqProvider:
    """The application's only AI provider, talking to Groq's OpenAI-compatible
    Chat Completions API via the official `openai` SDK, just pointed at a
    different base URL.

    If the configured model fails (rate limit, timeout, decommissioned
    model, transient 5xx, etc.), it automatically falls back to the next
    model in the chain rather than failing the whole request - Groq's low
    per-model rate limits make this a realistic scenario, not just a
    theoretical one.
    """

    def __init__(self) -> None:
        self._client: OpenAI | None = None
        # Which model actually answered the most recent successful call -
        # read by the routing service so the UI can show it.
        self.last_model_used: str | None = None

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

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        attempted: list[str] = []
        last_error: str | None = None

        for model in _build_model_chain():
            attempted.append(model)
            try:
                response = client.chat.completions.create(
                    model=model,
                    max_tokens=1024,
                    messages=messages,
                    tools=[ROUTE_TICKET_TOOL],
                    tool_choice={"type": "function", "function": {"name": ROUTE_TICKET_TOOL_NAME}},
                )
            except _NON_RETRYABLE_EXCEPTIONS as error:
                logger.error(
                    "Groq API call failed (non-retryable)", {"model": model, "error": str(error)}
                )
                raise AIUnavailableError(
                    "AI service is currently unavailable.", {"cause": str(error), "model": model}
                ) from error
            except Exception as error:  # noqa: BLE001 - fall back to the next model in the chain
                last_error = str(error)
                logger.warning(
                    "Groq model failed, falling back to next model",
                    {"model": model, "error": last_error},
                )
                continue

            tool_calls = response.choices[0].message.tool_calls if response.choices else None
            if not tool_calls:
                last_error = "response did not include a structured tool call"
                logger.warning(
                    "Groq model returned no tool call, falling back to next model",
                    {"model": model},
                )
                continue

            if model != config.GROQ_MODEL:
                logger.info("Ticket routed using a fallback model", {"model": model})
            self.last_model_used = model
            return tool_calls[0].function.arguments

        logger.error("All Groq models failed", {"attempted": attempted, "lastError": last_error})
        raise AIUnavailableError(
            "AI service is currently unavailable across all configured models.",
            {"attemptedModels": attempted, "lastError": last_error},
        )
