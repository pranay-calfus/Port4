from ticket_router.errors import AIUnavailableError


def _register_and_login(client, email="alice@example.com"):
    client.post("/auth/register", json={"name": "Alice", "email": email, "password": "password123"})
    login = client.post("/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_chat_message_requires_login(client):
    response = client.post("/chat/message", json={"message": "hi", "history": []})
    assert response.status_code == 401


def test_chat_message_returns_reply_and_updated_history(client, monkeypatch):
    from backend.routers import chat as chat_router

    monkeypatch.setattr(
        chat_router,
        "chat_with_general_agent",
        lambda history, message: "Have you tried restarting?",
    )
    headers = _register_and_login(client)

    response = client.post(
        "/chat/message", headers=headers, json={"message": "It's broken", "history": []}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "Have you tried restarting?"
    assert body["history"] == [
        {"role": "user", "content": "It's broken"},
        {"role": "assistant", "content": "Have you tried restarting?"},
    ]


def test_chat_message_returns_503_when_ai_unavailable(client, monkeypatch):
    from backend.routers import chat as chat_router

    def _raise(history, message):
        raise AIUnavailableError("AI service is currently unavailable.")

    monkeypatch.setattr(chat_router, "chat_with_general_agent", _raise)
    headers = _register_and_login(client)

    response = client.post(
        "/chat/message", headers=headers, json={"message": "It's broken", "history": []}
    )
    assert response.status_code == 503
