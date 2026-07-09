# Smart Support Ticket Router

An AI-powered support ticket triage system. Paste any customer support message and get back a structured, always-valid classification: **category**, **priority**, **assigned team**, **one-line reasoning**, and a **confidence score** — in seconds instead of minutes.

A single Python process: [Streamlit](https://streamlit.io) for the UI, [Groq](https://groq.com) (via its OpenAI-compatible API) for classification, and [Pydantic](https://docs.pydantic.dev) for strict validation, with automatic retries and JSON repair guaranteeing the app never crashes and never shows malformed data.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Getting a Groq API Key](#getting-a-groq-api-key)
- [Installation](#installation)
- [Environment Variables](#environment-variables)
- [Running the App](#running-the-app)
- [The Reusable Routing Function](#the-reusable-routing-function)
- [Prompt Engineering](#prompt-engineering)
- [JSON Reliability & Validation](#json-reliability--validation)
- [Retry Strategy](#retry-strategy)
- [Model Fallback](#model-fallback)
- [Edge Cases](#edge-cases)
- [Sample Tickets & Demo Mode](#sample-tickets--demo-mode)
- [Manual vs. AI Time Comparison](#manual-vs-ai-time-comparison)
- [Model Used](#model-used)
- [Testing](#testing)
- [Code Quality](#code-quality)
- [Screenshots](#screenshots)

## Overview

Support teams spend a meaningful amount of time simply _sorting_ incoming tickets before anyone starts solving them. This project automates that sorting step: it takes raw, unstructured ticket text and returns a structured routing decision that a real support desk could act on immediately — with the reasoning included, so a human can verify it at a glance.

## Architecture

```
smart-ticket-router (repo root)
├── app.py                     Streamlit entrypoint - Router tab + Demo Mode tab
├── ticket_router/             the reusable package
│   ├── config.py              env loading (GROQ_API_KEY, GROQ_MODEL)
│   ├── models.py              Pydantic models: TicketRouteResult, TicketRequest, enums
│   ├── errors.py              AppError hierarchy (ValidationError, AIUnavailableError, AIResponseError)
│   ├── logger.py              structured JSON logging
│   ├── prompts.py             system prompt + 12 few-shot examples
│   ├── ai/
│   │   ├── base.py             AIProvider Protocol
│   │   └── groq_provider.py    the app's only AI provider (Groq via the `openai` SDK)
│   ├── services/
│   │   ├── json_repair.py      code-fence stripping / brace extraction / trailing-comma fixes
│   │   ├── prompt_service.py   truncation + error summarizing
│   │   └── ticket_routing_service.py   the reusable route_ticket() function - retry/repair orchestration
│   └── ui/
│       ├── theme.py            dark, sleek custom CSS
│       ├── components.py       result card, comparison section, demo progress dots
│       ├── html.py             HTML-in-Markdown rendering helper
│       └── sample_tickets.py   loads sample-tickets/tickets.json
├── sample-tickets/            20 realistic tickets (source of truth for the example dropdown + Demo Mode)
├── tests/                     pytest suite (validation + retry/edge-case tests, mocked AI provider)
└── docs/                      AI-Concepts.md (plain-English explanation for reviewers/mentors)
```

The AI layer sits behind an `AIProvider` [Protocol](ticket_router/ai/base.py) implemented by [`GroqProvider`](ticket_router/ai/groq_provider.py), the app's only AI provider — this is what lets tests inject a fake provider instead of making real network calls.

## Getting a Groq API Key

1. Create a free account at [console.groq.com](https://console.groq.com).
2. Open **API Keys** in the console and create a new key.
3. Copy it into `GROQ_API_KEY` in `.env` (see [Environment Variables](#environment-variables)). Never commit this key.

## Installation

Requires Python 3.11+.

```bash
git clone <this-repo>
cd smart-ticket-router
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt   # or requirements.txt for a runtime-only install
cp .env.example .env
```

Edit `.env` and set your `GROQ_API_KEY`.

## Environment Variables

`.env`:

```env
GROQ_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile
# GROQ_FALLBACK_MODELS=llama-3.1-8b-instant,meta-llama/llama-4-scout-17b-16e-instruct
```

| Variable | Description | Default |
|---|---|---|
| `GROQ_API_KEY` | Your Groq API key (see [Getting a Groq API Key](#getting-a-groq-api-key)) | — |
| `GROQ_MODEL` | Groq model id | `llama-3.3-70b-versatile` |
| `GROQ_FALLBACK_MODELS` | Optional comma-separated override for the fallback chain (see [Model Fallback](#model-fallback)) | built-in default chain |

**No API key is ever hardcoded.** If `GROQ_API_KEY` is missing, the app still boots - the UI loads and the "Try an example" dropdown works, but clicking "Route Ticket" surfaces a clean, specific error (`AI_UNAVAILABLE`) instead of crashing.

## Running the App

```bash
source .venv/bin/activate
streamlit run app.py
```

Opens at `http://localhost:8501`. The app has two tabs, both in the same process:

- **Router** — paste a ticket, pick an example, or edit one, then click "Route Ticket".
- **Demo Mode** — step through all 20 sample tickets one at a time (or click "Run Full Demo" to classify all 20 in one pass) - built for walking a mentor through the system quickly.

## The Reusable Routing Function

Per the mission's "build a reusable function/service" requirement, every code path - the Router tab, Demo Mode, and the test suite - calls the exact same function:

```python
from ticket_router.services.ticket_routing_service import route_ticket

result = route_ticket("I was charged twice for my subscription this month.")
print(result.model_dump(by_alias=True))
# {'category': 'Billing', 'priority': 'Medium', 'assignedTeam': 'Billing Team',
#  'reasoning': '...', 'confidence': 0.95}
```

It also works as a quick CLI smoke test:

```bash
python -m ticket_router.services.ticket_routing_service "The app keeps crashing on launch."
```

## Prompt Engineering

The system prompt ([`ticket_router/prompts.py`](ticket_router/prompts.py)) is structured into explicit sections: role, objective, classification rules for all 11 categories, priority rules, team-assignment rules, reasoning rules, confidence rules, the output contract, and hard failure instructions ("never markdown, never prose, only call the tool"). It's reinforced with 12 few-shot examples covering password resets, refunds, outages, crashes, duplicate charges, login failures, feature requests, shipping delays, broken APIs, security breaches, cancellations, and invoice issues. See [docs/AI-Concepts.md](docs/AI-Concepts.md) for the full rationale.

## JSON Reliability & Validation

Six layers of defense guarantee the app always ends up with valid, schema-conforming data:

1. **Prompt engineering** — the system prompt above.
2. **Forced structured output** — Groq's OpenAI-compatible Chat Completions API is called with a `route_ticket` function tool and `tool_choice` forcing that exact tool call, so the model cannot reply with free text.
3. **Pydantic validation** — every result is parsed and validated against [`ticket_router/models.py`](ticket_router/models.py)'s `TicketRouteResult`, regardless of how it arrived.
4. **Automatic single retry** — on validation failure, the AI is called again with the error appended as context.
5. **JSON repair** — [`ticket_router/services/json_repair.py`](ticket_router/services/json_repair.py) strips code fences, extracts the first balanced `{...}` block, and fixes trailing commas, for the case the model's tool-call arguments aren't clean JSON.
6. **Graceful failure** — if all else fails, a typed `AIResponseError` is raised and the Streamlit UI shows a clean error message. **The app never crashes.**

## Retry Strategy

[`ticket_router/services/ticket_routing_service.py`](ticket_router/services/ticket_routing_service.py) implements the full pipeline: call → parse/validate (with repair fallback) → (if invalid) retry once with error context → parse/validate again → (if still invalid) raise a typed error. This is a single bounded retry, not an unbounded loop, keeping latency and cost predictable.

## Model Fallback

Retries alone don't help if the configured model itself is unavailable (Groq's free tier has fairly low per-model rate limits, and models occasionally get decommissioned or hit transient 5xx errors). [`ticket_router/ai/groq_provider.py`](ticket_router/ai/groq_provider.py) handles this at the model level, independently of the validation retry above.

`GROQ_MODEL` is tried first, then every other model currently on Groq is tried in turn, explicitly listed in [`DEFAULT_FALLBACK_MODELS`](ticket_router/ai/groq_provider.py) - general-purpose instruct/chat models first (most likely to succeed), moderation-only and agentic models last (included for completeness, but less likely to behave like a plain forced-tool-call model):

```
llama-3.3-70b-versatile (primary)
  → llama-3.1-8b-instant
  → meta-llama/llama-4-scout-17b-16e-instruct
  → openai/gpt-oss-120b
  → openai/gpt-oss-20b
  → qwen/qwen3-32b
  → qwen/qwen3.6-27b
  → allam-2-7b
  → openai/gpt-oss-safeguard-20b
  → groq/compound
  → groq/compound-mini
  → meta-llama/llama-prompt-guard-2-22m
  → meta-llama/llama-prompt-guard-2-86m
```

- On failure (rate limit, timeout, 5xx, or a response with no tool call), it automatically falls through to the next model in the chain above. Override the whole chain with `GROQ_FALLBACK_MODELS` in `.env` if you want a different list or order.
- **Authentication/permission errors fail fast** without burning the rest of the chain - a bad API key fails identically on every model, so there's no point retrying it thirteen times.
- If every model in the chain fails, a single `AIUnavailableError` is raised listing every model attempted.

## Edge Cases

| Case | Behavior |
|---|---|
| Angry / profanity-laden message | Classified normally; the model is instructed to never refuse based on tone. |
| Very short message (e.g. `"broken"`) | Still classified, with a lower confidence score - the UI shows an explicit "low confidence, consider manual review" banner below 65%. |
| Ambiguous message (e.g. `"I can't access my order"`) | Classified into the best-fit category, with reasoning that explains the choice over the alternative. |
| Empty input | Rejected with a clear inline message before any AI call is made. |
| Very long message | Truncated to 8,000 characters before being sent to the AI (`MAX_TICKET_LENGTH` in `ticket_router/models.py`). |
| Non-English message | Still classified, with lower confidence and a note of uncertainty in the reasoning. |

## Sample Tickets & Demo Mode

[`sample-tickets/tickets.json`](sample-tickets/tickets.json) contains 20 realistic tickets spanning all 11 categories. This file is the single source of truth for both the **example ticket dropdown** on the Router tab and **Demo Mode**, which steps through all 20 tickets (one at a time, or all at once via "Run Full Demo") showing the input, the AI's structured output, and the measured processing time for each.

## Manual vs. AI Time Comparison

The comparison panel on the Router tab starts with an illustrative "~2 sec" AI estimate against a documented 2-minute manual-triage baseline, but it upgrades to real evidence as you use the app:

- **AI side**: the moment you route a real ticket, the AI number switches to your session's actual average `processingTime` (in ms), plus a running "time saved so far" total.
- **Manual side**: click **"Start Manual Timer"** in the "Manual Routing" panel, pick a category/priority/team yourself the way a human triager would, then **"Submit Manual Routing"** to stop the clock. That measured time (not the 2-minute assumption) becomes the manual baseline for the comparison above, until you reset it.

Both sides are real, timed evidence for the same ticket, not static claims.

## Model Used

Every result card shows a **"Routed via `<model>`"** pill next to the processing time, naming whichever Groq model actually produced that classification. Normally that's `GROQ_MODEL`, but if the [model fallback](#model-fallback) chain kicked in, it names the fallback model instead - so it's always visible which model is responsible for a given result, not just that "the AI" answered.

## Testing

```bash
source .venv/bin/activate
pytest -v
```

24 tests across three files, run against a fake AI provider (no live API calls):

- `tests/test_validation.py` — 10 consecutive tests asserting `TicketRouteResult` accepts well-formed AI output and rejects malformed output (missing fields, invalid enums, out-of-range confidence, wrong types).
- `tests/test_retry.py` — empty-input rejection, JSON repair (code fences, trailing commas, prose-wrapped JSON), the single-retry-then-succeed path, the both-attempts-fail path, and the AI-unavailable path.
- `tests/test_groq_fallback.py` — falling back to the next model on an API error, falling back when a model returns no tool call, exhausting the whole chain, failing fast on an authentication error, and succeeding on the primary model without falling back at all.

## Code Quality

```bash
ruff check .      # lint
black .           # format
```

Strict Pydantic models, typed exceptions, PEP 8-conformant naming (`assigned_team` internally, aliased to `assignedTeam` on the wire to match the tool schema), and no hardcoded secrets anywhere in source.

## Screenshots

_Add screenshots of the Router tab, a result card, and Demo Mode to `screenshots/` and reference them here, e.g.:_

```markdown
![Main UI](screenshots/main-ui.png)
![Demo Mode](screenshots/demo-mode.png)
```
