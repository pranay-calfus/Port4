from ticket_router.ai.tool_classifier import run_classifier
from ticket_router.ai.tool_schema import CLASSIFY_FEEDBACK_TOOL, CLASSIFY_FEEDBACK_TOOL_NAME
from ticket_router.config import config
from ticket_router.errors import AppError
from ticket_router.logger import logger
from ticket_router.models import FeedbackClassification
from ticket_router.prompts import FEEDBACK_CLASSIFICATION_SYSTEM_PROMPT


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
    internal team it's most relevant to, a recurring theme, and an
    AI-generated summary. Used by
    backend.services.feedback_service.create_feedback_from_chat.

    Runs through the same shared reliability pipeline
    (ticket_router.ai.tool_classifier.run_classifier) as every other
    classifier in this app - multi-model fallback, retry-once-with-error-
    context. This is a best-effort classifier, though, layered on top of an
    already-created feedback row, so failures never raise past this
    function - they degrade to a safe default classification
    (Neutral/Other/Customer Success, confidence 0.0) rather than losing the
    customer's submission.
    """
    if not config.OPENAI_API_KEY:
        return _default_classification(text, "AI service is not configured.")

    try:
        return run_classifier(
            system_prompt=FEEDBACK_CLASSIFICATION_SYSTEM_PROMPT,
            message=text,
            tool=CLASSIFY_FEEDBACK_TOOL,
            tool_name=CLASSIFY_FEEDBACK_TOOL_NAME,
            result_model=FeedbackClassification,
            max_tokens=512,
        )
    except AppError as error:
        logger.warning("Feedback classification failed", {"error": str(error)})
        return _default_classification(text, "Classification unavailable.")
