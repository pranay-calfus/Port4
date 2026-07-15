from backend.models import Role
from backend.services import ticket_service


def _register(client, email="alice@example.com", password="password123"):
    return client.post(
        "/auth/register", json={"name": "Alice", "email": email, "password": password}
    )


def test_register_creates_user_and_returns_token(client):
    response = _register(client)
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "alice@example.com"
    assert body["user"]["role"] == "USER"
    assert body["access_token"]


def test_register_rejects_duplicate_email(client):
    _register(client)
    response = _register(client)
    assert response.status_code == 409


def test_login_succeeds_with_correct_password(client):
    _register(client)
    response = client.post(
        "/auth/login", json={"email": "alice@example.com", "password": "password123"}
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_login_rejects_wrong_password(client):
    _register(client)
    response = client.post(
        "/auth/login", json={"email": "alice@example.com", "password": "wrong-password"}
    )
    assert response.status_code == 401


def test_user_login_rejects_admin_account(client, db_session):
    ticket_service.create_user(
        db_session, name="Ops", email="admin@example.com", password="adminpass1", role=Role.ADMIN
    )
    response = client.post(
        "/auth/login", json={"email": "admin@example.com", "password": "adminpass1"}
    )
    assert response.status_code == 401


def test_admin_login_rejects_regular_user(client):
    _register(client)
    response = client.post(
        "/admin/login", json={"email": "alice@example.com", "password": "password123"}
    )
    assert response.status_code == 401


def test_admin_login_succeeds_for_admin_account(client, db_session):
    ticket_service.create_user(
        db_session, name="Ops", email="admin@example.com", password="adminpass1", role=Role.ADMIN
    )
    response = client.post(
        "/admin/login", json={"email": "admin@example.com", "password": "adminpass1"}
    )
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "ADMIN"


def test_me_returns_current_user_for_user_token(client):
    register = _register(client)
    token = register.json()["access_token"]

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "alice@example.com"
    assert response.json()["role"] == "USER"


def test_me_returns_current_user_for_admin_token(client, db_session):
    ticket_service.create_user(
        db_session, name="Ops", email="admin@example.com", password="adminpass1", role=Role.ADMIN
    )
    login = client.post(
        "/admin/login", json={"email": "admin@example.com", "password": "adminpass1"}
    )
    token = login.json()["access_token"]

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["role"] == "ADMIN"


def test_me_rejects_missing_token(client):
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_protected_endpoint_rejects_missing_token(client):
    response = client.get("/tickets")
    assert response.status_code == 401


def test_protected_endpoint_rejects_wrong_role(client, db_session):
    ticket_service.create_user(
        db_session, name="Ops", email="admin@example.com", password="adminpass1", role=Role.ADMIN
    )
    login = client.post(
        "/admin/login", json={"email": "admin@example.com", "password": "adminpass1"}
    )
    token = login.json()["access_token"]

    # An admin token must not grant access to the user-only /tickets router.
    response = client.get("/tickets", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
