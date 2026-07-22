from fastapi import APIRouter, Depends, HTTPException, status

from backend.auth import require_feedback_access
from backend.schemas import FeedbackDetailOut, FeedbackOut
from backend.services import feedback_service
from backend.supabase_client import client

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.get("", response_model=list[FeedbackOut])
def list_feedback(
    sentiment: str | None = None,
    category: str | None = None,
    team: str | None = None,
    search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    _user: dict = Depends(require_feedback_access),
):
    return feedback_service.list_feedback(
        client,
        sentiment=sentiment,
        category=category,
        team=team,
        search=search,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/metrics")
def metrics(
    date_from: str | None = None,
    date_to: str | None = None,
    _user: dict = Depends(require_feedback_access),
) -> dict:
    return feedback_service.feedback_metrics(client, date_from=date_from, date_to=date_to)


@router.get("/{feedback_id}", response_model=FeedbackDetailOut)
def get_feedback(feedback_id: int, _user: dict = Depends(require_feedback_access)):
    feedback = feedback_service.get_feedback(client, feedback_id)
    if feedback is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")
    return feedback
