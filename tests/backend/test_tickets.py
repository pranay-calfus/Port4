from backend.services import ticket_service
from ticket_router.errors import AIUnavailableError
from ticket_router.models import TicketRouteResult


def _fake_route_ticket_success(monkeypatch):
    result = TicketRouteResult(
        category="Billing",
        priority="High",
        assignedTeam="Billing Team",
        reasoning="Customer reports a duplicate charge on their invoice.",
        confidence=0.95,
    )
    result.model_used = "fake-model"
    monkeypatch.setattr(ticket_service, "route_ticket", lambda message: result)


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
    assert ticket["ticket_number"] == "TKT-00001"
    assert ticket["status"] == "OPEN"
    assert ticket["department"] == "Billing Team"
    assert ticket["priority"] == "High"
    assert ticket["ai_category"] == "Billing"
    assert [a["event_type"] for a in ticket["activity"]] == ["Ticket Created", "AI Categorized"]
    assert len(ticket["messages"]) == 1


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


def test_user_cannot_see_another_users_ticket(client, monkeypatch):
    _fake_route_ticket_success(monkeypatch)
    alice_headers = _register_and_login(client, email="alice@example.com")
    _escalate(client, alice_headers)

    bob_headers = _register_and_login(client, email="bob@example.com")
    response = client.get("/tickets/1", headers=bob_headers)
    assert response.status_code == 404


def test_reply_to_resolved_ticket_reopens_to_in_progress(client, monkeypatch, db_session):
    _fake_route_ticket_success(monkeypatch)
    headers = _register_and_login(client)
    _escalate(client, headers)

    from backend.models import Ticket, TicketStatus

    ticket = db_session.get(Ticket, 1)
    ticket_service.change_status(db_session, ticket, TicketStatus.RESOLVED)

    response = client.post(
        "/tickets/1/messages", headers=headers, json={"message": "This didn't fix it."}
    )
    assert response.status_code == 201

    ticket_response = client.get("/tickets/1", headers=headers)
    assert ticket_response.json()["status"] == "IN_PROGRESS"


def test_accept_solution_requires_resolved_status(client, monkeypatch):
    _fake_route_ticket_success(monkeypatch)
    headers = _register_and_login(client)
    _escalate(client, headers)

    response = client.post("/tickets/1/accept-solution", headers=headers)
    assert response.status_code == 409


def test_reply_to_closed_ticket_is_rejected(client, monkeypatch, db_session):
    _fake_route_ticket_success(monkeypatch)
    headers = _register_and_login(client)
    _escalate(client, headers)

    from backend.models import Ticket, TicketStatus

    ticket = db_session.get(Ticket, 1)
    ticket_service.change_status(db_session, ticket, TicketStatus.RESOLVED)
    ticket_service.accept_solution(db_session, ticket)
    assert ticket.status == TicketStatus.CLOSED

    response = client.post(
        "/tickets/1/messages", headers=headers, json={"message": "One more thing..."}
    )
    assert response.status_code == 409

    reopen_response = client.post("/tickets/1/reopen", headers=headers)
    assert reopen_response.status_code == 409
