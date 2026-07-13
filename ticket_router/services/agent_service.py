from functools import cache
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from ticket_router.ai.chat_llm import build_chat_llm
from ticket_router.errors import AIUnavailableError
from ticket_router.logger import logger
from ticket_router.models import AssignedTeam

SKILLS_DIR = Path(__file__).resolve().parent.parent.parent / "skills"

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


def chat_with_department(
    team: AssignedTeam,
    history: list[tuple[str, str]],
    message: str,
) -> str:
    """Sends one message to the conversational agent for `team`, grounded in
    that team's skills.md persona, plus the prior turns in `history`
    (list of (role, content) tuples where role is "user" or "assistant").
    Returns the agent's reply text.
    """
    skill_prompt = load_skill_prompt(team)
    llm = build_chat_llm()

    messages = [SystemMessage(content=skill_prompt)]
    for role, content in history:
        messages.append(
            HumanMessage(content=content) if role == "user" else AIMessage(content=content)
        )
    messages.append(HumanMessage(content=message))

    try:
        response = llm.invoke(messages)
    except Exception as error:  # noqa: BLE001 - surfaced to the UI as a clean AppError
        logger.error("Department agent chat call failed", {"team": team, "error": str(error)})
        raise AIUnavailableError(
            "The department agent is currently unavailable.", {"cause": str(error), "team": team}
        ) from error

    return response.content
