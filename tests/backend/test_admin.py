from backend.models import Role
from backend.services import ticket_service
from ticket_router.models import TicketRouteResult


def _fake_result(category, team, priority="High", confidence=0.9):
    result = TicketRouteResult(
        category=category,
        priority=priority,
        assignedTeam=team,
        reasoning="test",
        confidence=confidence,
    )
    result.model_used = "fake-model"
    return result


def _register_and_login(client, email="alice@example.com"):
    client.post("/auth/register", json={"name": "Alice", "email": email, "password": "password123"})
    login = client.post("/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _admin_login(client, db_session, email="admin@example.com", department=None):
    ticket_service.create_user(
        db_session,
        name="Admin",
        email=email,
        password="adminpass1",
        role=Role.ADMIN,
        department=department,
    )
    login = client.post("/admin/login", json={"email": email, "password": "adminpass1"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _escalate_as(client, monkeypatch, result, email):
    from backend.services import ticket_service as ts

    monkeypatch.setattr(ts, "route_ticket", lambda message: result)
    headers = _register_and_login(client, email=email)
    return client.post(
        "/chat/escalate",
        headers=headers,
        json={"history": [{"role": "user", "content": "help me"}]},
    ).json()


def test_department_scoped_admin_only_sees_own_department(client, monkeypatch, db_session):
    _escalate_as(
        client, monkeypatch, _fake_result("Billing", "Billing Team"), "billing-user@example.com"
    )
    _escalate_as(
        client, monkeypatch, _fake_result("Bug Report", "Engineering"), "eng-user@example.com"
    )

    billing_admin = _admin_login(
        client, db_session, email="billing-admin@example.com", department="Billing Team"
    )
    response = client.get("/admin/tickets", headers=billing_admin)
    tickets = response.json()
    assert len(tickets) == 1
    assert tickets[0]["department"] == "Billing Team"


def test_super_admin_sees_every_department(client, monkeypatch, db_session):
    _escalate_as(
        client, monkeypatch, _fake_result("Billing", "Billing Team"), "billing-user@example.com"
    )
    _escalate_as(
        client, monkeypatch, _fake_result("Bug Report", "Engineering"), "eng-user@example.com"
    )

    super_admin = _admin_login(client, db_session, email="super@example.com", department=None)
    response = client.get("/admin/tickets", headers=super_admin)
    assert len(response.json()) == 2


def test_department_scoped_admin_cannot_access_other_departments_ticket(
    client, monkeypatch, db_session
):
    ticket = _escalate_as(
        client, monkeypatch, _fake_result("Bug Report", "Engineering"), "eng-user@example.com"
    )

    billing_admin = _admin_login(
        client, db_session, email="billing-admin@example.com", department="Billing Team"
    )
    response = client.get(f"/admin/tickets/{ticket['id']}", headers=billing_admin)
    assert response.status_code == 404


def test_admin_can_change_status_and_reply(client, monkeypatch, db_session):
    ticket = _escalate_as(
        client, monkeypatch, _fake_result("Billing", "Billing Team"), "user@example.com"
    )
    admin = _admin_login(client, db_session, department="Billing Team")

    status_response = client.patch(
        f"/admin/tickets/{ticket['id']}/status", headers=admin, json={"status": "IN_PROGRESS"}
    )
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "IN_PROGRESS"

    reply_response = client.post(
        f"/admin/tickets/{ticket['id']}/message",
        headers=admin,
        json={"message": "Looking into it."},
    )
    assert reply_response.status_code == 201


def test_admin_cannot_change_status_of_closed_ticket(client, monkeypatch, db_session):
    ticket = _escalate_as(
        client, monkeypatch, _fake_result("Billing", "Billing Team"), "user@example.com"
    )
    admin = _admin_login(client, db_session, department="Billing Team")

    client.patch(
        f"/admin/tickets/{ticket['id']}/status", headers=admin, json={"status": "RESOLVED"}
    )
    client.patch(f"/admin/tickets/{ticket['id']}/status", headers=admin, json={"status": "CLOSED"})

    response = client.patch(
        f"/admin/tickets/{ticket['id']}/status", headers=admin, json={"status": "IN_PROGRESS"}
    )
    assert response.status_code == 409


def test_admin_assign_rejects_admin_from_a_different_department(client, monkeypatch, db_session):
    ticket = _escalate_as(
        client, monkeypatch, _fake_result("Billing", "Billing Team"), "user@example.com"
    )
    billing_admin = _admin_login(
        client, db_session, email="billing-admin@example.com", department="Billing Team"
    )
    eng_admin_user = ticket_service.create_user(
        db_session,
        name="Eng Admin",
        email="eng-admin@example.com",
        password="adminpass1",
        role=Role.ADMIN,
        department="Engineering",
    )

    response = client.patch(
        f"/admin/tickets/{ticket['id']}/assign",
        headers=billing_admin,
        json={"admin_id": eng_admin_user.id},
    )
    assert response.status_code == 400


def test_metrics_counts_open_tickets_and_per_department(client, monkeypatch, db_session):
    _escalate_as(client, monkeypatch, _fake_result("Billing", "Billing Team"), "user1@example.com")
    _escalate_as(client, monkeypatch, _fake_result("Billing", "Billing Team"), "user2@example.com")

    admin = _admin_login(client, db_session, department="Billing Team")
    response = client.get("/admin/metrics", headers=admin)
    body = response.json()
    assert body["open_tickets"] == 2
    assert body["tickets_per_department"] == {"Billing Team": 2}
