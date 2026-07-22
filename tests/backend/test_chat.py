from backend.services import ticket_service
from ticket_router.errors import AIUnavailableError
from ticket_router.models import TicketRouteResult


def _register_and_login(client, email="alice@example.com"):
    client.post("/auth/register", json={"name": "Alice", "email": email, "password": "password123"})
    login = client.post("/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _fake_classification(team="Billing Team"):
    result = TicketRouteResult(
        category="Billing",
        priority="High",
        assignedTeam=team,
        emotion="Frustrated",
        theme="Billing Error",
        reasoning="test",
        confidence=0.9,
    )
    result.model_used = "fake-model"
    return result


def test_chat_message_requires_login(client):
    response = client.post("/chat/message", json={"message": "hi", "history": []})
    assert response.status_code == 401


def test_chat_message_uses_department_persona_once_classified(client, monkeypatch):
    monkeypatch.setattr(
        ticket_service, "route_ticket", lambda text: _fake_classification("Billing Team")
    )

    calls = []

    def _fake_department_chat(team, history, message):
        calls.append(team)
        return f"[{team}] Let me help with that."

    monkeypatch.setattr(ticket_service, "chat_with_department", _fake_department_chat)

    def _general_agent_should_not_be_called(history, message):
        raise AssertionError("the general agent should not be called once classified")

    monkeypatch.setattr(
        ticket_service, "chat_with_general_agent", _general_agent_should_not_be_called
    )
    headers = _register_and_login(client)

    response = client.post(
        "/chat/message",
        headers=headers,
        json={"message": "I was charged twice this month.", "history": []},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "[Billing Team] Let me help with that."
    assert calls == ["Billing Team"]
    assert body["history"] == [
        {"role": "user", "content": "I was charged twice this month."},
        {"role": "assistant", "content": "[Billing Team] Let me help with that."},
    ]


def test_chat_message_falls_back_to_general_agent_when_classification_fails(client, monkeypatch):
    def _raise(text):
        raise AIUnavailableError("AI service is currently unavailable.")

    monkeypatch.setattr(ticket_service, "route_ticket", _raise)
    monkeypatch.setattr(
        ticket_service,
        "chat_with_general_agent",
        lambda history, message: "Have you tried restarting?",
    )
    headers = _register_and_login(client)

    response = client.post(
        "/chat/message", headers=headers, json={"message": "It's broken", "history": []}
    )
    assert response.status_code == 200
    assert response.json()["reply"] == "Have you tried restarting?"


def test_chat_message_returns_503_when_department_agent_unavailable(client, monkeypatch):
    monkeypatch.setattr(ticket_service, "route_ticket", lambda text: _fake_classification())

    def _raise(team, history, message):
        raise AIUnavailableError("AI service is currently unavailable.")

    monkeypatch.setattr(ticket_service, "chat_with_department", _raise)
    headers = _register_and_login(client)

    response = client.post(
        "/chat/message", headers=headers, json={"message": "It's broken", "history": []}
    )
    assert response.status_code == 503
