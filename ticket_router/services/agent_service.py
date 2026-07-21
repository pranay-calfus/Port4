from functools import cache
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from ticket_router.ai.chat_llm import build_chat_llm
from ticket_router.errors import AIUnavailableError
from ticket_router.logger import logger
from ticket_router.models import AssignedTeam

SKILLS_DIR = Path(__file__).resolve().parent.parent.parent / "skills"

# System prompt for the first-line chatbot a user talks to before any
# department/ticket exists yet - see backend/routers/chat.py. It tries to
# help directly and only ever suggests escalating to a ticket; it never
# claims to have created one, since ticket creation is a separate,
# explicit user action (POST /chat/escalate).
GENERAL_SUPPORT_SYSTEM_PROMPT = (
    "You are the first-line support assistant for a product support desk. "
    "Help the user resolve their issue directly using general troubleshooting "
    "knowledge and common sense. Be concise and concrete. If the issue needs "
    "a human specialist, account-specific action, or you cannot resolve it "
    "in this conversation, tell the user clearly and suggest they create a "
    "support ticket - but never claim to have created one yourself; you have "
    "no ability to do that."
)

# Maps each assigned team to the skills.md file that defines its
# conversational agent's persona, tone, and scope. One file per department -
# see skills/*.md.
TEAM_SKILL_FILES: dict[str, str] = {
    "Billing Team": "billing_team.md",
    "Support Team": "support_team.md",
    "Engineering": "engineering.md",
    "QA": "qa.md",
    "Security Team": "security_team.md",
    "Sales Team": "sales_team.md",
    "Logistics": "logistics.md",
    "Customer Success": "customer_success.md",
}


@cache
def load_skill_prompt(team: AssignedTeam) -> str:
    """Reads the department's skills.md file and returns its content
    verbatim, used as the system prompt for that department's
    conversational agent. Cached since the file content is static for the
    life of the process.
    """
    filename = TEAM_SKILL_FILES.get(team)
    if filename is None:
        raise ValueError(f"No skills.md mapping for team: {team!r}")

    path = SKILLS_DIR / filename
    return path.read_text(encoding="utf-8")


def _run_chat(
    system_prompt: str, history: list[tuple[str, str]], message: str, *, log_context: dict
) -> str:
    llm = build_chat_llm()

    messages = [SystemMessage(content=system_prompt)]
    for role, content in history:
        messages.append(
            HumanMessage(content=content) if role == "user" else AIMessage(content=content)
        )
    messages.append(HumanMessage(content=message))

    try:
        response = llm.invoke(messages)
    except Exception as error:  # noqa: BLE001 - surfaced to the caller as a clean AppError
        logger.error("Chat agent call failed", {**log_context, "error": str(error)})
        raise AIUnavailableError(
            "The chat agent is currently unavailable.", {"cause": str(error), **log_context}
        ) from error

    return response.content


# Appended to every department persona's system prompt so the bot
# proactively checks in on resolution once it believes the issue is
# handled - this is what gives the customer a natural moment to confirm,
# which backend.services.ticket_service's post-reply resolution check (see
# ticket_router.services.resolution_service.check_resolution) then detects
# to auto-close the ticket.
_RESOLUTION_CHECK_NUDGE = (
    "\n\n# CLOSING THE LOOP\n"
    "Once you believe you have fully addressed the customer's issue, explicitly ask them to "
    "confirm whether it's resolved and whether this ticket can be closed. Do not ask on every "
    "turn - only once, after you think the issue is actually handled."
)

# Appended on top of _RESOLUTION_CHECK_NUDGE, one entry per mid-lifecycle
# status - nudges the persona to ask the specific follow-up question that
# would let backend.services.ticket_service's status-progression classifier
# (ticket_router.services.status_progression_service.check_status_progression)
# detect the ticket is ready to move forward. Keyed by the ticket's current
# status so the question actually fits where the conversation is.
_STATUS_PROGRESSION_NUDGES: dict[str, str] = {
    "OPEN": (
        "The customer's issue has just come in. Ask whatever clarifying questions you need to "
        "fully understand the problem before proposing a fix."
    ),
    "IN_PROGRESS": (
        "You are actively working this issue. Ask whether the customer has tried any suggested "
        "steps yet, and whether the issue is still occurring."
    ),
    "PENDING_CUSTOMER": (
        "You are waiting on the customer. Be specific about exactly what information or "
        "confirmation you still need from them."
    ),
    "ON_HOLD": (
        "This ticket is on hold pending something on your side (an internal team, an "
        "escalation, or a blocker). Let the customer know you're following up internally and "
        "give them a sense of what you're waiting on."
    ),
}


def _status_progression_nudge(current_status: str | None) -> str:
    guidance = _STATUS_PROGRESSION_NUDGES.get(current_status or "")
    if guidance is None:
        return ""
    return "\n\n# MOVING THIS TICKET FORWARD\n" + guidance


def chat_with_department(
    team: AssignedTeam,
    history: list[tuple[str, str]],
    message: str,
    current_status: str | None = None,
) -> str:
    """Sends one message to the conversational agent for `team`, grounded in
    that team's skills.md persona (plus a shared nudge to check in on
    resolution, see _RESOLUTION_CHECK_NUDGE, and - when `current_status` is
    given - a status-specific nudge to ask the right follow-up question, see
    _STATUS_PROGRESSION_NUDGES), plus the prior turns in `history` (list of
    (role, content) tuples where role is "user" or "assistant"). Returns the
    agent's reply text.

    `current_status` is only meaningful once a real ticket exists (it's
    omitted for the pre-ticket chat flow, which has no status yet).
    """
    system_prompt = (
        load_skill_prompt(team) + _RESOLUTION_CHECK_NUDGE + _status_progression_nudge(current_status)
    )
    return _run_chat(
        system_prompt, history, message, log_context={"team": team, "status": current_status}
    )


def chat_with_general_agent(history: list[tuple[str, str]], message: str) -> str:
    """Sends one message to the pre-ticket, first-line support agent (no
    department assigned yet) - see GENERAL_SUPPORT_SYSTEM_PROMPT. Used by
    the chat flow before a conversation is escalated into a ticket.
    """
    return _run_chat(GENERAL_SUPPORT_SYSTEM_PROMPT, history, message, log_context={"team": None})
