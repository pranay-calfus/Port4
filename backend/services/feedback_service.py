"""Business logic for customer feedback: creation from a chat transcript,
classification, and the filtered queries backing the Product & CX
dashboard. Mirrors ticket_service.py's style - plain dicts over the
Supabase client, no ORM session - but feedback has no lifecycle/status of
its own, so there's no equivalent of change_status()/assign_admin()/etc.
"""

from supabase import Client

from backend.services.ticket_service import (
    _end_of_day,
    _maybe_single,
    _theme_trend,
    _top_themes,
    _transcript_to_text,
)
from ticket_router.services.feedback_classification_service import classify_feedback


def create_feedback_from_chat(client: Client, user: dict, history: list[tuple[str, str]]) -> dict:
    """Turns a chat conversation classified as Customer Feedback into a
    `feedback` row: stores the raw transcript, then runs the fail-soft
    feedback classifier and updates the row with its result. Never raises -
    classify_feedback() always returns a usable (possibly default)
    classification, so the customer's submission is never lost.
    """
    raw_text = _transcript_to_text(history)

    feedback = (
        client.table("feedback").insert({"user_id": user["id"], "raw_text": raw_text}).execute().data[0]
    )

    result = classify_feedback(raw_text)
    feedback = (
        client.table("feedback")
        .update(
            {
                "sentiment": result.sentiment,
                "category": result.category,
                "team": result.team,
                "theme": result.theme,
                "ai_summary": result.summary,
                "ai_reasoning": result.reasoning,
                "ai_confidence": result.confidence,
            }
        )
        .eq("id", feedback["id"])
        .execute()
        .data[0]
    )
    return feedback


def get_feedback(client: Client, feedback_id: int) -> dict | None:
    feedback = _maybe_single(client.table("feedback").select("*").eq("id", feedback_id))
    if feedback is None:
        return None
    requester = _maybe_single(client.table("users").select("*").eq("id", feedback["user_id"]))
    return {**feedback, "user": requester}


def list_feedback(
    client: Client,
    *,
    sentiment: str | None = None,
    category: str | None = None,
    team: str | None = None,
    search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict]:
    query = client.table("feedback").select("*")
    if sentiment:
        query = query.eq("sentiment", sentiment)
    if category:
        query = query.eq("category", category)
    if team:
        query = query.eq("team", team)
    if date_from:
        query = query.gte("created_at", date_from)
    if date_to:
        query = query.lte("created_at", _end_of_day(date_to))
    query = query.order("created_at", desc=True).order("id", desc=True)

    rows = query.execute().data
    if search:
        needle = search.strip().lower()
        rows = [
            row
            for row in rows
            if needle in row["raw_text"].lower() or needle in (row["ai_summary"] or "").lower()
        ]
    return rows


def _tally(rows: list[dict], key) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = key(row)
        if value is None:
            continue
        counts[value] = counts.get(value, 0) + 1
    return counts


def feedback_metrics(
    client: Client, *, date_from: str | None = None, date_to: str | None = None
) -> dict:
    rows = list_feedback(client, date_from=date_from, date_to=date_to)
    ranked_themes = _top_themes(rows)
    return {
        "total_feedback": len(rows),
        "feedback_per_sentiment": _tally(rows, lambda r: r["sentiment"]),
        "feedback_per_category": _tally(rows, lambda r: r["category"]),
        "feedback_per_team": _tally(rows, lambda r: r["team"]),
        "top_themes": ranked_themes,
        "theme_trend": _theme_trend(rows, [t["theme"] for t in ranked_themes]),
        "date_range": {"from": date_from, "to": date_to},
    }
