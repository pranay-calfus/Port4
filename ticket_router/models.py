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
ASSIGNED_TEAMS: tuple[str, ...] = AssignedTeam.__args__

# Hard cap on ticket length. Anything longer is truncated (not rejected)
# before being sent to the AI - see services/prompt_service.py.
MAX_TICKET_LENGTH = 8000


class TicketRouteResult(BaseModel):
    """The AI output contract. This mirrors the Groq tool's own `parameters`
    JSON schema exactly - it is the second line of defense (Layer 3 of JSON
    reliability) after Groq's forced tool call, guarding against enum
    drift, wrong types, or a malformed tool call. `assigned_team` uses a
    camelCase alias so the wire format matches the tool schema while the
    Python attribute stays snake_case/PEP 8.
    """

    model_config = ConfigDict(populate_by_name=True)

    category: Category
    priority: Priority
    assigned_team: AssignedTeam = Field(alias="assignedTeam")
    reasoning: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)


class TicketRequest(BaseModel):
    message: str = Field(min_length=1)

    @field_validator("message")
    @classmethod
    def strip_and_require_nonempty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("message cannot be empty")
        return stripped
