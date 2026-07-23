from backend.models import Role
from backend.services import ticket_service, weekly_summary_service
from ticket_router.errors import AIUnavailableError
from ticket_router.models import WeeklySummaryResult


def _register(client, email="alice@example.com"):
    response = client.post(
        "/auth/register", json={"name": "Alice", "email": email, "password": "password123"}
    )
    return response.json()["user"]["id"]


def _admin_login(client, db_session, email="admin@example.com", department=None, role=Role.ADMIN):
    ticket_service.create_user(
        db_session, name="Admin", email=email, password="adminpass1", role=role, department=department
    )
    login_path = "/product-cx/login" if role == Role.PRODUCT_CX else "/admin/login"
    login = client.post(login_path, json={"email": email, "password": "adminpass1"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _seed_feedback(db_session, user_id, *, sentiment, category, team, theme, raw_text):
    db_session.table("feedback").insert(
        {
            "user_id": user_id,
            "raw_text": raw_text,
            "sentiment": sentiment,
            "category": category,
            "team": team,
            "theme": theme,
            "ai_summary": "A summary.",
            "ai_reasoning": "A reason.",
            "ai_confidence": 0.9,
        }
    ).execute()


def _fake_narrative() -> WeeklySummaryResult:
    result = WeeklySummaryResult(
        overview="Test overview.",
        overall_sentiment="Mostly negative.",
        key_insights=["The 'Pricing Feedback' theme dominated this week."],
        risks=["Possible churn risk from pricing complaints."],
        recommendations=["Sales Team should review pricing given the 'Pricing Feedback' theme."],
        positive_highlights=[],
    )
    result.model_used = "fake-model"
    return result


def _stub_narrative(monkeypatch, captured: list | None = None):
    def _fake(metrics):
        if captured is not None:
            captured.append(metrics)
        return _fake_narrative()

    monkeypatch.setattr(weekly_summary_service, "generate_weekly_narrative", _fake)


def test_manual_generate_with_no_feedback_returns_empty_narrative(client, db_session):
    headers = _admin_login(client, db_session, email="cx@example.com", role=Role.PRODUCT_CX)

    response = client.post("/reports/weekly/generate", headers=headers)

    assert response.status_code == 201
    body = response.json()
    assert body["total_feedback"] == 0
    assert body["generated_by"] == "manual"
    assert body["model_used"] is None
    assert body["key_insights"] == []
    assert "No customer feedback" in body["overview"]


def test_manual_generate_aggregates_feedback_and_uses_ai_narrative(client, db_session, monkeypatch):
    user_id = _register(client)
    _seed_feedback(
        db_session,
        user_id,
        sentiment="Negative",
        category="Pricing",
        team="Sales Team",
        theme="Pricing Feedback",
        raw_text="Your pricing feels a bit high compared to competitors.",
    )
    _seed_feedback(
        db_session,
        user_id,
        sentiment="Negative",
        category="Pricing",
        team="Sales Team",
        theme="Pricing Feedback",
        raw_text="I think the plans are overpriced.",
    )
    _seed_feedback(
        db_session,
        user_id,
        sentiment="Positive",
        category="General Praise",
        team="Customer Success",
        theme="Positive Experience",
        raw_text="The app is great overall.",
    )
    captured: list = []
    _stub_narrative(monkeypatch, captured)
    headers = _admin_login(client, db_session, email="cx@example.com", role=Role.PRODUCT_CX)

    response = client.post("/reports/weekly/generate", headers=headers)

    assert response.status_code == 201
    body = response.json()
    assert body["total_feedback"] == 3
    assert body["sentiment_breakdown"]["Negative"]["count"] == 2
    assert body["sentiment_breakdown"]["Positive"]["count"] == 1
    assert {"theme": "Pricing Feedback", "count": 2} in body["top_themes"]
    assert body["overview"] == "Test overview."
    assert body["recommendations"] == [
        "Sales Team should review pricing given the 'Pricing Feedback' theme."
    ]
    assert body["generated_by"] == "manual"
    assert body["model_used"] == "fake-model"

    assert captured[0]["total_feedback"] == 3
    # list_feedback orders newest-first, so the excerpts come back in that
    # same order (most recently submitted first) - not insertion order.
    assert captured[0]["theme_excerpts"]["Pricing Feedback"] == [
        "I think the plans are overpriced.",
        "Your pricing feels a bit high compared to competitors.",
    ]


def test_manual_generate_surfaces_ai_failure_as_503(client, db_session, monkeypatch):
    user_id = _register(client)
    _seed_feedback(
        db_session,
        user_id,
        sentiment="Negative",
        category="Pricing",
        team="Sales Team",
        theme="Pricing Feedback",
        raw_text="Too expensive.",
    )

    def _raise(metrics):  # noqa: ARG001
        raise AIUnavailableError("AI service is currently unavailable.")

    monkeypatch.setattr(weekly_summary_service, "generate_weekly_narrative", _raise)
    headers = _admin_login(client, db_session, email="cx@example.com", role=Role.PRODUCT_CX)

    response = client.post("/reports/weekly/generate", headers=headers)

    assert response.status_code == 503


def test_latest_report_returns_404_when_none_exist(client, db_session):
    headers = _admin_login(client, db_session, email="cx@example.com", role=Role.PRODUCT_CX)

    response = client.get("/reports/weekly/latest", headers=headers)

    assert response.status_code == 404


def test_latest_and_history_return_reports_ordered_most_recent_first(client, db_session):
    headers = _admin_login(client, db_session, email="cx@example.com", role=Role.PRODUCT_CX)
    client.post(
        "/reports/weekly/generate",
        params={"date_from": "2020-01-01", "date_to": "2020-01-07"},
        headers=headers,
    )
    client.post(
        "/reports/weekly/generate",
        params={"date_from": "2020-02-01", "date_to": "2020-02-07"},
        headers=headers,
    )

    latest = client.get("/reports/weekly/latest", headers=headers)
    assert latest.status_code == 200
    assert latest.json()["period_start"].startswith("2020-02-01")

    history = client.get("/reports/weekly", headers=headers)
    assert history.status_code == 200
    periods = [r["period_start"][:10] for r in history.json()]
    assert periods == ["2020-02-01", "2020-01-01"]


def test_department_scoped_admin_cannot_access_reports(client, db_session):
    headers = _admin_login(client, db_session, department="Billing Team")

    assert client.get("/reports/weekly/latest", headers=headers).status_code == 403
    assert client.get("/reports/weekly", headers=headers).status_code == 403
    assert client.post("/reports/weekly/generate", headers=headers).status_code == 403


def test_scheduled_generation_skips_if_period_already_has_a_report(db_session):
    """The Monday scheduler job (backend.scheduler -> generate_report_for_
    previous_week) must never generate a second report for a week it
    already covered - this is the "without overwriting previous reports"
    guarantee, enforced at the application level rather than a DB
    constraint (see WeeklyReport's docstring for why)."""
    first = weekly_summary_service.generate_report_for_previous_week(db_session)
    second = weekly_summary_service.generate_report_for_previous_week(db_session)

    assert first["id"] == second["id"]
    all_reports = db_session.table("weekly_reports").select("id").execute().data
    assert len(all_reports) == 1


def test_super_admin_and_product_cx_can_access_reports(client, db_session):
    super_admin_headers = _admin_login(client, db_session, email="super@example.com")
    assert client.get("/reports/weekly/latest", headers=super_admin_headers).status_code == 404

    product_cx_headers = _admin_login(
        client, db_session, email="cx@example.com", role=Role.PRODUCT_CX
    )
    assert (
        client.post("/reports/weekly/generate", headers=product_cx_headers).status_code == 201
    )
    assert client.get("/reports/weekly/latest", headers=super_admin_headers).status_code == 200
