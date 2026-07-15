from typing import Any

from ticket_router.models import ASSIGNED_TEAMS, CATEGORIES, EMOTIONS, PRIORITIES

ROUTE_TICKET_TOOL_NAME = "route_ticket"

# Forcing the model to call this tool is our primary structured-output
# guarantee (Layer 2 of JSON reliability, see docs/AI-Concepts.md), shared
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
