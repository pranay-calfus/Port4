from typing import Any

from ticket_router.models import (
    ASSIGNED_TEAMS,
    CATEGORIES,
    EMOTIONS,
    FEEDBACK_CATEGORIES,
    FEEDBACK_SENTIMENTS,
    PRIORITIES,
    STATUS_PROGRESSIONS,
    SUBMISSION_TYPES,
)

ROUTE_TICKET_TOOL_NAME = "route_ticket"

# Forcing the model to call this tool is our primary structured-output
# guarantee (see "AI Reliability, Layer by Layer" in the README), shared
# by every model in OpenAIProvider's fallback chain.
ROUTE_TICKET_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": ROUTE_TICKET_TOOL_NAME,
        "description": "Classify a support ticket and return the routing decision.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "enum": list(CATEGORIES)},
                "priority": {"type": "string", "enum": list(PRIORITIES)},
                "assignedTeam": {"type": "string", "enum": list(ASSIGNED_TEAMS)},
                "emotion": {
                    "type": "string",
                    "enum": list(EMOTIONS),
                    "description": "The customer's dominant emotional tone in the message.",
                },
                "theme": {
                    "type": "string",
                    "description": (
                        "A short (2-4 word) label for the recurring problem/topic pattern this "
                        "ticket belongs to, distinct from category - e.g. 'Login Issues', "
                        "'Payment Failure'. Not restricted to a fixed list, but prefer general, "
                        "reusable phrasing over hyper-specific one-off wording."
                    ),
                },
                "reasoning": {
                    "type": "string",
                    "description": "One sentence justifying the decision, citing a specific signal from the ticket.",
                },
                "confidence": {"type": "number", "description": "A number between 0 and 1."},
            },
            "required": [
                "category",
                "priority",
                "assignedTeam",
                "emotion",
                "theme",
                "reasoning",
                "confidence",
            ],
            "additionalProperties": False,
        },
    },
}

CHECK_RESOLUTION_TOOL_NAME = "check_resolution"

# Forced tool call backing the resolution-detection classifier (see
# ticket_router.services.resolution_service) - lets the department bot
# notice when a customer confirms their issue is fixed and autonomously
# close the ticket, the same outcome a human admin gets from the
# accept-solution flow.
CHECK_RESOLUTION_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": CHECK_RESOLUTION_TOOL_NAME,
        "description": (
            "Decide whether the customer's latest message confirms their issue is now "
            "resolved and the support ticket can be closed."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "resolved": {
                    "type": "boolean",
                    "description": (
                        "True only if the customer's latest message explicitly confirms the "
                        "issue is fixed/working and agrees (or does not object) to closing the "
                        "ticket. False for anything else, including silence, a new question, "
                        "or continued troubleshooting."
                    ),
                },
                "reasoning": {
                    "type": "string",
                    "description": "One sentence citing the specific signal in the message.",
                },
            },
            "required": ["resolved", "reasoning"],
            "additionalProperties": False,
        },
    },
}

CHECK_STATUS_PROGRESSION_TOOL_NAME = "check_status_progression"

# Forced tool call backing the status-progression classifier (see
# ticket_router.services.status_progression_service) - lets the department
# bot notice when the conversation clearly indicates the ticket should move
# to a different mid-lifecycle status, and autonomously advance it, the same
# way CHECK_RESOLUTION_TOOL lets it auto-close.
CHECK_STATUS_PROGRESSION_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": CHECK_STATUS_PROGRESSION_TOOL_NAME,
        "description": (
            "Decide whether the conversation so far indicates this ticket should move to a "
            "different status, and explain why."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "recommended_status": {
                    "type": "string",
                    "enum": [*STATUS_PROGRESSIONS, "NO_CHANGE"],
                    "description": (
                        "The ticket's next status given the conversation, or NO_CHANGE if "
                        "nothing has shifted enough yet to justify moving it."
                    ),
                },
                "reasoning": {
                    "type": "string",
                    "description": "One sentence citing the specific signal that drove this decision.",
                },
            },
            "required": ["recommended_status", "reasoning"],
            "additionalProperties": False,
        },
    },
}

CLASSIFY_SUBMISSION_TYPE_TOOL_NAME = "classify_submission_type"

# Forced tool call backing the first classifier run on any raised
# submission (see ticket_router.services.submission_type_service) - decides
# whether the submission is a Support Issue (should become a ticket) or
# Customer Feedback (should not).
CLASSIFY_SUBMISSION_TYPE_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": CLASSIFY_SUBMISSION_TYPE_TOOL_NAME,
        "description": (
            "Classify whether a customer submission is a support issue that needs "
            "resolution, or unsolicited customer feedback."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "submission_type": {
                    "type": "string",
                    "enum": list(SUBMISSION_TYPES),
                    "description": (
                        "SUPPORT_ISSUE for a problem, request, question, or complaint that "
                        "needs individual resolution. CUSTOMER_FEEDBACK for commentary, "
                        "opinion, praise, or a suggestion with no expectation of individual "
                        "resolution."
                    ),
                },
                "reasoning": {
                    "type": "string",
                    "description": "One sentence citing the specific signal that drove this decision.",
                },
            },
            "required": ["submission_type", "reasoning"],
            "additionalProperties": False,
        },
    },
}

CLASSIFY_FEEDBACK_TOOL_NAME = "classify_feedback"

# Forced tool call backing the feedback classifier (see
# ticket_router.services.feedback_classification_service) - the same
# forced-tool-call shape as ROUTE_TICKET_TOOL, but for the feedback
# dimensions (sentiment/category/team/summary) instead of routing ones.
CLASSIFY_FEEDBACK_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": CLASSIFY_FEEDBACK_TOOL_NAME,
        "description": "Classify a piece of customer feedback and summarize it.",
        "parameters": {
            "type": "object",
            "properties": {
                "sentiment": {"type": "string", "enum": list(FEEDBACK_SENTIMENTS)},
                "category": {"type": "string", "enum": list(FEEDBACK_CATEGORIES)},
                "assignedTeam": {
                    "type": "string",
                    "enum": list(ASSIGNED_TEAMS),
                    "description": "The internal team this feedback is most relevant to.",
                },
                "theme": {
                    "type": "string",
                    "description": (
                        "A short (2-4 word) label for the recurring problem/topic pattern this "
                        "feedback belongs to, distinct from category - e.g. 'UI Improvements', "
                        "'Positive Experience'. Not restricted to a fixed list, but prefer "
                        "general, reusable phrasing over hyper-specific one-off wording."
                    ),
                },
                "summary": {
                    "type": "string",
                    "description": "A one-sentence AI-generated summary of the feedback.",
                },
                "reasoning": {
                    "type": "string",
                    "description": "One sentence justifying the sentiment/category/team choices.",
                },
                "confidence": {"type": "number", "description": "A number between 0 and 1."},
            },
            "required": [
                "sentiment",
                "category",
                "assignedTeam",
                "theme",
                "summary",
                "reasoning",
                "confidence",
            ],
            "additionalProperties": False,
        },
    },
}
