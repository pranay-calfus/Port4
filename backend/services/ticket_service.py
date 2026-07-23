"""Business logic for accounts, ticket lifecycle transitions, and the
message/activity trail. Every mutation goes through here (never directly in
a router) so status-transition rules and activity logging happen exactly
once, in one place.

Every function takes a Supabase client (backend/supabase_client.py) instead
of a SQLAlchemy Session, and works with plain dicts instead of ORM objects -
each `.execute()` call is its own HTTP request to Supabase's PostgREST API,
committed immediately, with no multi-statement transaction spanning several
calls the way a SQLAlchemy Session used to provide. Timestamps read back
from Postgres come through as ISO 8601 strings, not datetime objects - see
_parse_dt() where date arithmetic is needed.
"""

import time
from datetime import UTC, datetime

from supabase import Client

from backend.auth import hash_password, verify_password
from backend.models import Role, SenderType, TicketStatus
from backend.services.theme_normalization import group_themes
from ticket_router.errors import AppError
from ticket_router.models import NO_STATUS_CHANGE
from ticket_router.services.agent_service import chat_with_department, chat_with_general_agent
from ticket_router.services.resolution_service import check_resolution
from ticket_router.services.status_progression_service import check_status_progression
from ticket_router.services.ticket_routing_service import route_ticket

UNASSIGNED_DEPARTMENT = "Unassigned"
_DEFAULT_PRIORITY = "Medium"


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _maybe_single(query) -> dict | None:
    # postgrest-py's .maybe_single().execute() returns None outright (not a
    # response object with .data=None) when zero rows match - normalize that
    # here so callers can just check `is None` on the return value.
    result = query.maybe_single().execute()
    return result.data if result is not None else None


def log_activity(
    client: Client, ticket_id: int, event_type: str, detail: str | None = None
) -> None:
    client.table("ticket_activity").insert(
        {"ticket_id": ticket_id, "event_type": event_type, "detail": detail}
    ).execute()


# --- Accounts -------------------------------------------------------------


def create_user(
    client: Client,
    *,
    name: str,
    email: str,
    password: str,
    role: Role = Role.USER,
    department: str | None = None,
) -> dict:
    email_normalized = email.strip().lower()
    existing = client.table("users").select("id").eq("email", email_normalized).execute()
    if existing.data:
        raise ValueError("An account with this email already exists")

    result = (
        client.table("users")
        .insert(
            {
                "name": name,
                "email": email_normalized,
                "password_hash": hash_password(password),
                "role": role.value,
                "department": department,
            }
        )
        .execute()
    )
    return result.data[0]


def get_user_by_email(client: Client, email: str) -> dict | None:
    result = client.table("users").select("*").eq("email", email.strip().lower()).execute()
    return result.data[0] if result.data else None


def get_user(client: Client, user_id: int) -> dict | None:
    return _maybe_single(client.table("users").select("*").eq("id", user_id))


def list_admins(client: Client, admin: dict) -> list[dict]:
    """Admin accounts visible to `admin` for the ticket-assignment dropdown -
    every admin if `admin` is a super-admin, otherwise just their own
    department's admins. Deliberately excludes PRODUCT_CX accounts - they
    don't handle tickets, so they must never appear as an assignment target.
    """
    query = client.table("users").select("id,name,email,department").eq("role", Role.ADMIN.value)
    if admin["department"] is not None:
        query = query.eq("department", admin["department"])
    return query.execute().data


def list_team_accounts(client: Client) -> list[dict]:
    """Every non-customer account (ADMIN and PRODUCT_CX) for the super-admin
    team-management screen - unlike list_admins, this deliberately includes
    PRODUCT_CX accounts so they're visible/deletable there, even though they
    must stay out of the ticket-assignment dropdown.
    """
    return (
        client.table("users")
        .select("id,name,email,department,role")
        .in_("role", [Role.ADMIN.value, Role.PRODUCT_CX.value])
        .execute()
        .data
    )


