"""Pydantic request/response models for the backend API. Category/priority/
department fields reuse the existing ticket_router.models Literals so
there's exactly one place that defines the valid category/priority/team
values.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from backend.models import Role, SenderType, TicketStatus
from ticket_router.models import AssignedTeam, Priority

# --- Auth -------------------------------------------------------------


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)


class AdminCreateRequest(BaseModel):
    # Used by a super-admin (department is None) to provision a new team
    # account from the UI, in place of the old backend/create_admin.py CLI.
    # Omitting department creates another super-admin.
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    department: AssignedTeam | None = None


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
    # suggestion (which is still recorded separately as ai_priority).
    priority: Priority | None = None

    @field_validator("history")
    @classmethod
    def require_at_least_one_user_turn(cls, value: list[ChatTurn]) -> list[ChatTurn]:
        if not any(turn.role == "user" for turn in value):
            raise ValueError("cannot escalate an empty conversation")
        return value


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
    ai_category: str | None
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


class StatusUpdateRequest(BaseModel):
    status: TicketStatus


class AssignRequest(BaseModel):
    admin_id: int


class ReassignRequest(BaseModel):
    department: AssignedTeam | None = None
    priority: Priority | None = None


class UpdatePriorityRequest(BaseModel):
    priority: Priority
