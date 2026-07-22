from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from ticket_router.ai.openai_provider import build_model_chain
from ticket_router.ai.tool_schema import (
    CLASSIFY_SUBMISSION_TYPE_TOOL,
    CLASSIFY_SUBMISSION_TYPE_TOOL_NAME,
)
from ticket_router.config import config
from ticket_router.logger import logger
from ticket_router.models import SubmissionTypeResult
from ticket_router.prompts import SUBMISSION_TYPE_SYSTEM_PROMPT


def _build_llm() -> ChatOpenAI:
    primary_model, *_ = build_model_chain()
    return ChatOpenAI(
        api_key=config.OPENAI_API_KEY,
        model=primary_model,
        max_tokens=256,
        temperature=0,
    ).bind_tools([CLASSIFY_SUBMISSION_TYPE_TOOL], tool_choice=CLASSIFY_SUBMISSION_TYPE_TOOL_NAME)


def classify_submission_type(transcript: str) -> SubmissionTypeResult:
    """Classifies a raised submission's transcript as a Support Issue or
    Customer Feedback. This is the first classifier run on any submission -
    see backend.routers.chat._classify_and_dispatch.

    Failures never raise: they degrade to SUPPORT_ISSUE, the platform's
    existing behavior before this classifier existed, so an AI outage never
    silently drops a submission from the support queue.
    """
    if not config.OPENAI_API_KEY:
        return SubmissionTypeResult(
            submission_type="SUPPORT_ISSUE", reasoning="AI service is not configured."
        )

    messages = [
        SystemMessage(content=SUBMISSION_TYPE_SYSTEM_PROMPT),
        HumanMessage(content=transcript),
    ]

    try:
        response = _build_llm().invoke(messages)
    except Exception as error:  # noqa: BLE001 - best-effort, never blocks submission
        logger.warning("Submission type classification call failed", {"error": str(error)})
        return SubmissionTypeResult(
            submission_type="SUPPORT_ISSUE", reasoning="Classification unavailable."
        )

    tool_calls = response.tool_calls
    if not tool_calls:
        logger.warning("Submission type classification returned no tool call")
        return SubmissionTypeResult(
            submission_type="SUPPORT_ISSUE", reasoning="No structured response from the model."
        )

    try:
        return SubmissionTypeResult.model_validate(tool_calls[0]["args"])
    except Exception as error:  # noqa: BLE001 - malformed args degrade to SUPPORT_ISSUE
        logger.warning(
            "Submission type classification returned invalid arguments", {"error": str(error)}
        )
        return SubmissionTypeResult(
            submission_type="SUPPORT_ISSUE", reasoning="Invalid response from the model."
        )