def delete_admin(client: Client, target: dict) -> None:
    """Permanently removes a team/admin account. Tickets they were assigned
    to are unassigned rather than blocked or deleted - see the
    ondelete="SET NULL" foreign keys on Ticket.assigned_admin_id and
    TicketMessage.sender_id (backend/models.py) - so ticket and message
    history survives the admin account being removed. Irreversible - the
    router requires the caller to be a super-admin and to not be deleting
    their own account.
    """
    client.table("users").delete().eq("id", target["id"]).execute()


def authenticate(client: Client, email: str, password: str, role: Role) -> dict | None:
    user = get_user_by_email(client, email)
    if user is None or user["role"] != role.value:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user


# --- Chat escalation --------------------------------------------------------


def _transcript_to_text(history: list[tuple[str, str]]) -> str:
    speaker = {"user": "Customer", "assistant": "AI Assistant"}
    return "\n".join(f"{speaker[role]}: {content}" for role, content in history)


def reply_to_chat(history: list[tuple[str, str]], message: str):
    """Powers the pre-ticket chat endpoint. Classifies the conversation so
    far - the same route_ticket() used at escalation time - as soon as the
    customer sends a message, so the reply comes from the right
    department's skills.md-grounded persona (see chat_with_department) from
    the first turn, not a generic assistant. No ticket exists yet; this is
    purely picking who answers. Falls back to the general first-line agent
    if classification isn't available (e.g. AI temporarily down).

    Returns (reply_text, classification_or_none).
    """
    transcript = _transcript_to_text([*history, ("user", message)])
    try:
        classification = route_ticket(transcript)
    except AppError:
        classification = None

    if classification is not None:
        reply = chat_with_department(classification.assigned_team, history, message)
    else:
        reply = chat_with_general_agent(history, message)
    return reply, classification


def get_ticket(client: Client, ticket_id: int) -> dict | None:
    """The flat ticket row only - no messages/activity/requester. Used for
    ownership/scope checks and as the input to the mutation functions below,
    which only ever need the ticket's own columns.
    """
    return _maybe_single(client.table("tickets").select("*").eq("id", ticket_id))


def get_ticket_detail(client: Client, ticket_id: int) -> dict | None:
    """Assembles the full nested shape TicketDetailOut expects - the ticket
    itself, its messages, its activity log, and the requesting user. There's
    no lazy-loaded relationship traversal once queries go through the
    Supabase client, so each piece is fetched explicitly.
    """
    ticket = get_ticket(client, ticket_id)
    if ticket is None:
        return None
    messages = (
        client.table("ticket_messages")
        .select("*")
        .eq("ticket_id", ticket_id)
        .order("created_at")
        .execute()
        .data
    )
    activity = (
        client.table("ticket_activity")
        .select("*")
        .eq("ticket_id", ticket_id)
        .order("created_at")
        .execute()
        .data
    )
    requester = _maybe_single(client.table("users").select("*").eq("id", ticket["user_id"]))
    return {**ticket, "messages": messages, "activity": activity, "user": requester}


