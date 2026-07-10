import json

from pydantic import ValidationError as PydanticValidationError

from ticket_router.ai.base import AIProvider
from ticket_router.ai.combined_provider import CombinedProvider
from ticket_router.errors import AIResponseError
from ticket_router.logger import logger
from ticket_router.models import TicketRouteResult
from ticket_router.services.json_repair import repair_and_parse
from ticket_router.services.prompt_service import summarize_validation_error, truncate_message


def _parse_and_validate(raw: str) -> TicketRouteResult:
    """Parses a raw JSON string and validates it against TicketRouteResult.
    Tries a direct json.loads() first (the common case, since Groq's forced
    tool call already returns well-formed JSON), then falls back to
    string-based repair for anything malformed.

    Raises ValueError or pydantic.ValidationError on failure - callers
    catch these to drive the retry pipeline.
    """
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = repair_and_parse(raw)
        if parsed is None:
            raise ValueError("response was not valid JSON, even after repair attempts") from None

    return TicketRouteResult.model_validate(parsed)


def route_ticket(message: str, provider: AIProvider | None = None) -> TicketRouteResult:
    """Orchestrates the full JSON-reliability pipeline for a single ticket:
        1. Call the AI provider.
        2. Parse and validate (with a repair fallback) against the strict
           schema.
        3. On failure, retry the AI call exactly once with the error
           appended as context, then parse/validate again.
        4. On persistent failure, raise a typed AppError - never an
           unhandled exception.

    This is the project's single reusable routing function - the Streamlit
    UI, tests, and any future CLI/script all call this same function.
    """
    provider = provider or CombinedProvider()

    text, truncated = truncate_message(message)
    if truncated:
        logger.warning(
            "Ticket message truncated before sending to AI", {"original_length": len(message)}
        )

    first_raw = provider.route_ticket(text)
    try:
        result = _parse_and_validate(first_raw)
        result.model_used = getattr(provider, "last_model_used", None)
        return result
    except (ValueError, PydanticValidationError) as first_error:
        error_summary = summarize_validation_error(first_error)
        logger.warning(
            "Initial AI response failed validation, retrying once", {"error": error_summary}
        )

    second_raw = provider.route_ticket(text, retry_context=error_summary)
    try:
        result = _parse_and_validate(second_raw)
        result.model_used = getattr(provider, "last_model_used", None)
        return result
    except (ValueError, PydanticValidationError) as second_error:
        final_summary = summarize_validation_error(second_error)
        logger.error("AI response failed validation after retry", {"error": final_summary})
        raise AIResponseError(
            "The AI service could not produce a valid response after retries.",
            {"lastError": final_summary},
        ) from second_error


if __name__ == "__main__":
    import sys

    text = " ".join(sys.argv[1:]) or "The app keeps crashing every time I open it."
    result = route_ticket(text)
    print(json.dumps(result.model_dump(by_alias=True), indent=2))
