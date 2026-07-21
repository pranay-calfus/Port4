from fastapi import APIRouter, Depends, HTTPException, status

from backend.auth import require_admin, require_super_admin
from backend.models import Role, TicketStatus
from backend.schemas import (
    AdminCreateRequest,
    AssignRequest,
    MessageCreate,
    MessageOut,
    ReassignRequest,
    StatusUpdateRequest,
    TicketDetailOut,
    TicketOut,
    UserOut,
)
from backend.services import ticket_service
from backend.supabase_client import client

router = APIRouter(prefix="/admin", tags=["admin"])


def _get_visible_ticket(ticket_id: int, admin: dict) -> dict:
    ticket = ticket_service.get_ticket(client, ticket_id)
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
    date_from: str | None = None,
    date_to: str | None = None,
    admin: dict = Depends(require_admin),
):
    return ticket_service.list_tickets_for_admin(
        client,
        admin,
        department=department,
        priority=priority,
        status_filter=status_filter,
        assigned_admin_id=assigned_admin_id,
        search=search,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/tickets/{ticket_id}", response_model=TicketDetailOut)
def get_ticket(ticket_id: int, admin: dict = Depends(require_admin)):
    _get_visible_ticket(ticket_id, admin)  # 404s if missing/out of scope
    return ticket_service.get_ticket_detail(client, ticket_id)


@router.patch("/tickets/{ticket_id}/status", response_model=TicketOut)
def update_status(
    ticket_id: int,
    payload: StatusUpdateRequest,
    admin: dict = Depends(require_admin),
):
    ticket = _get_visible_ticket(ticket_id, admin)
    try:
        return ticket_service.change_status(client, ticket, payload.status)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.patch("/tickets/{ticket_id}/assign", response_model=TicketOut)
def assign_ticket(
    ticket_id: int,
    payload: AssignRequest,
    admin: dict = Depends(require_admin),
):
    ticket = _get_visible_ticket(ticket_id, admin)
    assignee = ticket_service.get_user(client, payload.admin_id)
    if assignee is None or assignee["role"] != Role.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Not a valid admin account"
        )
    if not ticket_service.admin_can_access(assignee, ticket):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That admin isn't scoped to this ticket's department",
        )
    return ticket_service.assign_admin(client, ticket, assignee)


@router.patch("/tickets/{ticket_id}/reassign", response_model=TicketOut)
def reassign_ticket(
    ticket_id: int,
    payload: ReassignRequest,
    admin: dict = Depends(require_admin),
):
    ticket = _get_visible_ticket(ticket_id, admin)
    return ticket_service.reassign(
        client, ticket, department=payload.department, priority=payload.priority
    )


@router.post(
    "/tickets/{ticket_id}/message", response_model=MessageOut, status_code=status.HTTP_201_CREATED
)
def reply_to_ticket(
    ticket_id: int,
    payload: MessageCreate,
    admin: dict = Depends(require_admin),
):
    ticket = _get_visible_ticket(ticket_id, admin)
    try:
        return ticket_service.add_admin_message(client, ticket, admin, payload.message)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.delete("/tickets/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ticket(ticket_id: int, admin: dict = Depends(require_admin)):
    ticket = _get_visible_ticket(ticket_id, admin)
    ticket_service.delete_ticket(client, ticket)


@router.get("/metrics")
def metrics(
    date_from: str | None = None,
    date_to: str | None = None,
    admin: dict = Depends(require_admin),
) -> dict:
    return ticket_service.dashboard_metrics(client, admin, date_from=date_from, date_to=date_to)


@router.get("/admins", response_model=list[dict])
def list_admins(admin: dict = Depends(require_admin)):
    return ticket_service.list_admins(client, admin)


@router.post("/admins", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_admin_account(
    payload: AdminCreateRequest,
    admin: dict = Depends(require_super_admin),
):
    try:
        return ticket_service.create_user(
            client,
            name=payload.name,
            email=payload.email,
            password=payload.password,
            role=Role.ADMIN,
            department=payload.department,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.delete("/admins/{admin_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_admin_account(admin_id: int, admin: dict = Depends(require_super_admin)):
    if admin_id == admin["id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot delete your own account"
        )
    target = ticket_service.get_user(client, admin_id)
    if target is None or target["role"] != Role.ADMIN.value:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found")
    ticket_service.delete_admin(client, target)
