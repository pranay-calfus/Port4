"""Business logic for the weekly feedback insight report: fetching a
period's feedback, aggregating it deterministically, generating the AI
narrative, and persisting the result. Mirrors feedback_service.py's style -
plain dicts over the Supabase client, no ORM session.

Counting/ranking (sentiment_breakdown, top_themes) is done here in plain
Python, not by the AI - the AI's only job (see
ticket_router.services.weekly_summary_service.generate_weekly_narrative) is
turning those already-correct numbers into prose, never re-deriving them.
"""

from datetime import UTC, date, datetime, time, timedelta

from supabase import Client

from backend.services import feedback_service
from backend.services.theme_normalization import group_themes
from backend.services.ticket_service import _maybe_single, _top_themes
from ticket_router.errors import AppError
from ticket_router.logger import logger
from ticket_router.models import FEEDBACK_SENTIMENTS
from ticket_router.services.weekly_summary_service import generate_weekly_narrative

# How many of the top themes get real feedback excerpts attached for the AI
# prompt (grounds "key insights" in actual customer wording instead of
# leaving the model to invent plausible-sounding detail), and how much of
# each excerpt is kept - capped so the JSON handed to the AI stays well
# under ticket_router.models.MAX_TICKET_LENGTH even for a very active week.
_THEMES_WITH_EXCERPTS = 5
_EXCERPTS_PER_THEME = 2
_EXCERPT_MAX_CHARS = 160


def _previous_calendar_week(today: date | None = None) -> tuple[datetime, datetime]:
    """The most recently completed Monday-Sunday week strictly before
    `today` - what the Monday-morning scheduled job (see backend/scheduler.py)
    generates a report for, so consecutive weekly reports never overlap or
    leave a gap.
    """
    today = today or datetime.now(UTC).date()
    this_monday = today - timedelta(days=today.weekday())
    last_monday = this_monday - timedelta(days=7)
    last_sunday = this_monday - timedelta(days=1)
    return (
        datetime.combine(last_monday, time.min, tzinfo=UTC),
        datetime.combine(last_sunday, time.max, tzinfo=UTC),
    )


def _trailing_seven_days(today: date | None = None) -> tuple[datetime, datetime]:
    """Default period for an on-demand report: the 7 days up to and
    including today - the mission's literal "previous 7 days" window,
    distinct from _previous_calendar_week above (which the Monday scheduler
    uses instead so its reports tile cleanly week to week).
    """
    today = today or datetime.now(UTC).date()
    return (
        datetime.combine(today - timedelta(days=6), time.min, tzinfo=UTC),
        datetime.combine(today, time.max, tzinfo=UTC),
    )


def resolve_period(date_from: str | None, date_to: str | None) -> tuple[datetime, datetime]:
    """Resolves the (period_start, period_end) for a manually-triggered
    report: an explicit "YYYY-MM-DD" date_from/date_to pair (same shape as
    every other dashboard date-range filter) if both are given, otherwise
    the trailing 7 days ending today.
    """
    if date_from and date_to:
        return (
            datetime.combine(date.fromisoformat(date_from), time.min, tzinfo=UTC),
            datetime.combine(date.fromisoformat(date_to), time.max, tzinfo=UTC),
        )
    return _trailing_seven_days()


def _tally(rows: list[dict], key) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = key(row)
        if value is None:
            continue
        counts[value] = counts.get(value, 0) + 1
    return counts


def _sentiment_breakdown(rows: list[dict]) -> dict:
    counts = _tally(rows, lambda r: r["sentiment"])
    total = len(rows)
    return {
        sentiment: {
            "count": counts.get(sentiment, 0),
            "pct": round(counts.get(sentiment, 0) / total * 100, 1) if total else 0.0,
        }
        for sentiment in FEEDBACK_SENTIMENTS
    }


