import re

from backend.services import ticket_service
from ticket_router.errors import AIUnavailableError
from ticket_router.models import ResolutionCheck, TicketRouteResult

TICKET_NUMBER_RE = re.compile(r"^TKT-(\d{5})$")


def _ticket_number_seq(ticket_number: str) -> int:
    match = TICKET_NUMBER_RE.match(ticket_number)
    assert match, f"unexpected ticket_number format: {ticket_number!r}"
    return int(match.group(1))


def _stub_resolution(monkeypatch, resolved, reasoning="test"):
    monkeypatch.setattr(
        ticket_service,
        "check_resolution",
        lambda transcript, latest_customer_message: ResolutionCheck(
            resolved=resolved, reasoning=reasoning
        ),
    )


def _fake_route_ticket_success(monkeypatch):
    result = TicketRouteResult(
        category="Billing",
        priority="High",
        assignedTeam="Billing Team",
        emotion="Frustrated",
        reasoning="Customer reports a duplicate charge on their invoice.",
        confidence=0.95,
    )
    result.model_used = "fake-model"
    monkeypatch.setattr(ticket_service, "route_ticket", lambda message: result)
    # escalate_to_ticket() now triggers the department's initial auto-reply
    # right away, so any successful escalation reaches chat_with_department -
    # default it to a canned reply so tests stay fast/deterministic unless a
    # test overrides it below with its own monkeypatch.
    monkeypatch.setattr(
        ticket_service, "chat_with_department", lambda team, history, message: "Noted."
    )


def _fake_route_ticket_failure(monkeypatch):
    def _raise(message):
        raise AIUnavailableError("AI service is currently unavailable.")

    monkeypatch.setattr(ticket_service, "route_ticket", _raise)


def _register_and_login(client, email="alice@example.com"):
    client.post("/auth/register", json={"name": "Alice", "email": email, "password": "password123"})
    login = client.post("/auth/login", json={"email": email, "password": "password123"})
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _escalate(client, headers, message="My invoice was charged twice this month."):
    return client.post(
        "/chat/escalate", headers=headers, json={"history": [{"role": "user", "content": message}]}
    )


def test_escalate_creates_ticket_with_ai_categorization(client, monkeypatch):
    _fake_route_ticket_success(monkeypatch)
    headers = _register_and_login(client)

    response = _escalate(client, headers)
    assert response.status_code == 201
    ticket = response.json()
    assert TICKET_NUMBER_RE.match(ticket["ticket_number"])
    assert ticket["status"] == "OPEN"
    assert ticket["department"] == "Billing Team"
    assert ticket["priority"] == "High"
    assert ticket["ai_category"] == "Billing"
    assert ticket["ai_emotion"] == "Frustrated"
    assert ticket["ai_processing_ms"] is not None and ticket["ai_processing_ms"] >= 0
    assert [a["event_type"] for a in ticket["activity"]] == [
        "Ticket Created",
        "AI Categorized",
        "AI Replied",
    ]
    assert len(ticket["messages"]) == 2  # escalation transcript + the bot's initial reply
    assert ticket["messages"][-1]["sender_type"] == "AI"
    assert ticket["messages"][-1]["message"] == "Noted."


def test_escalate_still_creates_ticket_when_ai_fails(client, monkeypatch):
    _fake_route_ticket_failure(monkeypatch)
    headers = _register_and_login(client)

    response = _escalate(client, headers)
    assert response.status_code == 201
    ticket = response.json()
    assert ticket["status"] == "NEW"
    assert ticket["department"] == "Unassigned"
    assert ticket["ai_category"] is None
    assert [a["event_type"] for a in ticket["activity"]] == [
        "Ticket Created",
        "AI Categorization Failed",
    ]


def test_escalate_with_explicit_priority_overrides_ai_suggestion(client, monkeypatch):
    _fake_route_ticket_success(monkeypatch)  # AI suggests "High"
    headers = _register_and_login(client)

    response = client.post(
        "/chat/escalate",
        headers=headers,
        json={
            "history": [{"role": "user", "content": "My invoice was charged twice."}],
            "priority": "Low",
        },
    )
    assert response.status_code == 201
    ticket = response.json()
    assert ticket["priority"] == "Low"
    assert ticket["ai_priority"] == "High"


def test_escalate_without_explicit_priority_uses_ai_suggestion(client, monkeypatch):
    _fake_route_ticket_success(monkeypatch)
    headers = _register_and_login(client)

    response = _escalate(client, headers)
    ticket = response.json()
    assert ticket["priority"] == "High"
    assert ticket["ai_priority"] == "High"


