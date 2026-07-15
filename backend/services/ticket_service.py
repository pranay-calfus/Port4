"""Business logic for accounts, ticket lifecycle transitions, and the
message/activity trail. Every mutation goes through here (never directly in
a router) so status-transition rules and activity logging happen exactly
once, in one place.
"""

import time
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.auth import hash_password, verify_password
from backend.models import (
    Role,
    SenderType,
    Ticket,
    TicketActivity,
    TicketMessage,
    TicketStatus,
    User,
)
from ticket_router.errors import AppError
from ticket_router.services.agent_service import chat_with_department
from ticket_router.services.ticket_routing_service import route_ticket

UNASSIGNED_DEPARTMENT = "Unassigned"
_DEFAULT_PRIORITY = "Medium"


def _utcnow() -> datetime:
    return datetime.now(UTC)


def log_activity(db: Session, ticket: Ticket, event_type: str, detail: str | None = None) -> None:
    db.add(TicketActivity(ticket_id=ticket.id, event_type=event_type, detail=detail))


# --- Accounts -------------------------------------------------------------


def create_user(
    db: Session,
    *,
    name: str,
    email: str,
    password: str,
    role: Role = Role.USER,
    department: str | None = None,
) -> User:
    email_normalized = email.strip().lower()
    existing = db.execute(select(User).where(User.email == email_normalized)).scalar_one_or_none()
    if existing is not None:
        raise ValueError("An account with this email already exists")

    user = User(
        name=name,
        email=email_normalized,
        password_hash=hash_password(password),
        role=role,
        department=department,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.execute(select(User).where(User.email == email.strip().lower())).scalar_one_or_none()


def authenticate(db: Session, email: str, password: str, role: Role) -> User | None:
    email_normalized = email.strip().lower()
    user = db.execute(select(User).where(User.email == email_normalized)).scalar_one_or_none()
    if user is None or user.role != role:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


# --- Chat escalation --------------------------------------------------------


def _transcript_to_text(history: list[tuple[str, str]]) -> str:
    speaker = {"user": "Customer", "assistant": "AI Assistant"}
    return "\n".join(f"{speaker[role]}: {content}" for role, content in history)


def escalate_to_ticket(
    db: Session,
    user: User,
    history: list[tuple[str, str]],
    user_priority: str | None = None,
) -> Ticket:
    """Turns an unresolved chat conversation into a real ticket: persists
    the transcript as ticket_messages, then classifies it with the same
    route_ticket() used by the original single-message flow. If AI
    categorization fails, the ticket is still created (status stays NEW,
    signaling "not yet triaged") so the customer's request is never lost -
    an admin can triage it manually.

    `user_priority` mirrors the original Router tab's priority picker: the
    customer's own call on urgency. If given, it's what's saved as the
    ticket's effective `priority` even after AI categorization succeeds -
    the AI's own suggestion is still recorded separately as `ai_priority`
    so the UI can show "AI suggested X, you chose Y".
    """
    transcript_text = _transcript_to_text(history)
    first_user_message = next(
        (content for role, content in history if role == "user"), transcript_text
    )
    title = first_user_message[:80] + ("…" if len(first_user_message) > 80 else "")

    ticket = Ticket(
        ticket_number="",
        user_id=user.id,
        title=title,
        description=transcript_text,
        department=UNASSIGNED_DEPARTMENT,
        priority=user_priority or _DEFAULT_PRIORITY,
        status=TicketStatus.NEW,
    )
    db.add(ticket)
    db.flush()  # assigns ticket.id without ending the transaction
    ticket.ticket_number = f"TKT-{ticket.id:05d}"
    log_activity(db, ticket, "Ticket Created", detail="Escalated from chat")

    for role, content in history:
        db.add(
            TicketMessage(
                ticket_id=ticket.id,
                sender_type=SenderType.USER if role == "user" else SenderType.AI,
                sender_id=user.id if role == "user" else None,
                message=content,
            )
        )

    started_at = time.perf_counter()
    try:
        result = route_ticket(transcript_text)
    except AppError as error:
        log_activity(db, ticket, "AI Categorization Failed", detail=str(error))
        db.commit()
        db.refresh(ticket)
        return ticket
    ticket.ai_processing_ms = (time.perf_counter() - started_at) * 1000

    ticket.department = result.assigned_team
    ticket.priority = user_priority or result.priority
    ticket.ai_priority = result.priority
    ticket.ai_summary = result.reasoning
    ticket.ai_category = result.category
    ticket.ai_emotion = result.emotion
    ticket.ai_confidence = result.confidence
    ticket.status = TicketStatus.OPEN
    activity_detail = (
        f"{result.category} → {result.assigned_team} "
        f"({result.priority} priority, {result.emotion} tone, {result.confidence:.0%} confidence)"
    )
    if user_priority and user_priority != result.priority:
        activity_detail += f" - customer set priority to {user_priority}"
    log_activity(db, ticket, "AI Categorized", detail=activity_detail)
    db.commit()
    db.refresh(ticket)
    return ticket


# --- Messages ---------------------------------------------------------------


def _department_auto_reply(db: Session, ticket: Ticket) -> None:
    """Once a ticket has a real department (AI categorization succeeded)
    and no human admin has taken over yet, the department's own
    skills.md-grounded agent keeps responding to the customer directly -
    the same "chat with the assigned team" behavior the original Router
    tab had, just persisted into the ticket's own message thread instead of
    a separate ephemeral chat. This is what makes the chatbot actually
    switch personas once a department is known, instead of staying the
    general first-line bot for the ticket's whole lifetime.

    Stops permanently the moment a human admin sends a reply, so the AI and
    the admin never talk over each other.
    """
    if ticket.department == UNASSIGNED_DEPARTMENT:
        return
    if any(m.sender_type == SenderType.ADMIN for m in ticket.messages):
        return

    ordered = sorted(ticket.messages, key=lambda m: m.created_at)
    history = [
        ("user" if m.sender_type == SenderType.USER else "assistant", m.message) for m in ordered
    ]
    if not history or history[-1][0] != "user":
        return
    *prior_history, (_, latest_message) = history

    try:
        reply = chat_with_department(ticket.department, prior_history, latest_message)
    except AppError as error:
        log_activity(db, ticket, "AI Reply Failed", detail=str(error))
        db.commit()
        return

    db.add(
        TicketMessage(ticket_id=ticket.id, sender_type=SenderType.AI, sender_id=None, message=reply)
    )
    log_activity(db, ticket, "AI Replied", detail=f"{ticket.department} agent")
    db.commit()


def add_user_message(db: Session, ticket: Ticket, user: User, text: str) -> TicketMessage:
    if ticket.status == TicketStatus.CLOSED:
        raise ValueError("This ticket is closed. Please open a new ticket.")

    message = TicketMessage(
        ticket_id=ticket.id, sender_type=SenderType.USER, sender_id=user.id, message=text
    )
    db.add(message)
    log_activity(db, ticket, "Customer Replied")

    if ticket.status == TicketStatus.RESOLVED:
        ticket.status = TicketStatus.IN_PROGRESS
        log_activity(
            db, ticket, "Status Changed", detail="RESOLVED → IN_PROGRESS (customer replied)"
        )

    db.commit()
    db.refresh(message)
    db.refresh(ticket)

    _department_auto_reply(db, ticket)
    db.refresh(message)
    return message


def add_admin_message(db: Session, ticket: Ticket, admin: User, text: str) -> TicketMessage:
    if ticket.status == TicketStatus.CLOSED:
        raise ValueError("This ticket is closed and cannot receive new replies.")

    message = TicketMessage(
        ticket_id=ticket.id, sender_type=SenderType.ADMIN, sender_id=admin.id, message=text
    )
    db.add(message)
    log_activity(db, ticket, "Admin Replied", detail=f"{admin.name}")
    db.commit()
    db.refresh(message)
    return message


# --- Status / assignment -----------------------------------------------------


def change_status(db: Session, ticket: Ticket, new_status: TicketStatus) -> Ticket:
    if ticket.status == TicketStatus.CLOSED:
        raise ValueError("A closed ticket's status cannot be changed.")

    if new_status == ticket.status:
        # No-op: re-selecting the ticket's current status and clicking
        # "Update Status" shouldn't log a redundant "X → X" activity entry.
        return ticket

    old_status = ticket.status
    ticket.status = new_status
    if new_status == TicketStatus.RESOLVED:
        ticket.resolved_at = _utcnow()
    if new_status == TicketStatus.CLOSED:
        ticket.closed_at = _utcnow()

    log_activity(db, ticket, "Status Changed", detail=f"{old_status.value} → {new_status.value}")
    db.commit()
    db.refresh(ticket)
    return ticket


def assign_admin(db: Session, ticket: Ticket, admin: User) -> Ticket:
    ticket.assigned_admin_id = admin.id
    log_activity(db, ticket, "Assigned", detail=f"Assigned to {admin.name}")
    db.commit()
    db.refresh(ticket)
    return ticket


def reassign(db: Session, ticket: Ticket, department: str | None, priority: str | None) -> Ticket:
    changes = []
    if department and department != ticket.department:
        changes.append(f"department {ticket.department} → {department}")
        ticket.department = department
    if priority and priority != ticket.priority:
        changes.append(f"priority {ticket.priority} → {priority}")
        ticket.priority = priority

    if changes:
        log_activity(db, ticket, "Reassigned", detail="; ".join(changes))
        db.commit()
        db.refresh(ticket)
    return ticket


def accept_solution(db: Session, ticket: Ticket) -> Ticket:
    if ticket.status != TicketStatus.RESOLVED:
        raise ValueError("Only a resolved ticket can be accepted.")

    ticket.status = TicketStatus.CLOSED
    ticket.closed_at = _utcnow()
    log_activity(db, ticket, "Closed", detail="Customer accepted the solution")
    db.commit()
    db.refresh(ticket)
    return ticket


def reopen_ticket(db: Session, ticket: Ticket) -> Ticket:
    if ticket.status != TicketStatus.RESOLVED:
        raise ValueError(
            "Only a resolved ticket can be reopened; closed tickets cannot be reopened."
        )

    ticket.status = TicketStatus.IN_PROGRESS
    log_activity(db, ticket, "Status Changed", detail="RESOLVED → IN_PROGRESS (customer reopened)")
    db.commit()
    db.refresh(ticket)
    return ticket


# --- Access control / queries -------------------------------------------------


def admin_can_access(admin: User, ticket: Ticket) -> bool:
    """A super-admin (department is None) can access every ticket; a
    department-scoped admin only their own department's tickets.
    """
    return admin.department is None or admin.department == ticket.department


def list_tickets_for_user(db: Session, user: User) -> list[Ticket]:
    stmt = select(Ticket).where(Ticket.user_id == user.id).order_by(Ticket.created_at.desc())
    return list(db.execute(stmt).scalars().all())


def list_tickets_for_admin(
    db: Session,
    admin: User,
    *,
    department: str | None = None,
    priority: str | None = None,
    status_filter: TicketStatus | None = None,
    assigned_admin_id: int | None = None,
    search: str | None = None,
) -> list[Ticket]:
    stmt = select(Ticket)
    if admin.department is not None:
        stmt = stmt.where(Ticket.department == admin.department)
    if department:
        stmt = stmt.where(Ticket.department == department)
    if priority:
        stmt = stmt.where(Ticket.priority == priority)
    if status_filter:
        stmt = stmt.where(Ticket.status == status_filter)
    if assigned_admin_id is not None:
        stmt = stmt.where(Ticket.assigned_admin_id == assigned_admin_id)
    stmt = stmt.order_by(Ticket.created_at.desc())

    tickets = list(db.execute(stmt).scalars().all())
    if search:
        needle = search.strip().lower()
        tickets = [
            t
            for t in tickets
            if needle in t.title.lower()
            or needle in t.description.lower()
            or needle in t.ticket_number.lower()
        ]
    return tickets


def dashboard_metrics(db: Session, admin: User) -> dict:
    tickets = list_tickets_for_admin(db, admin)
    open_tickets = [t for t in tickets if t.status != TicketStatus.CLOSED]

    resolution_hours = [
        (t.resolved_at - t.created_at).total_seconds() / 3600
        for t in tickets
        if t.resolved_at is not None
    ]

    per_department: dict[str, int] = {}
    per_status: dict[str, int] = {}
    for ticket in tickets:
        per_department[ticket.department] = per_department.get(ticket.department, 0) + 1
        per_status[ticket.status.value] = per_status.get(ticket.status.value, 0) + 1

    return {
        "open_tickets": len(open_tickets),
        "total_tickets": len(tickets),
        "avg_resolution_hours": (
            sum(resolution_hours) / len(resolution_hours) if resolution_hours else None
        ),
        "tickets_per_department": per_department,
        "tickets_per_status": per_status,
    }
