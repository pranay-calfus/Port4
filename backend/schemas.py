"""Pydantic request/response models for the backend API. Category/priority/
department fields reuse the existing ticket_router.models Literals so
there's exactly one place that defines the valid category/priority/team
values.
"""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from backend.models import Role, SenderType, TicketStatus
from ticket_router.models import (
    CHOICE_QUESTION_TYPES,
    AssignedTeam,
    FeedbackCategory,
    FeedbackSentiment,
    Priority,
    QuestionType,
)

# --- Auth -------------------------------------------------------------


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)


class AdminCreateRequest(BaseModel):
    # Used by a super-admin (department is None) to provision a new team
    # account from the UI, in place of the old backend/create_admin.py CLI.
    # Omitting department creates another super-admin. role selects between
    # a regular team/support account and a Product & CX account - Product &
    # CX accounts are never department-scoped (see validator below).
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    department: AssignedTeam | None = None
    role: Literal["ADMIN", "PRODUCT_CX"] = "ADMIN"

    @model_validator(mode="after")
    def product_cx_has_no_department(self) -> "AdminCreateRequest":
        if self.role == "PRODUCT_CX" and self.department is not None:
            raise ValueError("Product & CX accounts cannot be assigned a department")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: Role
    department: str | None
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# --- Chat / escalation --------------------------------------------------


class ChatTurn(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str


class ChatMessageRequest(BaseModel):
    message: str = Field(min_length=1)
    history: list[ChatTurn] = Field(default_factory=list)


class ChatMessageResponse(BaseModel):
    reply: str
    history: list[ChatTurn]


class EscalateRequest(BaseModel):
    history: list[ChatTurn] = Field(default_factory=list)
    # The customer's own call on urgency, same as the original Router tab's
    # priority picker. Optional - if omitted, the ticket's priority is
    # simply whatever the AI suggests. If provided, it wins over the AI's
    # suggestion (which is still recorded separately as ai_priority). Only
    # meaningful if the submission is classified as a Support Issue.
    priority: Priority | None = None

    @field_validator("history")
    @classmethod
    def require_at_least_one_user_turn(cls, value: list[ChatTurn]) -> list[ChatTurn]:
        if not any(turn.role == "user" for turn in value):
            raise ValueError("cannot escalate an empty conversation")
        return value


class BulkTicketRequest(BaseModel):
    # Each message is submitted independently through the same
    # classify-then-dispatch path as a single chat escalation (see
    # backend.routers.chat._classify_and_dispatch) - a batch can produce a
    # mix of tickets and feedback rows.
    messages: list[str] = Field(min_length=1)

    @field_validator("messages")
    @classmethod
    def strip_and_drop_blank_entries(cls, value: list[str]) -> list[str]:
        cleaned = [m.strip() for m in value if m.strip()]
        if not cleaned:
            raise ValueError("at least one non-empty submission is required")
        return cleaned


# --- Ticket messages / activity -----------------------------------------


class MessageCreate(BaseModel):
    message: str = Field(min_length=1)


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sender_type: SenderType
    sender_id: int | None
    message: str
    attachments: list | None
    created_at: datetime


class ActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: str
    detail: str | None
    created_at: datetime


# --- Tickets --------------------------------------------------------------


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_number: str
    user_id: int
    title: str
    description: str
    department: str
    priority: str
    status: TicketStatus
    assigned_admin_id: int | None
    ai_summary: str | None
    ai_reasoning: str | None
    ai_category: str | None
    theme: str | None
    ai_emotion: str | None
    ai_confidence: float | None
    ai_priority: str | None
    ai_processing_ms: float | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    closed_at: datetime | None


class TicketDetailOut(TicketOut):
    messages: list[MessageOut]
    activity: list[ActivityOut]
    user: UserOut


# --- Feedback ---------------------------------------------------------


class FeedbackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    raw_text: str
    sentiment: FeedbackSentiment | None
    category: FeedbackCategory | None
    team: str | None
    theme: str | None
    ai_summary: str | None
    ai_reasoning: str | None
    ai_confidence: float | None
    created_at: datetime
    updated_at: datetime


class FeedbackDetailOut(FeedbackOut):
    user: UserOut


class EscalateTicketResult(BaseModel):
    type: Literal["ticket"] = "ticket"
    ticket: TicketDetailOut


class EscalateFeedbackResult(BaseModel):
    type: Literal["feedback"] = "feedback"
    feedback: FeedbackOut


EscalateResponse = Annotated[
    EscalateTicketResult | EscalateFeedbackResult, Field(discriminator="type")
]


class StatusUpdateRequest(BaseModel):
    status: TicketStatus


class AssignRequest(BaseModel):
    admin_id: int


class ReassignRequest(BaseModel):
    department: AssignedTeam | None = None
    priority: Priority | None = None


class UpdatePriorityRequest(BaseModel):
    priority: Priority


# --- Surveys ------------------------------------------------------------


class SurveyQuestionIn(BaseModel):
    question_text: str = Field(min_length=1)
    question_type: QuestionType
    # Only meaningful for multiple_choice/single_choice - validated below.
    options: list[str] | None = None
    required: bool = True

    @model_validator(mode="after")
    def options_match_question_type(self) -> "SurveyQuestionIn":
        is_choice = self.question_type in CHOICE_QUESTION_TYPES
        if is_choice and (self.options is None or len(self.options) < 2):
            raise ValueError(
                f"{self.question_type} questions need at least 2 options"
            )
        if not is_choice and self.options is not None:
            raise ValueError(f"{self.question_type} questions cannot have options")
        return self


class SurveyQuestionOut(SurveyQuestionIn):
    model_config = ConfigDict(from_attributes=True)

    id: int


class SurveyCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    questions: list[SurveyQuestionIn] = Field(min_length=1)


class SurveyUpdateRequest(SurveyCreateRequest):
    pass


class SurveyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    is_published: bool
    created_by: int | None
    created_at: datetime
    updated_at: datetime
    response_count: int = 0


class SurveyDetailOut(SurveyOut):
    questions: list[SurveyQuestionOut]


class AnswerIn(BaseModel):
    # Shape (str vs int vs list[str]) is validated against the question's
    # own question_type in survey_service.submit_response - that requires
    # looking up the question, which a pure Pydantic validator here can't
    # do without a DB round-trip, so it lives in the service layer instead
    # (same pattern as the duplicate-email check in ticket_service.create_user).
    question_id: int
    value: str | int | list[str]


class SurveyResponseSubmitRequest(BaseModel):
    answers: list[AnswerIn] = Field(min_length=1)


class SurveyAnswerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_id: int
    value: str | int | list[str]


class SurveyResponseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    survey_id: int
    user_id: int
    submitted_at: datetime
    answers: list[SurveyAnswerOut]
    user: UserOut
