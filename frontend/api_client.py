"""Thin HTTP client shared by both Streamlit frontends. Neither frontend
touches a database directly - everything goes through the backend API,
which is what actually keeps the user and admin surfaces isolated (they're
separate processes that only ever call their own slice of the API).
"""

import os

import httpx

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Mirrors backend.models.TicketStatus - kept as a plain tuple here (rather
# than importing the backend package) since the frontends only ever talk to
# the API over HTTP, never to backend internals directly.
TICKET_STATUSES = (
    "NEW",
    "OPEN",
    "IN_PROGRESS",
    "PENDING_CUSTOMER",
    "ON_HOLD",
    "RESOLVED",
    "CLOSED",
)


class ApiError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _unwrap(response: httpx.Response):
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise ApiError(response.status_code, str(detail))
    return response.json() if response.content else None


def _request(method: str, path: str, token: str | None = None, **kwargs):
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with httpx.Client(base_url=API_BASE_URL, timeout=60.0) as client:
            response = client.request(method, path, headers=headers, **kwargs)
    except httpx.ConnectError as error:
        raise ApiError(
            503, f"Cannot reach the API at {API_BASE_URL}. Is the backend running?"
        ) from error
    return _unwrap(response)


# --- Auth ---------------------------------------------------------------


def register(name: str, email: str, password: str) -> dict:
    return _request(
        "POST", "/auth/register", json={"name": name, "email": email, "password": password}
    )


def login(email: str, password: str) -> dict:
    return _request("POST", "/auth/login", json={"email": email, "password": password})


def whoami(token: str) -> dict:
    """Resolves a token back into its owner - works for either role. Used
    to restore a session from a token persisted in the URL's query params
    (see frontend/app.py), so the app doesn't need the caller to already
    know whether it's a user or admin token.
    """
    return _request("GET", "/auth/me", token=token)


def admin_login(email: str, password: str) -> dict:
    return _request("POST", "/admin/login", json={"email": email, "password": password})


def forgot_password(email: str) -> dict:
    return _request("POST", "/auth/forgot-password", json={"email": email})


# --- Chat / escalation ------------------------------------------------------


def send_chat_message(token: str, message: str, history: list[dict]) -> dict:
    return _request(
        "POST", "/chat/message", token=token, json={"message": message, "history": history}
    )


def escalate_to_ticket(token: str, history: list[dict], priority: str | None = None) -> dict:
    return _request(
        "POST", "/chat/escalate", token=token, json={"history": history, "priority": priority}
    )


def bulk_create_tickets(token: str, messages: list[str]) -> list[dict]:
    return _request("POST", "/tickets/bulk", token=token, json={"messages": messages})


# --- User-facing tickets ------------------------------------------------------


def list_my_tickets(token: str) -> list[dict]:
    return _request("GET", "/tickets", token=token)


def get_my_ticket(token: str, ticket_id: int) -> dict:
    return _request("GET", f"/tickets/{ticket_id}", token=token)


def reply_to_ticket(token: str, ticket_id: int, message: str) -> dict:
    return _request(
        "POST", f"/tickets/{ticket_id}/messages", token=token, json={"message": message}
    )


def accept_solution(token: str, ticket_id: int) -> dict:
    return _request("POST", f"/tickets/{ticket_id}/accept-solution", token=token)


def reopen_ticket(token: str, ticket_id: int) -> dict:
    return _request("POST", f"/tickets/{ticket_id}/reopen", token=token)


# --- Admin ------------------------------------------------------------------


def admin_list_tickets(token: str, **filters) -> list[dict]:
    params = {k: v for k, v in filters.items() if v not in (None, "")}
    return _request("GET", "/admin/tickets", token=token, params=params)


def admin_get_ticket(token: str, ticket_id: int) -> dict:
    return _request("GET", f"/admin/tickets/{ticket_id}", token=token)


def admin_update_status(token: str, ticket_id: int, new_status: str) -> dict:
    return _request(
        "PATCH", f"/admin/tickets/{ticket_id}/status", token=token, json={"status": new_status}
    )


def admin_assign(token: str, ticket_id: int, admin_id: int) -> dict:
    return _request(
        "PATCH", f"/admin/tickets/{ticket_id}/assign", token=token, json={"admin_id": admin_id}
    )


def admin_reassign(
    token: str, ticket_id: int, department: str | None, priority: str | None
) -> dict:
    payload = {"department": department, "priority": priority}
    return _request("PATCH", f"/admin/tickets/{ticket_id}/reassign", token=token, json=payload)


def admin_reply(token: str, ticket_id: int, message: str) -> dict:
    return _request(
        "POST", f"/admin/tickets/{ticket_id}/message", token=token, json={"message": message}
    )


def admin_metrics(token: str) -> dict:
    return _request("GET", "/admin/metrics", token=token)


def admin_list_admins(token: str) -> list[dict]:
    return _request("GET", "/admin/admins", token=token)
