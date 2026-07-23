from fastapi import APIRouter, Depends, HTTPException, status

from backend.auth import require_feedback_access, require_user
from backend.schemas import (
    SurveyCreateRequest,
    SurveyDetailOut,
    SurveyOut,
    SurveyResponseOut,
    SurveyResponseSubmitRequest,
    SurveyUpdateRequest,
)
from backend.services import survey_service
from backend.supabase_client import client

router = APIRouter(prefix="/surveys", tags=["surveys"])


def _get_survey_or_404(survey_id: int) -> dict:
    survey = survey_service.get_survey(client, survey_id)
    if survey is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Survey not found")
    return survey


# --- Product & CX management ------------------------------------------------


@router.post("", response_model=SurveyDetailOut, status_code=status.HTTP_201_CREATED)
def create_survey(payload: SurveyCreateRequest, admin: dict = Depends(require_feedback_access)):
    return survey_service.create_survey(
        client,
        admin,
        title=payload.title,
        description=payload.description,
        questions=payload.questions,
    )


@router.get("", response_model=list[SurveyOut])
def list_surveys(_admin: dict = Depends(require_feedback_access)):
    return survey_service.list_surveys(client)


@router.get("/responses", response_model=list[SurveyResponseOut])
def list_survey_responses(
    survey_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    rating: int | None = None,
    question_id: int | None = None,
    user_id: int | None = None,
    _admin: dict = Depends(require_feedback_access),
):
    return survey_service.list_responses(
        client,
        survey_id=survey_id,
        date_from=date_from,
        date_to=date_to,
        rating=rating,
        question_id=question_id,
        user_id=user_id,
    )


# --- Customer-facing ---------------------------------------------------
# Registered before "/{survey_id}" so FastAPI doesn't try to parse "active"
# as the int path param - same gotcha as "/admin/team-accounts" vs
# "/admin/admins/{admin_id}" and "/feedback/metrics" vs "/feedback/{id}".


@router.get("/active", response_model=list[SurveyDetailOut])
def list_active_surveys(user: dict = Depends(require_user)):
    return survey_service.list_active_surveys_for_user(client, user["id"])


# --- Product & CX management (continued) ------------------------------


@router.get("/{survey_id}", response_model=SurveyDetailOut)
def get_survey(survey_id: int, _admin: dict = Depends(require_feedback_access)):
    return _get_survey_or_404(survey_id)


@router.patch("/{survey_id}", response_model=SurveyDetailOut)
def update_survey(
    survey_id: int, payload: SurveyUpdateRequest, _admin: dict = Depends(require_feedback_access)
):
    _get_survey_or_404(survey_id)
    return survey_service.update_survey(
        client,
        survey_id,
        title=payload.title,
        description=payload.description,
        questions=payload.questions,
    )


@router.delete("/{survey_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_survey(survey_id: int, _admin: dict = Depends(require_feedback_access)):
    _get_survey_or_404(survey_id)
    survey_service.delete_survey(client, survey_id)


@router.patch("/{survey_id}/publish", response_model=SurveyDetailOut)
def publish_survey(survey_id: int, _admin: dict = Depends(require_feedback_access)):
    _get_survey_or_404(survey_id)
    return survey_service.set_published(client, survey_id, True)


@router.patch("/{survey_id}/unpublish", response_model=SurveyDetailOut)
def unpublish_survey(survey_id: int, _admin: dict = Depends(require_feedback_access)):
    _get_survey_or_404(survey_id)
    return survey_service.set_published(client, survey_id, False)


@router.get("/{survey_id}/analytics")
def survey_analytics(
    survey_id: int,
    date_from: str | None = None,
    date_to: str | None = None,
    _admin: dict = Depends(require_feedback_access),
) -> dict:
    _get_survey_or_404(survey_id)
    return survey_service.survey_analytics(client, survey_id, date_from=date_from, date_to=date_to)


@router.post(
    "/{survey_id}/responses",
    response_model=SurveyResponseOut,
    status_code=status.HTTP_201_CREATED,
)
def submit_survey_response(
    survey_id: int, payload: SurveyResponseSubmitRequest, user: dict = Depends(require_user)
):
    survey = _get_survey_or_404(survey_id)
    if not survey["is_published"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Survey not found")
    try:
        return survey_service.submit_response(client, survey, user, payload.answers)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
