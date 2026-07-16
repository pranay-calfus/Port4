from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth import require_user
from backend.db import get_db
from backend.models import User
from backend.schemas import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatTurn,
    EscalateRequest,
    TicketDetailOut,
)
from backend.services import ticket_service
from ticket_router.errors import AppError

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/message", response_model=ChatMessageResponse)
def send_message(
    payload: ChatMessageRequest,
    user: User = Depends(require_user),  # noqa: ARG001 - login required before chatting, see plan
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


@router.post("/escalate", response_model=TicketDetailOut, status_code=status.HTTP_201_CREATED)
def escalate(
    payload: EscalateRequest,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    history_tuples = [(turn.role, turn.content) for turn in payload.history]
    return ticket_service.escalate_to_ticket(
        db, user, history_tuples, user_priority=payload.priority
    )