def escalate_to_ticket(
    client: Client,
    user: dict,
    history: list[tuple[str, str]],
    user_priority: str | None = None,
) -> dict:
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

    # ticket_number is populated by a Postgres trigger from the row's own
    # id (see alembic/versions - "cascade deletes and ticket number
    # trigger") - there's no app-level flush-then-derive step once queries
    # go through the Supabase client (a plain HTTP request per call, no
    # partial-transaction concept).
    ticket = (
        client.table("tickets")
        .insert(
            {
                "user_id": user["id"],
                "title": title,
                "description": transcript_text,
                "department": UNASSIGNED_DEPARTMENT,
                "priority": user_priority or _DEFAULT_PRIORITY,
                "status": TicketStatus.NEW.value,
            }
        )
        .execute()
        .data[0]
    )
    log_activity(client, ticket["id"], "Ticket Created", detail="Escalated from chat")

    message_rows = [
        {
            "ticket_id": ticket["id"],
            "sender_type": (SenderType.USER if role == "user" else SenderType.AI).value,
            "sender_id": user["id"] if role == "user" else None,
            "message": content,
        }
        for role, content in history
    ]
    if message_rows:
        client.table("ticket_messages").insert(message_rows).execute()

    started_at = time.perf_counter()
    try:
        result = route_ticket(transcript_text)
    except AppError as error:
        log_activity(client, ticket["id"], "AI Categorization Failed", detail=str(error))
        return get_ticket_detail(client, ticket["id"])
    ai_processing_ms = (time.perf_counter() - started_at) * 1000

    activity_detail = (
        f"{result.category} → {result.assigned_team} "
        f"({result.priority} priority, {result.emotion} tone, {result.confidence:.0%} confidence)"
    )
    if user_priority and user_priority != result.priority:
        activity_detail += f" - customer set priority to {user_priority}"

    ticket = (
        client.table("tickets")
        .update(
            {
                "ai_processing_ms": ai_processing_ms,
                "department": result.assigned_team,
                "priority": user_priority or result.priority,
                "ai_priority": result.priority,
                "ai_summary": result.summary,
                "ai_reasoning": result.reasoning,
                "ai_category": result.category,
                "theme": result.theme,
                "ai_emotion": result.emotion,
                "ai_confidence": result.confidence,
                "status": TicketStatus.OPEN.value,
            }
        )
        .eq("id", ticket["id"])
        .execute()
        .data[0]
    )
    log_activity(client, ticket["id"], "AI Categorized", detail=activity_detail)

    # Get the department's persona engaged right away, so the customer
    # opening the ticket right after creating it sees a live conversation
    # instead of just their own message sitting unanswered.
    _department_auto_reply(client, ticket)
    return get_ticket_detail(client, ticket["id"])


# --- Messages ---------------------------------------------------------------


def _department_auto_reply(client: Client, ticket: dict) -> None:
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
    if ticket["department"] == UNASSIGNED_DEPARTMENT:
        return

    messages = (
        client.table("ticket_messages")
        .select("*")
        .eq("ticket_id", ticket["id"])
        .order("created_at")
        .execute()
        .data
    )
    if any(m["sender_type"] == SenderType.ADMIN.value for m in messages):
        return

    history = [
        ("user" if m["sender_type"] == SenderType.USER.value else "assistant", m["message"])
        for m in messages
    ]
    if not history or history[-1][0] != "user":
        return
    *prior_history, (_, latest_message) = history

    try:
        reply = chat_with_department(
            ticket["department"], prior_history, latest_message, current_status=ticket["status"]
        )
    except AppError as error:
        log_activity(client, ticket["id"], "AI Reply Failed", detail=str(error))
        return

    client.table("ticket_messages").insert(
        {
            "ticket_id": ticket["id"],
            "sender_type": SenderType.AI.value,
            "sender_id": None,
            "message": reply,
        }
    ).execute()
    log_activity(client, ticket["id"], "AI Replied", detail=f"{ticket['department']} agent")

    ticket = _maybe_auto_close(client, ticket, prior_history, latest_message)
    if ticket["status"] not in (TicketStatus.RESOLVED.value, TicketStatus.CLOSED.value):
        _maybe_progress_status(client, ticket, prior_history, latest_message)