def test_escalate_rejects_conversation_with_no_user_turns(client, monkeypatch):
    _fake_route_ticket_success(monkeypatch)
    headers = _register_and_login(client)

    response = client.post(
        "/chat/escalate",
        headers=headers,
        json={"history": [{"role": "assistant", "content": "Hi!"}]},
    )
    assert response.status_code == 422


def test_bulk_create_tickets_creates_one_ticket_per_message(client, monkeypatch):
    _fake_route_ticket_success(monkeypatch)
    headers = _register_and_login(client)

    response = client.post(
        "/tickets/bulk",
        headers=headers,
        json={"messages": ["First issue.", "Second issue.", ""]},
    )
    assert response.status_code == 201
    tickets = response.json()
    assert len(tickets) == 2  # the blank entry is dropped
    first_seq = _ticket_number_seq(tickets[0]["ticket_number"])
    second_seq = _ticket_number_seq(tickets[1]["ticket_number"])
    assert second_seq == first_seq + 1
    assert all(t["ai_category"] == "Billing" for t in tickets)


def test_bulk_create_tickets_rejects_all_blank_messages(client):
    headers = _register_and_login(client)

    response = client.post("/tickets/bulk", headers=headers, json={"messages": ["  ", ""]})
    assert response.status_code == 422


def test_user_cannot_see_another_users_ticket(client, monkeypatch):
    _fake_route_ticket_success(monkeypatch)
    alice_headers = _register_and_login(client, email="alice@example.com")
    ticket_id = _escalate(client, alice_headers).json()["id"]

    bob_headers = _register_and_login(client, email="bob@example.com")
    response = client.get(f"/tickets/{ticket_id}", headers=bob_headers)
    assert response.status_code == 404


def test_reply_to_resolved_ticket_reopens_to_in_progress(client, monkeypatch, db_session):
    _fake_route_ticket_success(monkeypatch)
    monkeypatch.setattr(
        ticket_service, "chat_with_department", lambda team, history, message: "Noted."
    )
    _stub_resolution(monkeypatch, resolved=False)
    headers = _register_and_login(client)
    ticket_id = _escalate(client, headers).json()["id"]

    from backend.models import TicketStatus

    ticket = ticket_service.get_ticket(db_session, ticket_id)
    ticket_service.change_status(db_session, ticket, TicketStatus.RESOLVED)

    response = client.post(
        f"/tickets/{ticket_id}/messages", headers=headers, json={"message": "This didn't fix it."}
    )
    assert response.status_code == 201

    ticket_response = client.get(f"/tickets/{ticket_id}", headers=headers)
    assert ticket_response.json()["status"] == "IN_PROGRESS"


def test_customer_reply_gets_department_agent_auto_reply(client, monkeypatch):
    _fake_route_ticket_success(monkeypatch)  # assigns "Billing Team"
    monkeypatch.setattr(
        ticket_service,
        "chat_with_department",
        lambda team, history, message: f"[{team} agent] Thanks, looking into: {message}",
    )
    _stub_resolution(monkeypatch, resolved=False)
    headers = _register_and_login(client)
    ticket_id = _escalate(client, headers).json()["id"]

    response = client.post(
        f"/tickets/{ticket_id}/messages", headers=headers, json={"message": "Any update?"}
    )
    assert response.status_code == 201

    detail = client.get(f"/tickets/{ticket_id}", headers=headers).json()
    messages = detail["messages"]
    assert messages[-1]["sender_type"] == "AI"
    assert messages[-1]["message"] == "[Billing Team agent] Thanks, looking into: Any update?"
    assert "AI Replied" in [a["event_type"] for a in detail["activity"]]


def test_bot_auto_closes_ticket_when_customer_confirms_resolution(client, monkeypatch):
    _fake_route_ticket_success(monkeypatch)  # assigns "Billing Team"
    monkeypatch.setattr(
        ticket_service,
        "chat_with_department",
        lambda team, history, message: "Glad to hear it!",
    )
    _stub_resolution(monkeypatch, resolved=True, reasoning="Customer said 'that fixed it, thanks!'")
    headers = _register_and_login(client)
    ticket_id = _escalate(client, headers).json()["id"]

    response = client.post(
        f"/tickets/{ticket_id}/messages",
        headers=headers,
        json={"message": "That fixed it, thanks!"},
    )
    assert response.status_code == 201

    detail = client.get(f"/tickets/{ticket_id}", headers=headers).json()
    assert detail["status"] == "CLOSED"
    event_types = [a["event_type"] for a in detail["activity"]]
    assert "AI Detected Resolution" in event_types
    # OPEN -> RESOLVED and RESOLVED -> CLOSED, each its own "Status Changed" entry
    assert event_types.count("Status Changed") == 2
    messages = detail["messages"]
    assert messages[-2]["message"] == "Glad to hear it!"
    assert messages[-1]["sender_type"] == "AI"
    assert "resolved" in messages[-1]["message"].lower()
    assert "closed" in messages[-1]["message"].lower()


