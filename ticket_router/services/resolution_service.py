from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from ticket_router.ai.openai_provider import build_model_chain
from ticket_router.ai.tool_schema import CHECK_RESOLUTION_TOOL, CHECK_RESOLUTION_TOOL_NAME
from ticket_router.config import config
from ticket_router.logger import logger
from ticket_router.models import ResolutionCheck
from ticket_router.prompts import RESOLUTION_CHECK_SYSTEM_PROMPT


def _build_llm() -> ChatOpenAI:
    primary_model, *_ = build_model_chain()
    return ChatOpenAI(
        api_key=config.OPENAI_API_KEY,
        model=primary_model,
        max_tokens=256,
        temperature=0,
    ).bind_tools([CHECK_RESOLUTION_TOOL], tool_choice=CHECK_RESOLUTION_TOOL_NAME)


def check_resolution(transcript: str, latest_customer_message: str) -> ResolutionCheck:
    """Classifies whether `latest_customer_message` (the customer's newest
    reply on a ticket, with the rest of the thread in `transcript` for
    context) confirms the issue is resolved and the ticket can be closed.
    Used by backend.services.ticket_service to let the department bot
    autonomously move a ticket to RESOLVED then CLOSED once the customer
    confirms - the same outcome a human admin gets via accept_solution().

    This is a best-effort, secondary classifier layered on top of an
    already-successful bot reply, so failures never raise - they degrade to
    resolved=False (the ticket simply stays open, same as if this feature
    didn't exist) rather than risking the primary reply flow.
    """
    if not config.OPENAI_API_KEY:
        return ResolutionCheck(resolved=False, reasoning="AI service is not configured.")

    messages = [
        SystemMessage(content=RESOLUTION_CHECK_SYSTEM_PROMPT),
        HumanMessage(
            content=(
                f"Conversation so far:\n{transcript}\n\n"
                f"Customer's latest message:\n{latest_customer_message}"
            )
        ),
    ]

    try:
        response = _build_llm().invoke(messages)
    except Exception as error:  # noqa: BLE001 - best-effort, never blocks the reply flow
        logger.warning("Resolution check call failed", {"error": str(error)})
        return ResolutionCheck(resolved=False, reasoning="Resolution check unavailable.")

    tool_calls = response.tool_calls
    if not tool_calls:
        logger.warning("Resolution check returned no tool call")
        return ResolutionCheck(resolved=False, reasoning="No structured response from the model.")

    try:
        return ResolutionCheck.model_validate(tool_calls[0]["args"])
    except Exception as error:  # noqa: BLE001 - malformed args degrade to "not resolved"
        logger.warning("Resolution check returned invalid arguments", {"error": str(error)})
        return ResolutionCheck(resolved=False, reasoning="Invalid response from the model.")