def _maybe_auto_close(
    client: Client, ticket: dict, prior_history: list[tuple[str, str]], latest_message: str
) -> dict:
    """After the bot replies, checks whether the customer's latest message
    (the one that triggered this reply) just confirmed the issue is
    resolved - if so, the bot closes the loop itself (RESOLVED, then
    immediately CLOSED) instead of waiting on a human admin, the same
    outcome a customer clicking "Accept Solution" produces via
    accept_solution(). Never re-fires on a ticket that's already
    resolved/closed. Returns the ticket row, updated if it was just closed.
    """
    if ticket["status"] in (TicketStatus.RESOLVED.value, TicketStatus.CLOSED.value):
        return ticket
    if not prior_history:
        # This is the ticket's very first message (e.g. the initial
        # auto-reply fired right after creation) - nothing has been
        # discussed yet, so it cannot possibly be a resolution
        # confirmation. Skip the classifier call entirely.
        return ticket

    transcript = _transcript_to_text([*prior_history, ("user", latest_message)])
    result = check_resolution(transcript, latest_message)
    if not result.resolved:
        return ticket

    log_activity(client, ticket["id"], "AI Detected Resolution", detail=result.reasoning)
    ticket = change_status(client, ticket, TicketStatus.RESOLVED)
    ticket = change_status(client, ticket, TicketStatus.CLOSED)
    client.table("ticket_messages").insert(
        {
            "ticket_id": ticket["id"],
            "sender_type": SenderType.AI.value,
            "sender_id": None,
            "message": (
                "This ticket has been marked Resolved and Closed since you confirmed the "
                "issue is fixed. Reply anytime if it comes back."
            ),
        }
    ).execute()
    return ticket


_STATUS_PROGRESSION_VALUES = {
    TicketStatus.OPEN.value,
    TicketStatus.IN_PROGRESS.value,
    TicketStatus.PENDING_CUSTOMER.value,
    TicketStatus.ON_HOLD.value,
}


def _status_label(status: str) -> str:
    return status.replace("_", " ").title()


def _maybe_progress_status(
    client: Client, ticket: dict, prior_history: list[tuple[str, str]], latest_message: str
) -> None:
    """After the bot replies (and the ticket wasn't just auto-closed), checks
    whether the conversation so far indicates the ticket should move to a
    different mid-lifecycle status (OPEN/IN_PROGRESS/PENDING_CUSTOMER/
    ON_HOLD) - the same "let the AI keep the ticket's status honest" idea as
    _maybe_auto_close, just for the stages before resolution. Only ever
    moves between these four statuses; RESOLVED/CLOSED stay
    _maybe_auto_close's job, and a ticket that's NEW (AI categorization
    still pending/failed) or already RESOLVED/CLOSED is left alone.
    """
    if ticket["status"] not in _STATUS_PROGRESSION_VALUES:
        return
    if not prior_history:
        # Same reasoning as _maybe_auto_close - the very first auto-reply
        # has no prior turn to judge progression from.
        return

    transcript = _transcript_to_text([*prior_history, ("user", latest_message)])
    result = check_status_progression(transcript, latest_message, ticket["status"])
    if result.recommended_status in (NO_STATUS_CHANGE, ticket["status"]):
        return

    log_activity(client, ticket["id"], "AI Progressed Status", detail=result.reasoning)
    ticket = change_status(client, ticket, TicketStatus(result.recommended_status))
    client.table("ticket_messages").insert(
        {
            "ticket_id": ticket["id"],
            "sender_type": SenderType.AI.value,
            "sender_id": None,
            "message": (
                f"{result.reasoning} I've updated this ticket to "
                f"**{_status_label(result.recommended_status)}**."
            ),
        }
    ).execute()


def add_user_message(client: Client, ticket: dict, user: dict, text: str) -> dict:
    if ticket["status"] == TicketStatus.CLOSED.value:
        raise ValueError("This ticket is closed. Please open a new ticket.")

    message = (
        client.table("ticket_messages")
        .insert(
            {
                "ticket_id": ticket["id"],
                "sender_type": SenderType.USER.value,
                "sender_id": user["id"],
                "message": text,
            }
        )
        .execute()
        .data[0]
    )
    log_activity(client, ticket["id"], "Customer Replied")

    if ticket["status"] == TicketStatus.RESOLVED.value:
        ticket = (
            client.table("tickets")
            .update({"status": TicketStatus.IN_PROGRESS.value})
            .eq("id", ticket["id"])
            .execute()
            .data[0]
        )
        log_activity(
            client,
            ticket["id"],
            "Status Changed",
            detail="RESOLVED → IN_PROGRESS (customer replied)",
        )

    _department_auto_reply(client, ticket)
    return message


