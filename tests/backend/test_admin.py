from backend.models import Role
from backend.services import ticket_service
from ticket_router.models import TicketRouteResult


def _fake_result(category, team, priority="High", confidence=0.9):
    result = TicketRouteResult(
        category=category,
        priority=priority,
        assignedTeam=team,
        emotion="Neutral",
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
    monkeypatch.setattr(
        ts, "chat_with_department", lambda team, history, message, current_status=None: "Noted."
    )
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


def test_setting_status_to_its_current_value_does_not_log_a_new_activity_entry(
    client, monkeypatch, db_session
):
    ticket = _escalate_as(
        client, monkeypatch, _fake_result("Billing", "Billing Team"), "user@example.com"
    )
    admin = _admin_login(client, db_session, department="Billing Team")

    client.patch(
        f"/admin/tickets/{ticket['id']}/status",
        headers=admin,
        json={"status": "PENDING_CUSTOMER"},
    )
    activity_count_before = len(
        client.get(f"/admin/tickets/{ticket['id']}", headers=admin).json()["activity"]
    )

    client.patch(
        f"/admin/tickets/{ticket['id']}/status",
        headers=admin,
        json={"status": "PENDING_CUSTOMER"},
    )
    activity_after = client.get(f"/admin/tickets/{ticket['id']}", headers=admin).json()["activity"]
    assert len(activity_after) == activity_count_before


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
        json={"admin_id": eng_admin_user["id"]},
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
    assert body["tickets_per_status"] == {"OPEN": 2}
    assert body["tickets_per_priority"] == {"High": 2}
    assert body["tickets_per_emotion"] == {"Neutral": 2}
    assert "avg_first_response_hours" not in body
    assert "by_department" not in body  # only super-admins get the per-team breakdown
    assert body["date_range"] == {"from": None, "to": None}


def test_metrics_includes_category_breakdown(client, monkeypatch, db_session):
    _escalate_as(client, monkeypatch, _fake_result("Billing", "Billing Team"), "user1@example.com")
    _escalate_as(
        client, monkeypatch, _fake_result("Bug Report", "Engineering"), "user2@example.com"
    )

    admin = _admin_login(client, db_session, department=None)
    response = client.get("/admin/metrics", headers=admin)
    body = response.json()
    assert body["tickets_per_category"] == {"Billing": 1, "Bug Report": 1}


def test_metrics_date_range_excludes_tickets_outside_range(client, monkeypatch, db_session):
    from datetime import UTC, datetime, timedelta

    old_ticket = _escalate_as(
        client, monkeypatch, _fake_result("Billing", "Billing Team"), "user1@example.com"
    )
    a_year_ago = (datetime.now(UTC) - timedelta(days=365)).isoformat()
    db_session.table("tickets").update({"created_at": a_year_ago}).eq(
        "id", old_ticket["id"]
    ).execute()
    _escalate_as(client, monkeypatch, _fake_result("Billing", "Billing Team"), "user2@example.com")

    today = datetime.now(UTC).date().isoformat()
    admin = _admin_login(client, db_session, department="Billing Team")
    response = client.get("/admin/metrics", headers=admin, params={"date_from": today})
    body = response.json()
    assert body["total_tickets"] == 1
    assert body["date_range"] == {"from": today, "to": None}


def test_admin_ticket_list_respects_date_range(client, monkeypatch, db_session):
    from datetime import UTC, datetime, timedelta

    old_ticket = _escalate_as(
        client, monkeypatch, _fake_result("Billing", "Billing Team"), "user1@example.com"
    )
    a_year_ago = (datetime.now(UTC) - timedelta(days=365)).isoformat()
    db_session.table("tickets").update({"created_at": a_year_ago}).eq(
        "id", old_ticket["id"]
    ).execute()
    new_ticket = _escalate_as(
        client, monkeypatch, _fake_result("Billing", "Billing Team"), "user2@example.com"
    )

    today = datetime.now(UTC).date().isoformat()
    admin = _admin_login(client, db_session, department="Billing Team")
    response = client.get("/admin/tickets", headers=admin, params={"date_from": today})
    tickets = response.json()
    assert [t["id"] for t in tickets] == [new_ticket["id"]]


def test_admin_still_sees_status_and_full_timeline_after_ticket_is_closed(
    client, monkeypatch, db_session
):
    ticket = _escalate_as(
        client, monkeypatch, _fake_result("Billing", "Billing Team"), "user@example.com"
    )
    admin = _admin_login(client, db_session, department="Billing Team")

    from backend.models import TicketStatus

    db_ticket = ticket_service.get_ticket(db_session, ticket["id"])
    db_ticket = ticket_service.change_status(db_session, db_ticket, TicketStatus.RESOLVED)
    ticket_service.change_status(db_session, db_ticket, TicketStatus.CLOSED)

    queue_response = client.get("/admin/tickets", headers=admin)
    queue_tickets = queue_response.json()
    assert len(queue_tickets) == 1
    assert queue_tickets[0]["status"] == "CLOSED"

    detail_response = client.get(f"/admin/tickets/{ticket['id']}", headers=admin)
    detail = detail_response.json()
    assert detail["status"] == "CLOSED"
    assert [a["event_type"] for a in detail["activity"]] == [
        "Ticket Created",
        "AI Categorized",
        "AI Replied",
        "Status Changed",
        "Status Changed",
    ]
    assert len(detail["messages"]) == 2  # escalation transcript + the bot's initial reply


def test_admin_can_delete_ticket(client, monkeypatch, db_session):
    ticket = _escalate_as(
        client, monkeypatch, _fake_result("Billing", "Billing Team"), "user@example.com"
    )
    admin = _admin_login(client, db_session, department="Billing Team")

    response = client.delete(f"/admin/tickets/{ticket['id']}", headers=admin)
    assert response.status_code == 204

    assert client.get(f"/admin/tickets/{ticket['id']}", headers=admin).status_code == 404
    assert client.get("/admin/tickets", headers=admin).json() == []


def test_department_scoped_admin_cannot_delete_other_departments_ticket(
    client, monkeypatch, db_session
):
    ticket = _escalate_as(
        client, monkeypatch, _fake_result("Bug Report", "Engineering"), "eng-user@example.com"
    )
    billing_admin = _admin_login(
        client, db_session, email="billing-admin@example.com", department="Billing Team"
    )

    response = client.delete(f"/admin/tickets/{ticket['id']}", headers=billing_admin)
    assert response.status_code == 404


def test_super_admin_metrics_include_per_department_breakdown(client, monkeypatch, db_session):
    _escalate_as(client, monkeypatch, _fake_result("Billing", "Billing Team"), "user1@example.com")
    _escalate_as(
        client, monkeypatch, _fake_result("Bug Report", "Engineering"), "user2@example.com"
    )
    _escalate_as(
        client, monkeypatch, _fake_result("Bug Report", "Engineering"), "user3@example.com"
    )

    admin = _admin_login(client, db_session, department=None)
    response = client.get("/admin/metrics", headers=admin)
    body = response.json()
    assert body["total_tickets"] == 3
    assert set(body["by_department"].keys()) == {"Billing Team", "Engineering"}
    assert body["by_department"]["Billing Team"]["total_tickets"] == 1
    assert body["by_department"]["Engineering"]["total_tickets"] == 2


def test_super_admin_can_create_team_account(client, db_session):
    super_admin = _admin_login(client, db_session, email="super@example.com", department=None)

    response = client.post(
        "/admin/admins",
        headers=super_admin,
        json={
            "name": "New Admin",
            "email": "new-admin@example.com",
            "password": "adminpass1",
            "department": "Billing Team",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "new-admin@example.com"
    assert body["role"] == "ADMIN"
    assert body["department"] == "Billing Team"

    login = client.post(
        "/admin/login", json={"email": "new-admin@example.com", "password": "adminpass1"}
    )
    assert login.status_code == 200


def test_super_admin_can_create_another_super_admin(client, db_session):
    super_admin = _admin_login(client, db_session, email="super@example.com", department=None)

    response = client.post(
        "/admin/admins",
        headers=super_admin,
        json={"name": "Second Super", "email": "super2@example.com", "password": "adminpass1"},
    )
    assert response.status_code == 201
    assert response.json()["department"] is None


def test_scoped_admin_cannot_create_team_account(client, db_session):
    scoped_admin = _admin_login(
        client, db_session, email="billing-admin@example.com", department="Billing Team"
    )

    response = client.post(
        "/admin/admins",
        headers=scoped_admin,
        json={"name": "New Admin", "email": "new-admin@example.com", "password": "adminpass1"},
    )
    assert response.status_code == 403


def test_creating_team_account_with_duplicate_email_conflicts(client, db_session):
    super_admin = _admin_login(client, db_session, email="super@example.com", department=None)

    response = client.post(
        "/admin/admins",
        headers=super_admin,
        json={"name": "Dupe", "email": "super@example.com", "password": "adminpass1"},
    )
    assert response.status_code == 409


def test_super_admin_can_delete_team_account(client, db_session):
    super_admin = _admin_login(client, db_session, email="super@example.com", department=None)
    target = ticket_service.create_user(
        db_session,
        name="Billing Admin",
        email="billing-admin@example.com",
        password="adminpass1",
        role=Role.ADMIN,
        department="Billing Team",
    )

    response = client.delete(f"/admin/admins/{target['id']}", headers=super_admin)
    assert response.status_code == 204

    remaining = client.get("/admin/admins", headers=super_admin).json()
    assert target["id"] not in [a["id"] for a in remaining]


def test_deleting_admin_unassigns_their_tickets(client, monkeypatch, db_session):
    ticket = _escalate_as(
        client, monkeypatch, _fake_result("Billing", "Billing Team"), "user@example.com"
    )
    super_admin = _admin_login(client, db_session, email="super@example.com", department=None)
    target = ticket_service.create_user(
        db_session,
        name="Billing Admin",
        email="billing-admin@example.com",
        password="adminpass1",
        role=Role.ADMIN,
        department="Billing Team",
    )
    assign_response = client.patch(
        f"/admin/tickets/{ticket['id']}/assign",
        headers=super_admin,
        json={"admin_id": target["id"]},
    )
    assert assign_response.status_code == 200
    assert assign_response.json()["assigned_admin_id"] == target["id"]

    delete_response = client.delete(f"/admin/admins/{target['id']}", headers=super_admin)
    assert delete_response.status_code == 204

    ticket_after = client.get(f"/admin/tickets/{ticket['id']}", headers=super_admin).json()
    assert ticket_after["assigned_admin_id"] is None


def test_scoped_admin_cannot_delete_team_account(client, db_session):
    scoped_admin = _admin_login(
        client, db_session, email="billing-admin@example.com", department="Billing Team"
    )
    target = ticket_service.create_user(
        db_session,
        name="Eng Admin",
        email="eng-admin@example.com",
        password="adminpass1",
        role=Role.ADMIN,
        department="Engineering",
    )

    response = client.delete(f"/admin/admins/{target['id']}", headers=scoped_admin)
    assert response.status_code == 403


def test_super_admin_cannot_delete_own_account(client, db_session):
    super_admin = _admin_login(client, db_session, email="super@example.com", department=None)
    self_user = ticket_service.get_user_by_email(db_session, "super@example.com")

    response = client.delete(f"/admin/admins/{self_user['id']}", headers=super_admin)
    assert response.status_code == 400


def test_deleting_nonexistent_admin_returns_404(client, db_session):
    super_admin = _admin_login(client, db_session, email="super@example.com", department=None)

    response = client.delete("/admin/admins/999999", headers=super_admin)
    assert response.status_code == 404
