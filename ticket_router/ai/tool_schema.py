from typing import Any

from ticket_router.models import ASSIGNED_TEAMS, CATEGORIES, EMOTIONS, PRIORITIES

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
