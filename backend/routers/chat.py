from fastapi import APIRouter, Depends, HTTPException, status

from backend.auth import require_user
from backend.schemas import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatTurn,
    EscalateFeedbackResult,
    EscalateRequest,
    EscalateResponse,
    EscalateTicketResult,
)
from backend.services import feedback_service, ticket_service
from backend.services.ticket_service import _transcript_to_text
from backend.supabase_client import client
from ticket_router.errors import AppError
from ticket_router.services.submission_type_service import classify_submission_type

router = APIRouter(prefix="/chat", tags=["chat"])


def _classify_and_dispatch(
    user: dict, history_tuples: list[tuple[str, str]], priority: str | None = None
) -> EscalateResponse:
    """The single entry point for turning a raised submission into either a
    support ticket or a piece of customer feedback. Runs the fail-soft
    submission-type classifier first (defaults to SUPPORT_ISSUE on any AI
    failure, so nothing is silently dropped), then dispatches to the
    matching peer service. escalate_to_ticket() itself is untouched by this
    branch, so the Support Issue path is exactly what it was before
    Customer Feedback existed.
    """
    transcript = _transcript_to_text(history_tuples)
    kind = classify_submission_type(transcript)
    if kind.submission_type == "CUSTOMER_FEEDBACK":
        feedback = feedback_service.create_feedback_from_chat(client, user, history_tuples)
        return EscalateFeedbackResult(feedback=feedback)
    ticket = ticket_service.escalate_to_ticket(client, user, history_tuples, user_priority=priority)
    return EscalateTicketResult(ticket=ticket)


@router.post("/message", response_model=ChatMessageResponse)
def send_message(
    payload: ChatMessageRequest,
    user: dict = Depends(require_user),  # noqa: ARG001 - login required before chatting, see plan
):
    history_tuples = [(turn.role, turn.content) for turn in payload.history]
    try:
        reply, _classification = ticket_service.reply_to_chat(history_tuples, payload.message)
    except AppError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=error.message
        ) from error

    updated_history = [
        *payload.history,
        ChatTurn(role="user", content=payload.message),
        ChatTurn(role="assistant", content=reply),
    ]
    return ChatMessageResponse(reply=reply, history=updated_history)


@router.post("/escalate", response_model=EscalateResponse, status_code=status.HTTP_201_CREATED)
def escalate(
    payload: EscalateRequest,
    user: dict = Depends(require_user),
):
    history_tuples = [(turn.role, turn.content) for turn in payload.history]
    return _classify_and_dispatch(user, history_tuples, payload.priority)
