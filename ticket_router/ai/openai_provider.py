import json

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from ticket_router.ai.tool_schema import ROUTE_TICKET_TOOL, ROUTE_TICKET_TOOL_NAME
from ticket_router.config import config
from ticket_router.errors import AIUnavailableError
from ticket_router.logger import logger
from ticket_router.prompts import SYSTEM_PROMPT

# Auth failures are a property of the API key, not the model - retrying
# with a different model would just fail the same way, so we fail fast
# instead of burning the whole fallback chain on a bad key.
_NON_RETRYABLE_STATUS_CODES = (401, 403)


def build_model_chain() -> list[str]:
    """The configured primary model, plus any fallback models explicitly
    listed in OPENAI_FALLBACK_MODELS (comma-separated, deduplicated, order
    preserved). Fallback is opt-in: with OPENAI_FALLBACK_MODELS unset, the
    chain is just [OPENAI_MODEL] and a failure raises immediately.
    """
    fallbacks = [m.strip() for m in config.OPENAI_FALLBACK_MODELS.split(",") if m.strip()]
    return list(dict.fromkeys([config.OPENAI_MODEL, *fallbacks]))


def _is_non_retryable(error: Exception) -> bool:
    status_code = getattr(error, "status_code", None)
    return status_code in _NON_RETRYABLE_STATUS_CODES


class OpenAIProvider:
    """The application's only AI provider - OpenAI's Chat Completions API,
    called through LangChain's ChatOpenAI.

    If the configured model fails (rate limit, timeout, decommissioned
    model, transient 5xx, or a response with no structured tool call), it
    automatically falls back to the next model in `build_model_chain()`
    rather than failing the whole request.
    """

    def __init__(self) -> None:
        self._llms: dict[str, ChatOpenAI] = {}
        # Which model actually answered the most recent successful call -
        # read by the routing service so the UI can show it.
        self.last_model_used: str | None = None

    def _get_llm(self, model: str) -> ChatOpenAI:
        if not config.OPENAI_API_KEY:
            raise AIUnavailableError(
                "AI service unavailable: OPENAI_API_KEY is not configured. Set it in .env."
            )
        if model not in self._llms:
            self._llms[model] = ChatOpenAI(
                api_key=config.OPENAI_API_KEY,
                model=model,
                max_tokens=1024,
                # This is a structured classification task, not creative
                # generation - temperature=0 makes routing decisions
                # reproducible instead of the same ticket landing on a
                # different category/priority/team from one run to the next.
                temperature=0,
            ).bind_tools(
                [ROUTE_TICKET_TOOL],
                tool_choice=ROUTE_TICKET_TOOL_NAME,
            )
        return self._llms[model]

    def route_ticket(self, message: str, retry_context: str | None = None) -> str:
        # Raises immediately if the key is missing, before spending any
        # attempts on the model chain.
        self._get_llm(config.OPENAI_MODEL)

        user_content = message
        if retry_context:
            user_content = (
                f"{message}\n\n[SYSTEM NOTICE] Your previous response failed validation: "
                f"{retry_context}. Re-emit strictly valid arguments via the "
                f"{ROUTE_TICKET_TOOL_NAME} tool only."
            )

        messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_content)]

        attempted: list[str] = []
        last_error: str | None = None

        for model in build_model_chain():
            attempted.append(model)
            llm = self._get_llm(model)
            try:
                response = llm.invoke(messages)
            except Exception as error:  # noqa: BLE001 - evaluated below
                if _is_non_retryable(error):
                    logger.error(
                        "OpenAI API call failed (non-retryable)",
                        {"model": model, "error": str(error)},
                    )
                    raise AIUnavailableError(
                        "AI service is currently unavailable.",
                        {"cause": str(error), "model": model},
                    ) from error
                last_error = str(error)
                logger.warning(
                    "OpenAI model failed, falling back to next model",
                    {"model": model, "error": last_error},
                )
                continue

            tool_calls = response.tool_calls
            if not tool_calls:
                last_error = "response did not include a structured tool call"
                logger.warning(
                    "OpenAI model returned no tool call, falling back to next model",
                    {"model": model},
                )
                continue

            if model != config.OPENAI_MODEL:
                logger.info("Ticket routed using a fallback model", {"model": model})
            self.last_model_used = model
            return json.dumps(tool_calls[0]["args"])

        logger.error("All OpenAI models failed", {"attempted": attempted, "lastError": last_error})
        raise AIUnavailableError(
            "AI service is currently unavailable across all configured models.",
            {"attemptedModels": attempted, "lastError": last_error},
        )
