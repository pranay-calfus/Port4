from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from ticket_router.ai.openai_provider import build_model_chain
from ticket_router.ai.tool_schema import CLASSIFY_FEEDBACK_TOOL, CLASSIFY_FEEDBACK_TOOL_NAME
from ticket_router.config import config
from ticket_router.logger import logger
from ticket_router.models import FeedbackClassification
from ticket_router.prompts import FEEDBACK_CLASSIFICATION_SYSTEM_PROMPT


def _build_llm() -> ChatOpenAI:
    primary_model, *_ = build_model_chain()
    return ChatOpenAI(
        api_key=config.OPENAI_API_KEY,
        model=primary_model,
        max_tokens=512,
        temperature=0,
    ).bind_tools([CLASSIFY_FEEDBACK_TOOL], tool_choice=CLASSIFY_FEEDBACK_TOOL_NAME)


def _fallback_summary(text: str) -> str:
    first_line = text.strip().splitlines()[0] if text.strip() else "No summary available."
    return first_line[:200]


def _default_classification(text: str, reasoning: str) -> FeedbackClassification:
    return FeedbackClassification(
        sentiment="Neutral",
        category="Other",
        assignedTeam="Customer Success",
        theme="Uncategorized",
        summary=_fallback_summary(text),
        reasoning=reasoning,
        confidence=0.0,
    )


def classify_feedback(text: str) -> FeedbackClassification:
    """Classifies a piece of customer feedback: sentiment, category, the
    internal team it's most relevant to, and an AI-generated summary. Used
    by backend.services.feedback_service.create_feedback_from_chat.

    This is a best-effort classifier, layered on top of an already-created
    feedback row, so failures never raise - they degrade to a safe default
    classification (Neutral/Other/Customer Success, confidence 0.0) rather
    than losing the customer's submission.
    """
    if not config.OPENAI_API_KEY:
        return _default_classification(text, "AI service is not configured.")

    messages = [
        SystemMessage(content=FEEDBACK_CLASSIFICATION_SYSTEM_PROMPT),
        HumanMessage(content=text),
    ]

    try:
        response = _build_llm().invoke(messages)
    except Exception as error:  # noqa: BLE001 - best-effort, never blocks submission
        logger.warning("Feedback classification call failed", {"error": str(error)})
        return _default_classification(text, "Classification unavailable.")

    tool_calls = response.tool_calls
    if not tool_calls:
        logger.warning("Feedback classification returned no tool call")
        return _default_classification(text, "No structured response from the model.")

    try:
        return FeedbackClassification.model_validate(tool_calls[0]["args"])
    except Exception as error:  # noqa: BLE001 - malformed args degrade to the safe default
        logger.warning("Feedback classification returned invalid arguments", {"error": str(error)})
        return _default_classification(text, "Invalid response from the model.")
