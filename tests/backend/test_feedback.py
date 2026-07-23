from backend.models import Role
from backend.routers import chat as chat_router
from backend.services import feedback_service, ticket_service
from ticket_router.models import FeedbackClassification, SubmissionTypeResult, TicketRouteResult


def _register_and_login(client, email="alice@example.com"):
    client.post("/auth/register", json={"name": "Alice", "email": email, "password": "password123"})
    login = client.post("/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _admin_login(client, db_session, email="admin@example.com", department=None, role=Role.ADMIN):
    ticket_service.create_user(
        db_session, name="Admin", email=email, password="adminpass1", role=role, department=department
    )
    login_path = "/product-cx/login" if role == Role.PRODUCT_CX else "/admin/login"
    login = client.post(login_path, json={"email": email, "password": "adminpass1"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _stub_as_feedback(monkeypatch):
    monkeypatch.setattr(
        chat_router,
        "classify_submission_type",
        lambda transcript: SubmissionTypeResult(
            submission_type="CUSTOMER_FEEDBACK", reasoning="test"
        ),
    )
    monkeypatch.setattr(
        feedback_service,
        "classify_feedback",
        lambda text: FeedbackClassification(
            sentiment="Positive",
            category="General Praise",
            assignedTeam="Customer Success",
            theme="Positive Experience",
            summary="Customer likes the product.",
            reasoning="test",
            confidence=0.9,
        ),
    )


def _stub_as_ticket(monkeypatch):
    monkeypatch.setattr(
        chat_router,
        "classify_submission_type",
        lambda transcript: SubmissionTypeResult(submission_type="SUPPORT_ISSUE", reasoning="test"),
    )
    result = TicketRouteResult(
        category="Billing",
        priority="High",
        assignedTeam="Billing Team",
        emotion="Frustrated",
        theme="Billing Error",
        summary="test summary",
        reasoning="test",
        confidence=0.9,
    )
    result.model_used = "fake-model"
    monkeypatch.setattr(ticket_service, "route_ticket", lambda message: result)
    monkeypatch.setattr(
        ticket_service,
        "chat_with_department",
        lambda team, history, message, current_status=None: "Noted.",
    )


def test_feedback_classified_submission_creates_feedback_not_ticket(client, monkeypatch):
    _stub_as_feedback(monkeypatch)
    headers = _register_and_login(client)

    response = client.post(
        "/chat/escalate",
        headers=headers,
        json={"history": [{"role": "user", "content": "The app is very easy to use."}]},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["type"] == "feedback"
    assert body["feedback"]["sentiment"] == "Positive"
    assert body["feedback"]["category"] == "General Praise"
    assert body["feedback"]["team"] == "Customer Success"
    assert body["feedback"]["theme"] == "Positive Experience"

    assert client.get("/tickets", headers=headers).json() == []


def test_bulk_submission_mixes_tickets_and_feedback(client, monkeypatch):
    _stub_as_ticket(monkeypatch)
    headers = _register_and_login(client)

    def fake_classify_submission_type(transcript):
        is_feedback = "easy to use" in transcript
        return SubmissionTypeResult(
            submission_type="CUSTOMER_FEEDBACK" if is_feedback else "SUPPORT_ISSUE",
            reasoning="test",
        )

    monkeypatch.setattr(chat_router, "classify_submission_type", fake_classify_submission_type)
    monkeypatch.setattr(
        feedback_service,
        "classify_feedback",
        lambda text: FeedbackClassification(
            sentiment="Positive",
            category="General Praise",
            assignedTeam="Customer Success",
            theme="Positive Experience",
            summary="test",
            reasoning="test",
            confidence=0.9,
        ),
    )

    response = client.post(
        "/tickets/bulk",
        headers=headers,
        json={"messages": ["Payment keeps failing.", "The app is very easy to use."]},
    )
    assert response.status_code == 201
    results = response.json()
    assert [r["type"] for r in results] == ["ticket", "feedback"]


def test_department_scoped_admin_cannot_access_feedback(client, monkeypatch, db_session):
    _stub_as_feedback(monkeypatch)
    headers = _register_and_login(client)
    client.post(
        "/chat/escalate",
        headers=headers,
        json={"history": [{"role": "user", "content": "The app is very easy to use."}]},
    )

    admin_headers = _admin_login(client, db_session, department="Billing Team")
    response = client.get("/feedback", headers=admin_headers)
    assert response.status_code == 403


def test_super_admin_and_product_cx_can_access_feedback(client, monkeypatch, db_session):
    _stub_as_feedback(monkeypatch)
    headers = _register_and_login(client)
    client.post(
        "/chat/escalate",
        headers=headers,
        json={"history": [{"role": "user", "content": "The app is very easy to use."}]},
    )

    super_admin_headers = _admin_login(client, db_session, email="super@example.com")
    response = client.get("/feedback", headers=super_admin_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1

    product_cx_headers = _admin_login(
        client, db_session, email="cx@example.com", role=Role.PRODUCT_CX
    )
    response = client.get("/feedback", headers=product_cx_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_product_cx_account_cannot_log_in_via_admin_login(client, db_session):
    ticket_service.create_user(
        db_session,
        name="CX",
        email="cx@example.com",
        password="adminpass1",
        role=Role.PRODUCT_CX,
    )
    response = client.post(
        "/admin/login", json={"email": "cx@example.com", "password": "adminpass1"}
    )
    assert response.status_code == 401


def test_super_admin_can_create_product_cx_account(client, db_session):
    super_admin_headers = _admin_login(client, db_session, email="super@example.com")
    response = client.post(
        "/admin/admins",
        headers=super_admin_headers,
        json={
            "name": "CX Lead",
            "email": "cx-lead@example.com",
            "password": "cxpassword1",
            "role": "PRODUCT_CX",
        },
    )
    assert response.status_code == 201
    assert response.json()["role"] == "PRODUCT_CX"

    login = client.post(
        "/product-cx/login", json={"email": "cx-lead@example.com", "password": "cxpassword1"}
    )
    assert login.status_code == 200

    accounts = client.get("/admin/team-accounts", headers=super_admin_headers).json()
    assert any(a["email"] == "cx-lead@example.com" and a["role"] == "PRODUCT_CX" for a in accounts)
