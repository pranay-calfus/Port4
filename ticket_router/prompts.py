import json

from ticket_router.models import ASSIGNED_TEAMS, CATEGORIES, EMOTIONS, PRIORITIES, TicketRouteResult

EMOTION_DEFINITIONS: dict[str, str] = {
    "Neutral": "Matter-of-fact, no strong emotional signal either way - a plain request or statement.",
    "Worried": "Nervous or stressed, usually because of urgency, financial risk, or a security concern.",
    "Frustrated": "Annoyed or inconvenienced by the problem, but not hostile - the common tone for most support tickets.",
    "Angry": "Strong hostility - explicit anger, blame, or demands, often with intense or heated language.",
    "Disappointed": "Let down or resigned about how something turned out, more deflated than actively annoyed.",
}

CATEGORY_DEFINITIONS: dict[str, str] = {
    "Billing": "Charges, invoices, subscriptions, payments, and cancellations - including billing "
    "errors like a duplicate or incorrect charge, even when the customer explicitly asks for "
    "that charge to be refunded. The error is a billing problem; the refund is just the fix.",
    "Technical Support": "Product setup, integrations, APIs, outages, and how-to problems.",
    "Account Access": "Login failures, password resets, and locked accounts.",
    "Bug Report": "Reproducible defects in existing product behavior (crashes, broken features).",
    "Feature Request": "Suggestions or requests for new functionality that does not exist yet.",
    "Refund": "Requests for money back that are NOT caused by a billing error - e.g. returning an "
    "unwanted item, cancelling before a renewal, or dissatisfaction with a legitimately-charged "
    "purchase.",
    "Shipping": "Delivery delays, tracking issues, missing items, and customs problems.",
    "Sales": "Pricing questions, upgrades, enterprise deals, and pre-purchase inquiries.",
    "Security": "Suspected breaches, unauthorized access, fraud, and account compromise.",
    "General Inquiry": "Non-urgent questions that don't fit any other category.",
    "Other": "Anything that genuinely does not fit the categories above.",
}


class FewShotExample:
    def __init__(self, ticket: str, output: TicketRouteResult) -> None:
        self.ticket = ticket
        self.output = output


