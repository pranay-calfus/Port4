from typing import Protocol


class AIProvider(Protocol):
    """Structural interface implemented by GroqProvider (the app's only AI
    provider). Keeping this as a Protocol - rather than calling GroqProvider
    directly everywhere - is what lets tests inject a fake provider instead
    of making real network calls.
    """

    # Set by route_ticket() after a successful call, so the caller can find
    # out which model actually answered (relevant with model fallback).
    # Optional by convention - callers read it with getattr(..., None).
    last_model_used: str | None

    def route_ticket(self, message: str, retry_context: str | None = None) -> str:
        """Returns the raw, not-yet-validated JSON string from the model.
        Validation is owned by services.ticket_routing_service, not the
        provider.
        """
        ...
