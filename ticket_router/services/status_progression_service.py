from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from ticket_router.ai.openai_provider import build_model_chain
from ticket_router.ai.tool_schema import (
    CHECK_STATUS_PROGRESSION_TOOL,
    CHECK_STATUS_PROGRESSION_TOOL_NAME,
)
from ticket_router.config import config
from ticket_router.logger import logger
from ticket_router.models import NO_STATUS_CHANGE, StatusProgressionCheck
from ticket_router.prompts import STATUS_PROGRESSION_SYSTEM_PROMPT


def _build_llm() -> ChatOpenAI:
    primary_model, *_ = build_model_chain()
    return ChatOpenAI(
        api_key=config.OPENAI_API_KEY,
        model=primary_model,
        max_tokens=256,
        temperature=0,
    ).bind_tools([CHECK_STATUS_PROGRESSION_TOOL], tool_choice=CHECK_STATUS_PROGRESSION_TOOL_NAME)


def check_status_progression(
    transcript: str, latest_customer_message: str, current_status: str
) -> StatusProgressionCheck:
    """Classifies whether the conversation so far indicates `current_status`
    (one of OPEN/IN_PROGRESS/PENDING_CUSTOMER/ON_HOLD) should move to another
    of those four mid-lifecycle statuses. Used by backend.services.ticket_service
    to let the department bot autonomously advance a ticket through its
    lifecycle as the conversation clearly warrants it - the same idea as
    check_resolution, just for the stages before resolution.

    This is a best-effort, secondary classifier layered on top of an
    already-successful bot reply, so failures never raise - they degrade to
    "NO_CHANGE" (the ticket simply keeps its current status) rather than
    risking the primary reply flow.
    """
    if not config.OPENAI_API_KEY:
        return StatusProgressionCheck(
            recommended_status=NO_STATUS_CHANGE, reasoning="AI service is not configured."
        )

    messages = [
        SystemMessage(content=STATUS_PROGRESSION_SYSTEM_PROMPT),
        HumanMessage(
            content=(
                f"Current status: {current_status}\n\n"
                f"Conversation so far:\n{transcript}\n\n"
                f"Customer's latest message:\n{latest_customer_message}"
            )
        ),
    ]

    try:
        response = _build_llm().invoke(messages)
    except Exception as error:  # noqa: BLE001 - best-effort, never blocks the reply flow
        logger.warning("Status progression check call failed", {"error": str(error)})
        return StatusProgressionCheck(
            recommended_status=NO_STATUS_CHANGE, reasoning="Status progression check unavailable."
        )

    tool_calls = response.tool_calls
    if not tool_calls:
        logger.warning("Status progression check returned no tool call")
        return StatusProgressionCheck(
            recommended_status=NO_STATUS_CHANGE, reasoning="No structured response from the model."
        )

    try:
        return StatusProgressionCheck.model_validate(tool_calls[0]["args"])
    except Exception as error:  # noqa: BLE001 - malformed args degrade to "NO_CHANGE"
        logger.warning("Status progression check returned invalid arguments", {"error": str(error)})
        return StatusProgressionCheck(
            recommended_status=NO_STATUS_CHANGE, reasoning="Invalid response from the model."
        )