def test_bot_does_not_auto_close_when_customer_has_not_confirmed_resolution(client, monkeypatch):
    _fake_route_ticket_success(monkeypatch)
    monkeypatch.setattr(
        ticket_service, "chat_with_department", lambda team, history, message: "Still looking."
    )
    _stub_resolution(monkeypatch, resolved=False, reasoning="No confirmation in the message")
    headers = _register_and_login(client)
    ticket_id = _escalate(client, headers).json()["id"]

    client.post(f"/tickets/{ticket_id}/messages", headers=headers, json={"message": "Any update?"})

    detail = client.get(f"/tickets/{ticket_id}", headers=headers).json()
    assert detail["status"] == "OPEN"
    assert "AI Detected Resolution" not in [a["event_type"] for a in detail["activity"]]


def test_department_agent_stops_replying_once_admin_takes_over(client, monkeypatch, db_session):
    _fake_route_ticket_success(monkeypatch)
    calls = []
    monkeypatch.setattr(
        ticket_service,
        "chat_with_department",
        lambda team, history, message: calls.append(message) or "auto-reply",
    )
    headers = _register_and_login(client)
    ticket_id = _escalate(client, headers).json()[
        "id"
    ]  # triggers the ticket's own initial auto-reply

    from backend.models import Role

    ticket = ticket_service.get_ticket(db_session, ticket_id)
    admin = ticket_service.create_user(
        db_session, name="Ops", email="ops@example.com", password="adminpass1", role=Role.ADMIN
    )
    ticket_service.add_admin_message(db_session, ticket, admin, "A human is now on this.")

    calls_before_admin_reply = len(calls)
    client.post(f"/tickets/{ticket_id}/messages", headers=headers, json={"message": "Hello again?"})
    assert len(calls) == calls_before_admin_reply  # no new call after an admin reply


def test_unassigned_department_never_gets_an_agent_reply(client, monkeypatch):
    _fake_route_ticket_failure(monkeypatch)  # department stays "Unassigned"
    called = []
    monkeypatch.setattr(
        ticket_service,
        "chat_with_department",
        lambda team, history, message: called.append(1) or "should not be called",
    )
    headers = _register_and_login(client)
    ticket_id = _escalate(client, headers).json()["id"]

    client.post(f"/tickets/{ticket_id}/messages", headers=headers, json={"message": "Hello?"})
    assert called == []


def test_repeated_same_status_update_does_not_add_activity_entry(client, monkeypatch, db_session):
    _fake_route_ticket_success(monkeypatch)
    headers = _register_and_login(client)
    ticket_id = _escalate(client, headers).json()["id"]

    from backend.models import TicketStatus

    ticket = ticket_service.get_ticket(db_session, ticket_id)
    ticket = ticket_service.change_status(db_session, ticket, TicketStatus.PENDING_CUSTOMER)
    activity_count_before = len(ticket_service.get_ticket_detail(db_session, ticket_id)["activity"])

    ticket_service.change_status(db_session, ticket, TicketStatus.PENDING_CUSTOMER)
    activity_count_after = len(ticket_service.get_ticket_detail(db_session, ticket_id)["activity"])
    assert activity_count_after == activity_count_before


def test_accept_solution_requires_resolved_status(client, monkeypatch):
    _fake_route_ticket_success(monkeypatch)
    headers = _register_and_login(client)
    ticket_id = _escalate(client, headers).json()["id"]

    response = client.post(f"/tickets/{ticket_id}/accept-solution", headers=headers)
    assert response.status_code == 409


def test_reply_to_closed_ticket_is_rejected(client, monkeypatch, db_session):
    _fake_route_ticket_success(monkeypatch)
    headers = _register_and_login(client)
    ticket_id = _escalate(client, headers).json()["id"]

    from backend.models import TicketStatus

    ticket = ticket_service.get_ticket(db_session, ticket_id)
    ticket = ticket_service.change_status(db_session, ticket, TicketStatus.RESOLVED)
    ticket = ticket_service.accept_solution(db_session, ticket)
    assert ticket["status"] == TicketStatus.CLOSED.value

    response = client.post(
        f"/tickets/{ticket_id}/messages", headers=headers, json={"message": "One more thing..."}
    )
    assert response.status_code == 409

    reopen_response = client.post(f"/tickets/{ticket_id}/reopen", headers=headers)
    assert reopen_response.status_code == 409