def _theme_excerpts(rows: list[dict], top_themes: list[dict]) -> dict[str, list[str]]:
    """Real feedback excerpts per top theme, for the AI prompt (see module
    docstring). `top_themes` entries are canonical, normalized labels (see
    theme_normalization.group_themes) - e.g. "Billing Issues" rather than
    any single row's raw "Billing Error"/"Billing Errors"/"Payment Issue" -
    so matching rows back to a theme goes through the same raw-to-label
    mapping _top_themes used, not exact string equality against `r["theme"]`.
    """
    raw_to_label = group_themes(rows)
    excerpts: dict[str, list[str]] = {}
    for entry in top_themes[:_THEMES_WITH_EXCERPTS]:
        theme = entry["theme"]
        if theme == "Other":
            continue
        matches = [
            r["raw_text"] for r in rows if raw_to_label.get(r["theme"]) == theme
        ][:_EXCERPTS_PER_THEME]
        excerpts[theme] = [
            m if len(m) <= _EXCERPT_MAX_CHARS else m[: _EXCERPT_MAX_CHARS] + "…" for m in matches
        ]
    return excerpts


def _empty_narrative() -> dict:
    return {
        "overview": "No customer feedback was submitted during this period.",
        "overall_sentiment": "Not applicable - no feedback was received this period.",
        "key_insights": [],
        "risks": [],
        "recommendations": [],
        "positive_highlights": [],
    }


def get_report_for_period(client: Client, period_start: datetime, period_end: datetime) -> dict | None:
    return _maybe_single(
        client.table("weekly_reports")
        .select("*")
        .eq("period_start", period_start.isoformat())
        .eq("period_end", period_end.isoformat())
    )


def get_latest_report(client: Client) -> dict | None:
    result = (
        client.table("weekly_reports")
        .select("*")
        .order("period_end", desc=True)
        .order("id", desc=True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def list_reports(client: Client, *, limit: int = 52) -> list[dict]:
    return (
        client.table("weekly_reports")
        .select("*")
        .order("period_end", desc=True)
        .order("id", desc=True)
        .limit(limit)
        .execute()
        .data
    )


def generate_weekly_report(
    client: Client, *, period_start: datetime, period_end: datetime, generated_by: str
) -> dict:
    """Fetches the period's feedback, aggregates it, generates the AI
    narrative (skipped entirely when there's no feedback to summarize - see
    _empty_narrative), and inserts the result as a new weekly_reports row.
    Always inserts, never updates - see WeeklyReport's docstring.
    """
    rows = feedback_service.list_feedback(
        client,
        date_from=period_start.date().isoformat(),
        date_to=period_end.date().isoformat(),
    )

    sentiment_breakdown = _sentiment_breakdown(rows)
    top_themes = _top_themes(rows)

    if rows:
        ai_input = {
            "period": {"from": period_start.date().isoformat(), "to": period_end.date().isoformat()},
            "total_feedback": len(rows),
            "sentiment_breakdown": sentiment_breakdown,
            "category_breakdown": _tally(rows, lambda r: r["category"]),
            "team_breakdown": _tally(rows, lambda r: r["team"]),
            "top_themes": top_themes,
            "theme_excerpts": _theme_excerpts(rows, top_themes),
        }
        result = generate_weekly_narrative(ai_input)
        narrative = result.model_dump()
        model_used = result.model_used
    else:
        narrative = _empty_narrative()
        model_used = None

    report = (
        client.table("weekly_reports")
        .insert(
            {
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "total_feedback": len(rows),
                "sentiment_breakdown": sentiment_breakdown,
                "top_themes": top_themes,
                **narrative,
                "generated_by": generated_by,
                "model_used": model_used,
            }
        )
        .execute()
        .data[0]
    )
    return report


def generate_report_for_previous_week(client: Client) -> dict | None:
    """Entry point for the Monday APScheduler job (see backend/scheduler.py).
    Generates a report for the most recently completed Monday-Sunday week,
    skipping generation (never overwriting) if a report for that exact
    period already exists - e.g. if the app restarts and the scheduler
    happens to fire twice for the same week.
    """
    period_start, period_end = _previous_calendar_week()
    existing = get_report_for_period(client, period_start, period_end)
    if existing is not None:
        logger.info(
            "Weekly report already exists for period, skipping",
            {"period_start": period_start.isoformat(), "period_end": period_end.isoformat()},
        )
        return existing

    try:
        return generate_weekly_report(
            client, period_start=period_start, period_end=period_end, generated_by="scheduled"
        )
    except AppError as error:
        logger.error(
            "Scheduled weekly report generation failed",
            {
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "error": str(error),
            },
        )
        return None