def add_admin_message(client: Client, ticket: dict, admin: dict, text: str) -> dict:
    if ticket["status"] == TicketStatus.CLOSED.value:
        raise ValueError("This ticket is closed and cannot receive new replies.")

    message = (
        client.table("ticket_messages")
        .insert(
            {
                "ticket_id": ticket["id"],
                "sender_type": SenderType.ADMIN.value,
                "sender_id": admin["id"],
                "message": text,
            }
        )
        .execute()
        .data[0]
    )
    log_activity(client, ticket["id"], "Admin Replied", detail=f"{admin['name']}")
    return message


# --- Status / assignment -----------------------------------------------------


def change_status(client: Client, ticket: dict, new_status: TicketStatus) -> dict:
    if ticket["status"] == TicketStatus.CLOSED.value:
        raise ValueError("A closed ticket's status cannot be changed.")

    if new_status.value == ticket["status"]:
        # No-op: re-selecting the ticket's current status and clicking
        # "Update Status" shouldn't log a redundant "X → X" activity entry.
        return ticket

    old_status = ticket["status"]
    updates: dict = {"status": new_status.value}
    # resolved_at/closed_at are only set on this specific transition (not a
    # blanket "stamp on every write" rule like updated_at), so they're set
    # explicitly here in the app rather than via a DB trigger.
    if new_status == TicketStatus.RESOLVED:
        updates["resolved_at"] = _utcnow().isoformat()
    if new_status == TicketStatus.CLOSED:
        updates["closed_at"] = _utcnow().isoformat()

    updated = client.table("tickets").update(updates).eq("id", ticket["id"]).execute().data[0]
    log_activity(
        client, ticket["id"], "Status Changed", detail=f"{old_status} → {new_status.value}"
    )
    return updated


def assign_admin(client: Client, ticket: dict, admin: dict) -> dict:
    updated = (
        client.table("tickets")
        .update({"assigned_admin_id": admin["id"]})
        .eq("id", ticket["id"])
        .execute()
        .data[0]
    )
    log_activity(client, ticket["id"], "Assigned", detail=f"Assigned to {admin['name']}")
    return updated


def reassign(client: Client, ticket: dict, department: str | None, priority: str | None) -> dict:
    changes = []
    updates: dict = {}
    if department and department != ticket["department"]:
        changes.append(f"department {ticket['department']} → {department}")
        updates["department"] = department
    if priority and priority != ticket["priority"]:
        changes.append(f"priority {ticket['priority']} → {priority}")
        updates["priority"] = priority

    if not changes:
        return ticket

    updated = client.table("tickets").update(updates).eq("id", ticket["id"]).execute().data[0]
    log_activity(client, ticket["id"], "Reassigned", detail="; ".join(changes))
    return updated


def update_priority(client: Client, ticket: dict, priority: str) -> dict:
    """Customer-facing priority override. Never touches ai_priority - that
    stays the AI's original immutable suggestion (see Ticket.ai_priority in
    backend/models.py) so PriorityHint can keep showing the divergence even
    after the customer changes priority again.
    """
    if priority == ticket["priority"]:
        return ticket

    updated = (
        client.table("tickets").update({"priority": priority}).eq("id", ticket["id"]).execute().data[0]
    )
    log_activity(
        client, ticket["id"], "Priority Changed", detail=f"{ticket['priority']} → {priority} (by customer)"
    )
    return updated


def accept_solution(client: Client, ticket: dict) -> dict:
    if ticket["status"] != TicketStatus.RESOLVED.value:
        raise ValueError("Only a resolved ticket can be accepted.")

    updated = (
        client.table("tickets")
        .update({"status": TicketStatus.CLOSED.value, "closed_at": _utcnow().isoformat()})
        .eq("id", ticket["id"])
        .execute()
        .data[0]
    )
    log_activity(client, ticket["id"], "Closed", detail="Customer accepted the solution")
    return updated