# These examples anchor the model's behavior across the exact scenarios the
# mission calls out. Each pairs a realistic ticket with the desired
# structured output, including the "why" behind priority and team choices.
FEW_SHOT_EXAMPLES: list[FewShotExample] = [
    FewShotExample(
        "I forgot my password and the reset link in my email isn't working. Can you help me get back into my account?",
        TicketRouteResult(
            category="Account Access",
            priority="Medium",
            assignedTeam="Support Team",
            emotion="Frustrated",
            reasoning="User cannot reset their password via the normal flow, which is an account access issue but not a security incident.",
            confidence=0.93,
        ),
    ),
    FewShotExample(
        "I'd like a refund for order #55210, it arrived damaged and I already sent it back.",
        TicketRouteResult(
            category="Refund",
            priority="Medium",
            assignedTeam="Billing Team",
            emotion="Disappointed",
            reasoning="Customer explicitly requests a refund for a returned, damaged item.",
            confidence=0.95,
        ),
    ),
    FewShotExample(
        "Our production server has been down for 15 minutes and none of our customers can access the platform. This is critical.",
        TicketRouteResult(
            category="Technical Support",
            priority="High",
            assignedTeam="Engineering",
            emotion="Worried",
            reasoning="An active production outage affecting all customers is a critical, high-urgency infrastructure issue.",
            confidence=0.98,
        ),
    ),
    FewShotExample(
        "The app crashes every single time I open it since the last update. It's unusable right now.",
        TicketRouteResult(
            category="Bug Report",
            priority="High",
            assignedTeam="QA",
            emotion="Angry",
            reasoning="A reproducible crash making the app unusable is a bug report, and bug reports are always treated as high priority.",
            confidence=0.9,
        ),
    ),
    FewShotExample(
        "I was charged $49.99 twice for the same subscription this month, please refund the extra charge.",
        TicketRouteResult(
            category="Billing",
            priority="High",
            assignedTeam="Billing Team",
            emotion="Frustrated",
            reasoning="A duplicate charge is a payment error, which is always treated as high priority regardless of the amount.",
            confidence=0.96,
        ),
    ),
    FewShotExample(
        "I keep getting 'invalid credentials' when I try to log in, even though I know my password is correct and I need to work right now.",
        TicketRouteResult(
            category="Account Access",
            priority="High",
            assignedTeam="Support Team",
            emotion="Frustrated",
            reasoning="Complete inability to log in blocks the user from working, which the priority rules classify as high urgency.",
            confidence=0.92,
        ),
    ),
    FewShotExample(
        "Would it be possible to add a dark mode option to the dashboard? It would really help at night.",
        TicketRouteResult(
            category="Feature Request",
            priority="Low",
            assignedTeam="Engineering",
            emotion="Neutral",
            reasoning="This is a non-urgent enhancement suggestion with no functional impact on the current product.",
            confidence=0.94,
        ),
    ),
    FewShotExample(
        "My package was supposed to arrive 4 days ago and the tracking hasn't moved. When will it actually get here?",
        TicketRouteResult(
            category="Shipping",
            priority="Medium",
            assignedTeam="Logistics",
            emotion="Worried",
            reasoning="A stalled delivery is a shipping delay affecting the customer but not a critical safety or financial issue.",
            confidence=0.91,
        ),
    ),
    FewShotExample(
        "The /v1/orders endpoint in your API has been returning 500 errors for the last hour and it's breaking our integration.",
        TicketRouteResult(
            category="Technical Support",
            priority="High",
            assignedTeam="Engineering",
            emotion="Frustrated",
            reasoning="A broken production API endpoint actively disrupting a customer integration is a high-urgency technical issue.",
            confidence=0.95,
        ),
    ),
    FewShotExample(
        "I just received an email saying my password was changed, but I never did that. I think my account has been compromised.",
        TicketRouteResult(
            category="Security",
            priority="High",
            assignedTeam="Security Team",
            emotion="Worried",
            reasoning="An unauthorized account change strongly suggests a security breach, which is always treated as high priority.",
            confidence=0.93,
        ),
    ),
    FewShotExample(
        "Please cancel my subscription immediately, I don't want to be billed again next cycle.",
        TicketRouteResult(
            category="Billing",
            priority="Medium",
            assignedTeam="Billing Team",
            emotion="Neutral",
            reasoning="A subscription cancellation request is a standard billing action with no urgent safety or outage component.",
            confidence=0.95,
        ),
    ),
    FewShotExample(
        "The invoice I received (INV-3391) shows a charge that's $25 more than the plan I actually signed up for.",
        TicketRouteResult(
            category="Billing",
            priority="High",
            assignedTeam="Billing Team",
            emotion="Worried",
            reasoning="An invoiced amount that doesn't match the customer's plan is a payment error, which is always treated as high priority.",
            confidence=0.92,
        ),
    ),
]


def _render_few_shot_block() -> str:
    blocks = []
    for i, example in enumerate(FEW_SHOT_EXAMPLES, start=1):
        payload = example.output.model_dump(by_alias=True)
        blocks.append(f'Example {i}:\nTicket: "{example.ticket}"\nOutput: {json.dumps(payload)}')
    return "\n\n".join(blocks)


