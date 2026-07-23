import json

from ticket_router.ai.tool_classifier import run_classifier
from ticket_router.ai.tool_schema import (
    GENERATE_WEEKLY_SUMMARY_TOOL,
    GENERATE_WEEKLY_SUMMARY_TOOL_NAME,
)
from ticket_router.config import config
from ticket_router.errors import AIUnavailableError
from ticket_router.models import WeeklySummaryResult
from ticket_router.prompts import WEEKLY_SUMMARY_SYSTEM_PROMPT


def generate_weekly_narrative(metrics: dict) -> WeeklySummaryResult:
    """Turns a week's pre-aggregated feedback metrics (counts/themes/
    excerpts - never raw per-row data) into the narrative sections of a
    weekly report, via the same forced-tool-call reliability pipeline
    (ticket_router.ai.tool_classifier.run_classifier) as every other
    classifier in this app.

    Unlike classify_feedback/classify_submission_type, this raises
    AIUnavailableError/AIResponseError on persistent failure rather than
    degrading to a safe default - there's no partial customer submission to
    protect here, just a report that either can or can't be produced yet
    (see backend.services.weekly_summary_service for how the caller handles
    that: the manual endpoint surfaces it as a 503, the scheduled job logs
    it and retries next Monday).
    """
    if not config.OPENAI_API_KEY:
        raise AIUnavailableError(
            "AI service unavailable: OPENAI_API_KEY is not configured. Set it in .env."
        )

    return run_classifier(
        system_prompt=WEEKLY_SUMMARY_SYSTEM_PROMPT,
        message=json.dumps(metrics),
        tool=GENERATE_WEEKLY_SUMMARY_TOOL,
        tool_name=GENERATE_WEEKLY_SUMMARY_TOOL_NAME,
        result_model=WeeklySummaryResult,
        max_tokens=1536,
    )