def delete_ticket(client: Client, ticket: dict) -> None:
    """Permanently removes a ticket and its message/activity history - the
    child foreign keys have ondelete="CASCADE" at the DB level (see
    backend/models.py), so deleting the ticket row is enough; there's no
    ORM session to cascade this the way relationship(cascade=...) used to.
    Irreversible - the router requires a fresh confirmation from the admin
    before calling this.
    """
    client.table("tickets").delete().eq("id", ticket["id"]).execute()


def reopen_ticket(client: Client, ticket: dict) -> dict:
    if ticket["status"] != TicketStatus.RESOLVED.value:
        raise ValueError(
            "Only a resolved ticket can be reopened; closed tickets cannot be reopened."
        )

    updated = (
        client.table("tickets")
        .update({"status": TicketStatus.IN_PROGRESS.value})
        .eq("id", ticket["id"])
        .execute()
        .data[0]
    )
    log_activity(
        client, ticket["id"], "Status Changed", detail="RESOLVED → IN_PROGRESS (customer reopened)"
    )
    return updated


# --- Access control / queries -------------------------------------------------


def admin_can_access(admin: dict, ticket: dict) -> bool:
    """A super-admin (department is None) can access every ticket; a
    department-scoped admin only their own department's tickets.
    """
    return admin["department"] is None or admin["department"] == ticket["department"]


def list_tickets_for_user(client: Client, user: dict) -> list[dict]:
    # Bulk submission can create several tickets within the same wall-clock
    # millisecond, so created_at alone can tie - id.desc() is a stable
    # tiebreaker (autoincrement, so it's also always submission order),
    # otherwise SQL is free to return tied rows in an arbitrary order and
    # the list appears to "shuffle" between requests.
    result = (
        client.table("tickets")
        .select("*")
        .eq("user_id", user["id"])
        .order("created_at", desc=True)
        .order("id", desc=True)
        .execute()
    )
    return result.data


def _end_of_day(date_str: str) -> str:
    # date_str is a plain "YYYY-MM-DD" from an HTML <input type="date">, so
    # a bare .lte(date_to) would exclude that whole day's tickets (anything
    # after 00:00:00 on date_to) - push it to the last instant of the day
    # so "to 2026-01-31" actually includes 2026-01-31.
    return f"{date_str}T23:59:59.999999"


def list_tickets_for_admin(
    client: Client,
    admin: dict,
    *,
    department: str | None = None,
    priority: str | None = None,
    status_filter: TicketStatus | None = None,
    assigned_admin_id: int | None = None,
    search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict]:
    query = client.table("tickets").select("*")
    if admin["department"] is not None:
        query = query.eq("department", admin["department"])
    if department:
        query = query.eq("department", department)
    if priority:
        query = query.eq("priority", priority)
    if status_filter:
        query = query.eq("status", status_filter.value)
    if assigned_admin_id is not None:
        query = query.eq("assigned_admin_id", assigned_admin_id)
    if date_from:
        query = query.gte("created_at", date_from)
    if date_to:
        query = query.lte("created_at", _end_of_day(date_to))
    query = query.order("created_at", desc=True).order("id", desc=True)

    tickets = query.execute().data
    if search:
        needle = search.strip().lower()
        tickets = [
            t
            for t in tickets
            if needle in t["title"].lower()
            or needle in t["description"].lower()
            or needle in t["ticket_number"].lower()
        ]
    return tickets


def _tally(tickets: list[dict], key) -> dict[str, int]:
    counts: dict[str, int] = {}
    for ticket in tickets:
        value = key(ticket)
        if value is None:
            continue
        counts[value] = counts.get(value, 0) + 1
    return counts


