from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Category = Literal[
    "Billing",
    "Technical Support",
    "Account Access",
    "Bug Report",
    "Feature Request",
    "Refund",
    "Shipping",
    "Sales",
    "Security",
    "General Inquiry",
    "Other",
]

Priority = Literal["High", "Medium", "Low"]

Emotion = Literal["Neutral", "Worried", "Frustrated", "Angry", "Disappointed"]

# One emoji per emotion, for compact display next to the text label in the
# frontend's ticket AI card.
EMOTION_EMOJI: dict[str, str] = {
    "Neutral": "🫥",
    "Worried": "😰",
    "Frustrated": "😤",
    "Angry": "😡",
    "Disappointed": "😞",
}

AssignedTeam = Literal[
    "Billing Team",
    "Support Team",
    "Engineering",
    "QA",
    "Security Team",
    "Sales Team",
    "Logistics",
    "Customer Success",
]

CATEGORIES: tuple[str, ...] = Category.__args__
PRIORITIES: tuple[str, ...] = Priority.__args__
EMOTIONS: tuple[str, ...] = Emotion.__args__
ASSIGNED_TEAMS: tuple[str, ...] = AssignedTeam.__args__

# Whether a submission is a support issue (should become a ticket) or
# unsolicited customer feedback (should not) - see
# ticket_router.services.submission_type_service.classify_submission_type.
SubmissionType = Literal["SUPPORT_ISSUE", "CUSTOMER_FEEDBACK"]

FeedbackSentiment = Literal["Positive", "Neutral", "Negative"]

FeedbackCategory = Literal[
    "UI/UX",
    "Performance",
    "Pricing",
    "Feature Request",
    "Customer Support Experience",
    "General Praise",
    "Other",
]

SUBMISSION_TYPES: tuple[str, ...] = SubmissionType.__args__
FEEDBACK_SENTIMENTS: tuple[str, ...] = FeedbackSentiment.__args__
FEEDBACK_CATEGORIES: tuple[str, ...] = FeedbackCategory.__args__

# Survey question types (see backend.models.SurveyQuestion). Not an
# AI-classified value - authored directly by a Product & CX user when
# building a survey - but kept here alongside the other taxonomies since
# it's still a single-source-of-truth Literal shared by the Pydantic
# schemas (backend/schemas.py) and the SQLAlchemy model's plain-string
# column, the same rationale as Category/AssignedTeam above.
QuestionType = Literal["short_text", "long_text", "rating", "multiple_choice", "single_choice"]

QUESTION_TYPES: tuple[str, ...] = QuestionType.__args__

# Question types that carry a fixed set of selectable options.
CHOICE_QUESTION_TYPES = {"multiple_choice", "single_choice"}

# Hard cap on ticket length. Anything longer is truncated (not rejected)
# before being sent to the AI - see services/prompt_service.py.
MAX_TICKET_LENGTH = 8000


class TicketRouteResult(BaseModel):
    """The AI output contract. This mirrors the tool's own `parameters`
    JSON schema exactly - it is the second line of defense (Layer 3 of JSON
    reliability) after OpenAI's forced tool call, guarding against enum
    drift, wrong types, or a malformed tool call. `assigned_team` uses a
    camelCase alias so the wire format matches the tool schema while the
    Python attribute stays snake_case/PEP 8.
    """

    model_config = ConfigDict(populate_by_name=True)

    category: Category
    priority: Priority
    assigned_team: AssignedTeam = Field(alias="assignedTeam")
    emotion: Emotion
    # A short, freely-generated (not enum-constrained) label for the
    # recurring problem pattern this ticket belongs to - e.g. "Login
    # Issues", "Payment Failure" - distinct from `category`'s fixed
    # taxonomy. See "THEME RULES" in prompts.py for the generation rules
    # that keep this consistent enough to aggregate across tickets.
    theme: str = Field(min_length=1)
    reasoning: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    # Not part of the AI's output contract - set by the routing service
    # after a successful call, purely so the UI can show which model
    # actually answered (relevant once model fallback kicks in).
    model_used: str | None = Field(default=None, exclude=True)


class ResolutionCheck(BaseModel):
    """Output contract for the resolution-detection classifier (see
    ticket_router.services.resolution_service.check_resolution) - decides
    whether a customer's latest reply confirms their issue is resolved and
    the ticket can be closed.
    """

    resolved: bool
    reasoning: str = Field(min_length=1)


# The mid-lifecycle statuses the status-progression classifier is allowed to
# move a ticket between - RESOLVED/CLOSED stay check_resolution's job, and a
# ticket that's NEW or already RESOLVED/CLOSED is never handed to this
# classifier at all (see backend.services.ticket_service._maybe_progress_status).
StatusProgression = Literal["OPEN", "IN_PROGRESS", "PENDING_CUSTOMER", "ON_HOLD"]

STATUS_PROGRESSIONS: tuple[str, ...] = StatusProgression.__args__

# Required sentinel meaning "nothing has shifted enough to move the ticket
# yet" - a required field with this sentinel, rather than an optional/
# nullable one, matches this codebase's existing forced-tool-call schemas
# (see CHECK_RESOLUTION_TOOL), which avoid nullable fields.
NO_STATUS_CHANGE: Literal["NO_CHANGE"] = "NO_CHANGE"

StatusProgressionOrNoChange = Literal[
    "OPEN", "IN_PROGRESS", "PENDING_CUSTOMER", "ON_HOLD", "NO_CHANGE"
]


class StatusProgressionCheck(BaseModel):
    """Output contract for the status-progression classifier (see
    ticket_router.services.status_progression_service.check_status_progression)
    - decides whether the conversation so far indicates the ticket should
    move to a different mid-lifecycle status.
    """

    recommended_status: StatusProgressionOrNoChange
    reasoning: str = Field(min_length=1)


class SubmissionTypeResult(BaseModel):
    """Output contract for the submission-type classifier (see
    ticket_router.services.submission_type_service.classify_submission_type)
    - the first thing run on any raised submission, deciding whether it
    becomes a support ticket or a piece of customer feedback.
    """

    submission_type: SubmissionType
    reasoning: str = Field(min_length=1)


class FeedbackClassification(BaseModel):
    """The AI output contract for customer feedback (see
    ticket_router.services.feedback_classification_service.classify_feedback)
    - mirrors TicketRouteResult's shape/rationale, but for the feedback
    dimensions (sentiment/category/team/summary) rather than routing ones.
    `team` reuses the same AssignedTeam taxonomy as tickets, since it answers
    the same question ("which internal team should see this"), just for
    feedback instead of an actionable issue.
    """

    model_config = ConfigDict(populate_by_name=True)

    sentiment: FeedbackSentiment
    category: FeedbackCategory
    team: AssignedTeam = Field(alias="assignedTeam")
    # Same free-generated recurring-pattern label as TicketRouteResult.theme
    # (e.g. "UI Improvements", "Positive Experience") - shares the same
    # THEME RULES prompt guidance so themes can recur across both tickets
    # and feedback.
    theme: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    reasoning: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    model_used: str | None = Field(default=None, exclude=True)


class TicketRequest(BaseModel):
    message: str = Field(min_length=1)

    @field_validator("message")
    @classmethod
    def strip_and_require_nonempty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("message cannot be empty")
        return stripped
