from fastapi import APIRouter, Depends, HTTPException, status

from backend.auth import require_user
from backend.models import TicketStatus
from backend.schemas import (
    MessageCreate,
    MessageOut,
    TicketDetailOut,
    TicketOut,
    UpdatePriorityRequest,
)
from backend.services import ticket_service
from backend.supabase_client import client

router = APIRouter(prefix="/tickets", tags=["tickets"])


def _get_owned_ticket(ticket_id: int, user: dict) -> dict:
    ticket = ticket_service.get_ticket(client, ticket_id)
    if ticket is None or ticket["user_id"] != user["id"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return ticket


@router.get("", response_model=list[TicketOut])
def list_my_tickets(user: dict = Depends(require_user)) -> list[dict]:
    return ticket_service.list_tickets_for_user(client, user)


@router.get("/{ticket_id}", response_model=TicketDetailOut)
def get_ticket(ticket_id: int, user: dict = Depends(require_user)) -> dict:
    _get_owned_ticket(ticket_id, user)  # 404s if missing/not owned
    return ticket_service.get_ticket_detail(client, ticket_id)


@router.post(
    "/{ticket_id}/messages", response_model=MessageOut, status_code=status.HTTP_201_CREATED
)
def reply_to_ticket(
    ticket_id: int,
    payload: MessageCreate,
    user: dict = Depends(require_user),
):
    ticket = _get_owned_ticket(ticket_id, user)
    try:
        return ticket_service.add_user_message(client, ticket, user, payload.message)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.post("/{ticket_id}/accept-solution", response_model=TicketOut)
def accept_solution(ticket_id: int, user: dict = Depends(require_user)):
    ticket = _get_owned_ticket(ticket_id, user)
    try:
        return ticket_service.accept_solution(client, ticket)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.post("/{ticket_id}/reopen", response_model=TicketOut)
def reopen_ticket(ticket_id: int, user: dict = Depends(require_user)):
    ticket = _get_owned_ticket(ticket_id, user)
    try:
        return ticket_service.reopen_ticket(client, ticket)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.patch("/{ticket_id}/priority", response_model=TicketOut)
def update_ticket_priority(
    ticket_id: int,
    payload: UpdatePriorityRequest,
    user: dict = Depends(require_user),
):
    ticket = _get_owned_ticket(ticket_id, user)
    if ticket["status"] == TicketStatus.CLOSED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Cannot change priority on a closed ticket"
        )
    return ticket_service.update_priority(client, ticket, payload.priority)
