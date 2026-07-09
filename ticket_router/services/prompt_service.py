from ticket_router.models import MAX_TICKET_LENGTH


def truncate_message(message: str) -> tuple[str, bool]:
    """Enforces the documented input-length limit before sending a ticket to
    the AI. Truncation (not rejection) keeps huge inputs usable - see the
    "huge input" edge case in docs/AI-Concepts.md.

    Returns (text, was_truncated).
    """
    if len(message) <= MAX_TICKET_LENGTH:
        return message, False
    return message[:MAX_TICKET_LENGTH], True


def summarize_validation_error(error: Exception) -> str:
    """Builds a concise, human-readable summary of a validation/parse
    failure to hand back to the AI provider as retry context.
    """
    return str(error)
