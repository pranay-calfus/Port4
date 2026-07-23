from ticket_router.ai.tool_classifier import run_classifier
from ticket_router.ai.tool_schema import (
    CLASSIFY_SUBMISSION_TYPE_TOOL,
    CLASSIFY_SUBMISSION_TYPE_TOOL_NAME,
)
from ticket_router.config import config
from ticket_router.errors import AppError
from ticket_router.logger import logger
from ticket_router.models import SubmissionTypeResult
from ticket_router.prompts import SUBMISSION_TYPE_SYSTEM_PROMPT


def classify_submission_type(transcript: str) -> SubmissionTypeResult:
    """Classifies a raised submission's transcript as a Support Issue or
    Customer Feedback. This is the first classifier run on any submission -
    see backend.routers.chat._classify_and_dispatch.

    Runs through the same shared reliability pipeline
    (ticket_router.ai.tool_classifier.run_classifier) as every other
    classifier in this app - multi-model fallback, retry-once-with-error-
    context. Failures never raise past this function, though: they degrade
    to SUPPORT_ISSUE, the platform's existing behavior before this
    classifier existed, so an AI outage never silently drops a submission
    from the support queue.
    """
    if not config.OPENAI_API_KEY:
        return SubmissionTypeResult(
            submission_type="SUPPORT_ISSUE", reasoning="AI service is not configured."
        )

    try:
        return run_classifier(
            system_prompt=SUBMISSION_TYPE_SYSTEM_PROMPT,
            message=transcript,
            tool=CLASSIFY_SUBMISSION_TYPE_TOOL,
            tool_name=CLASSIFY_SUBMISSION_TYPE_TOOL_NAME,
            result_model=SubmissionTypeResult,
            max_tokens=256,
        )
    except AppError as error:
        logger.warning("Submission type classification failed", {"error": str(error)})
        return SubmissionTypeResult(
            submission_type="SUPPORT_ISSUE", reasoning="Classification unavailable."
        )
