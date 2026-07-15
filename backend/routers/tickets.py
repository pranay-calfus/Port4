from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth import require_user
from backend.db import get_db
from backend.models import Ticket, User
from backend.schemas import BulkTicketRequest, MessageCreate, MessageOut, TicketDetailOut, TicketOut
from backend.services import ticket_service

router = APIRouter(prefix="/tickets", tags=["tickets"])


def _get_owned_ticket(db: Session, ticket_id: int, user: User) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None or ticket.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return ticket


@router.get("", response_model=list[TicketOut])
def list_my_tickets(
    user: User = Depends(require_user), db: Session = Depends(get_db)
) -> list[Ticket]:
    return ticket_service.list_tickets_for_user(db, user)


# Registered before "/{ticket_id}" - otherwise FastAPI would try to parse
# the literal path segment "bulk" as that int path parameter and 422 first.
@router.post("/bulk", response_model=list[TicketDetailOut], status_code=status.HTTP_201_CREATED)
def bulk_create_tickets(
    payload: BulkTicketRequest,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> list[Ticket]:
    """Creates one ticket per pasted description, each classified
    independently via the same escalate_to_ticket() pipeline as the
    chat-escalation flow (just with a single-turn "history" instead of a
    real conversation).
    """
    return [
        ticket_service.escalate_to_ticket(db, user, [("user", message)])
        for message in payload.messages
    ]


@router.get("/{ticket_id}", response_model=TicketDetailOut)
def get_ticket(
    ticket_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)
) -> Ticket:
    return _get_owned_ticket(db, ticket_id, user)


@router.post(
    "/{ticket_id}/messages", response_model=MessageOut, status_code=status.HTTP_201_CREATED
)
def reply_to_ticket(
    ticket_id: int,
    payload: MessageCreate,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    ticket = _get_owned_ticket(db, ticket_id, user)
    try:
        return ticket_service.add_user_message(db, ticket, user, payload.message)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.post("/{ticket_id}/accept-solution", response_model=TicketOut)
def accept_solution(
    ticket_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)
):
    ticket = _get_owned_ticket(db, ticket_id, user)
    try:
        return ticket_service.accept_solution(db, ticket)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.post("/{ticket_id}/reopen", response_model=TicketOut)
def reopen_ticket(
    ticket_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)
):
    ticket = _get_owned_ticket(db, ticket_id, user)
    try:
        return ticket_service.reopen_ticket(db, ticket)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