def _top_themes(items: list[dict], *, top_n: int = 10) -> list[dict]:
    """Ranks `theme` values by frequency, capped at `top_n` with the
    remainder folded into an "Other" bucket - themes are AI-generated free
    text (see ticket_router.models.TicketRouteResult.theme), so raw values
    are first merged into canonical buckets via
    theme_normalization.group_themes (case/punctuation/whitespace/plural
    variants and known synonyms - e.g. "Billing Error"/"Billing Errors"/
    "Payment Issue" all count toward one "Billing Issues" bucket) before
    ranking, so near-duplicate phrasings don't fragment into separate bars.
    Shared by ticket_service and feedback_service - both tickets and
    feedback rows have a `theme` column with the same shape.
    """
    raw_to_label = group_themes(items)
    counts = _tally(items, lambda i: raw_to_label.get(i["theme"]) if i["theme"] is not None else None)
    ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    top, rest = ranked[:top_n], ranked[top_n:]
    if rest:
        top.append(("Other", sum(n for _, n in rest)))
    return [{"theme": t, "count": n} for t, n in top]


def _theme_trend(
    items: list[dict], top_theme_names: list[str], *, date_key: str = "created_at"
) -> list[dict]:
    """Per-day counts of each of `top_theme_names` (everything else folded
    into "Other"), for the dashboard's theme trend-over-time chart. Each
    item's raw theme is mapped through the same canonical grouping
    _top_themes uses (see theme_normalization.group_themes), so the trend
    lines match the buckets `top_theme_names` was ranked by. Shared by
    ticket_service and feedback_service.
    """
    raw_to_label = group_themes(items)
    top_set = set(top_theme_names)
    by_date: dict[str, dict[str, int]] = {}
    for item in items:
        if item["theme"] is None:
            continue
        label = raw_to_label.get(item["theme"], item["theme"])
        bucket = label if label in top_set else "Other"
        date_str = item[date_key][:10]
        by_date.setdefault(date_str, {}).setdefault(bucket, 0)
        by_date[date_str][bucket] += 1
    return [{"date": d, "counts": c} for d, c in sorted(by_date.items())]


def _metrics_for(tickets: list[dict]) -> dict:
    open_tickets = [t for t in tickets if t["status"] != TicketStatus.CLOSED.value]
    resolution_hours = [
        (_parse_dt(t["resolved_at"]) - _parse_dt(t["created_at"])).total_seconds() / 3600
        for t in tickets
        if t["resolved_at"] is not None
    ]
    ranked_themes = _top_themes(tickets)
    return {
        "open_tickets": len(open_tickets),
        "total_tickets": len(tickets),
        "avg_resolution_hours": (
            sum(resolution_hours) / len(resolution_hours) if resolution_hours else None
        ),
        "tickets_per_status": _tally(tickets, lambda t: t["status"]),
        "tickets_per_priority": _tally(tickets, lambda t: t["priority"]),
        "tickets_per_emotion": _tally(tickets, lambda t: t["ai_emotion"]),
        "tickets_per_category": _tally(tickets, lambda t: t["ai_category"]),
        "top_themes": ranked_themes,
        "theme_trend": _theme_trend(tickets, [t["theme"] for t in ranked_themes]),
    }


def dashboard_metrics(
    client: Client, admin: dict, *, date_from: str | None = None, date_to: str | None = None
) -> dict:
    """Overall metrics for this admin's scope (their one department, or every
    department for a super-admin), optionally restricted to tickets created
    within [date_from, date_to] (inclusive, "YYYY-MM-DD" strings from the
    dashboard's date-range picker - see backend/routers/admin.py). A
    super-admin additionally gets `by_department`: the same metric shape
    computed separately for each department that has at least one ticket, so
    the dashboard can show a dedicated section per team instead of just one
    blended aggregate.
    """
    tickets = list_tickets_for_admin(client, admin, date_from=date_from, date_to=date_to)
    metrics = _metrics_for(tickets)
    metrics["tickets_per_department"] = _tally(tickets, lambda t: t["department"])
    # Echoed back verbatim so the CSV/PDF export can print the range it was
    # generated from without the frontend needing to track it separately -
    # None means "all time" (no filter was applied).
    metrics["date_range"] = {"from": date_from, "to": date_to}

    if admin["department"] is None:
        metrics["by_department"] = {
            department: _metrics_for([t for t in tickets if t["department"] == department])
            for department in metrics["tickets_per_department"]
        }

    return metrics