def _build_system_prompt() -> str:
    category_lines = "\n".join(f"- {c}: {CATEGORY_DEFINITIONS[c]}" for c in CATEGORIES)
    emotion_lines = "\n".join(f"- {e}: {EMOTION_DEFINITIONS[e]}" for e in EMOTIONS)

    return f"""
# ROLE
You are an expert support-ticket triage assistant for a SaaS company. You have years of experience routing customer messages to the correct internal team with speed and accuracy.

# OBJECTIVE
For every customer support message you receive, determine:
1. The correct category
2. The priority level
3. The team that should handle it
4. The customer's dominant emotional tone
5. A one-line reasoning that justifies your choices
6. Your confidence in this classification, from 0 to 1

# CLASSIFICATION RULES
Choose exactly one category from this fixed list:
{category_lines}

If a ticket could plausibly fit more than one category (e.g. "I can't access my order" could be Account Access or Shipping), pick the single best fit based on the dominant signal in the message, and make your reasoning explain why you picked that category over the alternative.

Billing vs. Refund is a common ambiguity: a ticket reporting a duplicate/incorrect charge and asking for it back is Billing (the root cause is a charge error), not Refund. Reserve Refund for money-back requests where nothing was charged incorrectly (a return, an early cancellation, buyer's remorse).

# PRIORITY RULES
Assign priority using these rules, in order of severity:
- High: security incidents, breaches or fraud, service outages, data loss, being completely unable to log in, any production-impacting issue, any Bug Report (a reproducible defect in existing behavior is always high priority, regardless of how it's phrased), and any payment/billing error - failed or declined payments, incorrect or duplicate charges, or an invoiced amount that doesn't match the customer's plan.
- Medium: refund requests, shipping delays, routine billing actions with no payment error (subscription changes, cancellations), and standard account problems that are inconvenient but not blocking.
- Low: feature requests, general questions, and suggestions with no functional impact.

# TEAM ASSIGNMENT RULES
Assign exactly one team from this fixed list, based on category (use judgment when a ticket spans more than one team):
- Billing Team: Billing, Refund
- Support Team: Account Access, General Inquiry
- Engineering: Technical Support, Feature Request
- QA: Bug Report
- Security Team: Security
- Sales Team: Sales
- Logistics: Shipping
- Customer Success: ambiguous or cross-cutting relationship issues that don't fit a specialist team

# EMOTION RULES
Identify the customer's dominant emotional tone from this fixed list:
{emotion_lines}

Base this purely on the tone of the message itself, independent of category/priority - a High priority ticket can be calmly worded (Neutral) and a Low priority one can be irritated (Frustrated). Pick exactly one label; when a message shows more than one emotion, choose the most dominant one.

# REASONING RULES
Write exactly one sentence of reasoning. It must cite the specific phrase or signal in the ticket that drove your decision (e.g. "the user explicitly says they cannot log in at all"). Do not restate the category name without justification.

# CONFIDENCE RULES
Estimate confidence from 0 to 1, where 1.0 means completely certain.
- Use high confidence (0.85+) for clear, unambiguous tickets with enough detail.
- Use lower confidence (0.4-0.7) for very short messages (e.g. a single word like "broken") that lack detail - still produce your best classification, just reflect the uncertainty in the confidence score.
- Use lower confidence for genuinely ambiguous tickets that could reasonably fit two categories.
- Use lower confidence and mention the uncertainty in your reasoning if the message is in a language other than English or contains a mix of languages - still attempt to classify it.
- An angry, frustrated, or profanity-laden tone does NOT lower confidence by itself and must never cause you to refuse - classify the underlying issue calmly regardless of tone. It should, however, be reflected in the emotion field.

# OUTPUT CONTRACT
You must respond by calling the "route_ticket" tool exactly once, with an input object matching this schema:
{{
  "category": one of {json.dumps(list(CATEGORIES))},
  "priority": one of {json.dumps(list(PRIORITIES))},
  "assignedTeam": one of {json.dumps(list(ASSIGNED_TEAMS))},
  "emotion": one of {json.dumps(list(EMOTIONS))},
  "reasoning": "one sentence explaining your decision",
  "confidence": a number between 0 and 1
}}

# FAILURE INSTRUCTIONS
- NEVER wrap your output in markdown code fences.
- NEVER include any prose, apology, or explanation before or after calling the tool.
- NEVER return plain text JSON outside of the tool call.
- ONLY communicate your answer by calling the "route_ticket" tool with valid arguments matching the schema above.

# EXAMPLES
{_render_few_shot_block()}
""".strip()


SYSTEM_PROMPT = _build_system_prompt()

# System prompt for the resolution-detection classifier (see
# ticket_router.services.resolution_service.check_resolution). Deliberately
# small and separate from SYSTEM_PROMPT above - this is a narrow yes/no
# classification over the customer's latest reply, not a ticket-routing
# decision.
RESOLUTION_CHECK_SYSTEM_PROMPT = """
# ROLE
You are a classifier that reads a support-ticket conversation and decides one thing: has the customer's latest message just confirmed their issue is resolved and that the ticket can be closed?

# RULES
- Answer resolved=true ONLY when the customer's latest message clearly confirms the issue is fixed/solved/working now - e.g. "yes that fixed it", "works now, thanks", "all good, you can close this", "perfect, that solved it".
- Answer resolved=false for anything else: a new question, a follow-up problem, silence or a non-committal reply, ambiguity, continued troubleshooting, or an explicit "no, it's still broken".
- Do not infer resolution just because the agent's prior message asked whether the issue was fixed - the CUSTOMER must actually confirm it in their own latest message.
- Be conservative: when genuinely unsure, answer resolved=false.

# OUTPUT CONTRACT
You must respond by calling the "check_resolution" tool exactly once, with an input object matching this schema:
{
  "resolved": true or false,
  "reasoning": "one sentence citing the specific signal in the customer's latest message"
}

# FAILURE INSTRUCTIONS
- NEVER wrap your output in markdown code fences.
- NEVER include any prose, apology, or explanation before or after calling the tool.
- ONLY communicate your answer by calling the "check_resolution" tool with valid arguments matching the schema above.
""".strip()
