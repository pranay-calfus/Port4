from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.auth import require_admin
from backend.db import get_db
from backend.models import Role, Ticket, TicketStatus, User
from backend.schemas import (
    AssignRequest,
    MessageCreate,
    MessageOut,
    ReassignRequest,
    StatusUpdateRequest,
    TicketDetailOut,
    TicketOut,
)
from backend.services import ticket_service

router = APIRouter(prefix="/admin", tags=["admin"])


def _get_visible_ticket(db: Session, ticket_id: int, admin: User) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None or not ticket_service.admin_can_access(admin, ticket):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return ticket


@router.get("/tickets", response_model=list[TicketOut])
def list_tickets(
    department: str | None = None,
    priority: str | None = None,
    status_filter: TicketStatus | None = None,
    assigned_admin_id: int | None = None,
    search: str | None = None,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return ticket_service.list_tickets_for_admin(
        db,
        admin,
        department=department,
        priority=priority,
        status_filter=status_filter,
        assigned_admin_id=assigned_admin_id,
        search=search,
    )


@router.get("/tickets/{ticket_id}", response_model=TicketDetailOut)
def get_ticket(ticket_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return _get_visible_ticket(db, ticket_id, admin)


@router.patch("/tickets/{ticket_id}/status", response_model=TicketOut)
def update_status(
    ticket_id: int,
    payload: StatusUpdateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ticket = _get_visible_ticket(db, ticket_id, admin)
    try:
        return ticket_service.change_status(db, ticket, payload.status)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.patch("/tickets/{ticket_id}/assign", response_model=TicketOut)
def assign_ticket(
    ticket_id: int,
    payload: AssignRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ticket = _get_visible_ticket(db, ticket_id, admin)
    assignee = db.get(User, payload.admin_id)
    if assignee is None or assignee.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Not a valid admin account"
        )
    if not ticket_service.admin_can_access(assignee, ticket):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That admin isn't scoped to this ticket's department",
        )
    return ticket_service.assign_admin(db, ticket, assignee)


@router.patch("/tickets/{ticket_id}/reassign", response_model=TicketOut)
def reassign_ticket(
    ticket_id: int,
    payload: ReassignRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ticket = _get_visible_ticket(db, ticket_id, admin)
    return ticket_service.reassign(
        db, ticket, department=payload.department, priority=payload.priority
    )


@router.post(
    "/tickets/{ticket_id}/message", response_model=MessageOut, status_code=status.HTTP_201_CREATED
)
def reply_to_ticket(
    ticket_id: int,
    payload: MessageCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ticket = _get_visible_ticket(db, ticket_id, admin)
    try:
        return ticket_service.add_admin_message(db, ticket, admin, payload.message)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.get("/metrics")
def metrics(admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    return ticket_service.dashboard_metrics(db, admin)


@router.get("/admins", response_model=list[dict])
def list_admins(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    stmt = select(User).where(User.role == Role.ADMIN)
    if admin.department is not None:
        stmt = stmt.where(User.department == admin.department)
    admins = db.execute(stmt).scalars().all()
    return [
        {"id": a.id, "name": a.name, "email": a.email, "department": a.department} for a in admins
    ]
