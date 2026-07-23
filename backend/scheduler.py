"""APScheduler-driven background jobs for the backend API - currently just
the weekly feedback report (see backend.services.weekly_summary_service.
generate_report_for_previous_week). Started once from main.py's lifespan
alongside run_migrations()/seed_accounts(), stopped on shutdown.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.services import weekly_summary_service
from backend.supabase_client import client

_WEEKLY_REPORT_JOB_ID = "weekly_feedback_report"

_scheduler = BackgroundScheduler(timezone="UTC")


def _run_weekly_report_job() -> None:
    # generate_report_for_previous_week already catches AppError and logs
    # it - nothing here should ever raise into APScheduler's job runner.
    weekly_summary_service.generate_report_for_previous_week(client)


def start_scheduler() -> None:
    if _scheduler.running:
        return
    # Every Monday morning: generates a report for the week that just
    # ended (Monday-Sunday) - see _previous_calendar_week in
    # weekly_summary_service.
    _scheduler.add_job(
        _run_weekly_report_job,
        CronTrigger(day_of_week="mon", hour=6, minute=0),
        id=_WEEKLY_REPORT_JOB_ID,
        replace_existing=True,
    )
    _scheduler.start()


def stop_scheduler() -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
