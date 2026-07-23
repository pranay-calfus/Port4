from fastapi import APIRouter, Depends, HTTPException, status

from backend.auth import require_feedback_access
from backend.schemas import WeeklyReportOut
from backend.services import weekly_summary_service
from backend.supabase_client import client

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/weekly/latest", response_model=WeeklyReportOut)
def latest_weekly_report(_user: dict = Depends(require_feedback_access)):
    report = weekly_summary_service.get_latest_report(client)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No weekly report has been generated yet"
        )
    return report


@router.get("/weekly", response_model=list[WeeklyReportOut])
def weekly_report_history(limit: int = 52, _user: dict = Depends(require_feedback_access)):
    return weekly_summary_service.list_reports(client, limit=limit)


@router.post("/weekly/generate", response_model=WeeklyReportOut, status_code=status.HTTP_201_CREATED)
def generate_weekly_report_now(
    date_from: str | None = None,
    date_to: str | None = None,
    _user: dict = Depends(require_feedback_access),
):
    """Manually generates a report right now - defaults to the trailing 7
    days ending today, or an explicit date_from/date_to range (same
    "YYYY-MM-DD" shape as every other dashboard date-range filter).
    """
    period_start, period_end = weekly_summary_service.resolve_period(date_from, date_to)
    return weekly_summary_service.generate_weekly_report(
        client, period_start=period_start, period_end=period_end, generated_by="manual"
    )
