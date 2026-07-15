# Port4 — AI-Powered Ticket Management System

An AI-powered support ticket system: a customer chats with a first-line bot first; if it can't resolve the issue, the conversation escalates into a real ticket, which the AI automatically classifies (category, priority, department, summary, confidence). From there the ticket moves through a full lifecycle - triage, assignment, replies, resolution, customer acceptance - tracked with a persisted message thread and audit trail, behind real user/admin authentication.

A FastAPI backend is the single source of truth (auth, tickets, messages, activity log, AI orchestration); a single Streamlit app is a thin HTTP client of it, with one landing page offering a Customer login/register tab and an Admin login tab - after logging in, the app renders the matching dashboard for that account's role.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Getting API Keys](#getting-api-keys)
- [Installation](#installation)
- [Environment Variables](#environment-variables)
- [Running the App](#running-the-app)
- [Authentication & Roles](#authentication--roles)
- [Ticket Lifecycle](#ticket-lifecycle)
- [AI Chatbot & Escalation Flow](#ai-chatbot--escalation-flow)
- [API Overview](#api-overview)
- [The Reusable Routing Function](#the-reusable-routing-function)
- [Prompt Engineering](#prompt-engineering)
- [JSON Reliability & Validation](#json-reliability--validation)
- [Retry Strategy](#retry-strategy)
- [Model Fallback](#model-fallback)
- [Department Agents & skills.md](#department-agents--skillsmd)
- [Edge Cases](#edge-cases)
- [Testing](#testing)
- [Code Quality](#code-quality)
- [Screenshots](#screenshots)

## Overview

Support teams spend a meaningful amount of time simply _sorting_ incoming tickets before anyone starts solving them. The AI layer automates that sorting step: it takes a chat conversation the bot couldn't resolve and returns a structured routing decision - category, priority, assigned department, and a one-line reasoning a human can audit at a glance - the moment a ticket is created. Everything after that (assignment, status, replies, resolution) is a normal ticket-management workflow with real accounts and role-based access control.

## Architecture

```
Port4 (repo root)
├── backend/                    FastAPI service - the single source of truth
│   ├── main.py                  app assembly, CORS, startup DB init
│   ├── db.py                    SQLAlchemy engine/session (SQLite by default)
│   ├── models.py                ORM: User, Ticket, TicketMessage, TicketActivity
│   ├── schemas.py                Pydantic request/response models
│   ├── auth.py                   bcrypt hashing, JWT issue/verify, role guards
│   ├── create_admin.py           CLI to provision admin accounts (no self-service admin signup)
│   ├── routers/                  auth.py, tickets.py, admin.py, chat.py
│   └── services/
│       └── ticket_service.py     status transitions + activity logging; calls into
│                                  ticket_router's AI pipeline, unchanged
├── frontend/
│   ├── api_client.py             httpx client + persistent-login (query-param token) helpers
│   └── app.py                     single entry point: landing page (Customer/Admin login),
│                                    then the chat+ticket dashboard or the admin queue+metrics
│                                    dashboard depending on the logged-in account's role
├── ticket_router/                the reusable AI package (unchanged in behavior)
│   ├── config.py                  env loading (API keys/models, DATABASE_URL, JWT settings)
│   ├── models.py                  Pydantic models: TicketRouteResult, TicketRequest, enums
│   ├── errors.py                  AppError hierarchy (ValidationError, AIUnavailableError, AIResponseError)
│   ├── logger.py                  structured JSON logging
│   ├── prompts.py                 system prompt + 12 few-shot examples for ticket classification
│   ├── ai/
│   │   ├── base.py                 AIProvider Protocol
│   │   ├── tool_schema.py          the shared route_ticket function-calling schema
│   │   ├── openai_provider.py      the only provider - LangChain's ChatOpenAI, forced tool call, model fallback chain
│   │   └── chat_llm.py             free-form conversational LLM (LangChain `.with_fallbacks()`) for chat agents
│   ├── services/
│   │   ├── json_repair.py          code-fence stripping / brace extraction / trailing-comma fixes
│   │   ├── prompt_service.py       truncation + error summarizing
│   │   ├── ticket_routing_service.py  the reusable route_ticket() function - retry/repair orchestration
│   │   └── agent_service.py        drives the pre-ticket general chat agent and the per-department agents
│   └── ui/                        theme.py (dark CSS), components.py (AI result card, priority hint),
│                                    sample_tickets.py (loads sample-tickets/tickets.json)
├── sample-tickets/tickets.json  20 example tickets - the "Try an example" dropdown in the Chat tab
├── skills/                     one skills.md per department (Billing, Support, Engineering, QA, Security, Sales, Logistics, Customer Success)
├── tests/
│   ├── backend/                 FastAPI TestClient tests: auth, ticket lifecycle, admin, chat/escalation
│   └── test_validation.py, test_retry.py, test_openai_provider.py   AI-layer tests (unchanged, mocked provider)
└── docs/                       AI-Concepts.md (plain-English explanation of the AI layer)
```

The AI layer sits behind an `AIProvider` [Protocol](ticket_router/ai/base.py), unchanged from before: `route_ticket()` calls [`OpenAIProvider`](ticket_router/ai/openai_provider.py) by default, which lets tests inject a fake provider instead of making real network calls. Both the routing provider and the chat agents are orchestrated through [LangChain](https://python.langchain.com) (`ChatOpenAI`).

**Role gating**: `frontend/app.py` decides what to render purely from the logged-in account's role (`USER` vs `ADMIN`, returned by the backend) - a customer session never renders admin controls and vice versa. The backend also enforces this independently (every `/admin/*` route requires an `ADMIN`-role token), so the UI branch is a convenience, not the only guard.

**Session persistence**: the JWT is mirrored into the page's URL query params on login (and cleared on logout), so a browser refresh restores the session via `GET /auth/me` instead of forcing a re-login.

## Getting API Keys

**OpenAI (the only provider):**

1. Create an account at [platform.openai.com](https://platform.openai.com).
2. Open **API Keys** and create a new key.
3. Copy it into `OPENAI_API_KEY` in `.env` (see [Environment Variables](#environment-variables)). Never commit this key.

Without `OPENAI_API_KEY` set, the backend still boots - registration, login, and ticket browsing all work, but escalating a chat to a ticket surfaces a clean `AI_UNAVAILABLE` error (the ticket is still created, in `NEW` status, for manual triage) instead of crashing.

## Installation

Requires Python 3.11+.

```bash
git clone <this-repo>
cd Port4
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt   # or requirements.txt for a runtime-only install
cp .env.example .env
```

Edit `.env` and set `OPENAI_API_KEY` and `JWT_SECRET_KEY` (see below).

## Environment Variables

`.env`:

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
# OPENAI_FALLBACK_MODELS=gpt-4o,gpt-4-turbo,gpt-3.5-turbo
# DATABASE_URL=sqlite:////absolute/path/to/port4.db
JWT_SECRET_KEY=insecure-dev-secret-change-me-32bytes+
# JWT_EXPIRE_MINUTES=1440
```

| Variable | Description | Default |
|---|---|---|
| `OPENAI_API_KEY` | Your OpenAI API key (see [Getting API Keys](#getting-api-keys)) | — |
| `OPENAI_MODEL` | OpenAI model id, tried first | `gpt-4o-mini` |
| `OPENAI_FALLBACK_MODELS` | Optional comma-separated list of other models to fall back to (see [Model Fallback](#model-fallback)) | unset - no fallback |
| `DATABASE_URL` | SQLAlchemy database URL for the backend API | `sqlite:///<repo>/port4.db` |
| `JWT_SECRET_KEY` | Signs issued JWT access tokens - **set a real value outside local dev** | insecure dev default |
| `JWT_EXPIRE_MINUTES` | Minutes until an access token expires | `1440` (1 day) |

Swapping to Postgres later is a one-line change: `DATABASE_URL=postgresql+psycopg://user:pass@host/dbname` - the entire backend is written against SQLAlchemy, not SQLite-specific code.

## Running the App

Two processes, in two terminals (both from the repo root, with `.venv` activated):

```bash
# 1. Backend API
uvicorn backend.main:app --reload --port 8000

# 2. Frontend (one app, one port - landing page offers Customer and Admin login)
streamlit run frontend/app.py --server.port 8501
```

Open `http://localhost:8501`: the landing page has a **Customer** tab (login/register) and an **Admin** tab (login only, no self-service admin signup by design - admin login must never be reachable via a customer registration flow). Create the first admin account with:

```bash
python -m backend.create_admin --name "Ops Admin" --email admin@example.com --password <a-real-password>
# add --department "Engineering" (etc.) to scope an admin to one team instead of super-admin
```

## Authentication & Roles

Two roles, `USER` and `ADMIN`, in one `users` table (`backend/models.py`). Passwords are hashed with `bcrypt`; sessions are stateless JWT access tokens (`pyjwt`), verified per-request by FastAPI dependencies (`backend/auth.py`: `get_current_user`, `require_role(...)`).

- `POST /auth/register` / `POST /auth/login` - regular users only; rejects admin accounts.
- `POST /admin/login` - admin accounts only; rejects regular users. There is no `/admin/register` - see [Running the App](#running-the-app).
- An `ADMIN` row's `department` column scopes that admin to one team's tickets; `NULL` means a super-admin who sees every department.
- `POST /auth/forgot-password` is a placeholder: it generates and logs a reset token server-side but doesn't send an email yet (no email provider is wired up).

## Ticket Lifecycle

Seven statuses (`backend/models.py: TicketStatus`), replacing the old two-value Pending/Closed model:

| Status | Meaning |
|---|---|
| `NEW` | Created, AI has not (yet, or successfully) triaged it |
| `OPEN` | AI has triaged it; department assigned; waiting in queue |
| `IN_PROGRESS` | An admin is actively working it |
| `PENDING_CUSTOMER` | Waiting on more information from the customer |
| `ON_HOLD` | Waiting on a vendor, external dependency, or another internal team |
| `RESOLVED` | Admin believes it's solved; customer can accept or reject |
| `CLOSED` | Terminal - cannot be reopened; a new issue needs a new ticket |

Rules enforced in `backend/services/ticket_service.py` (never left to the frontend):
- A customer reply while `RESOLVED` automatically moves the ticket back to `IN_PROGRESS`, unless it's already `CLOSED`.
- `POST /tickets/:id/accept-solution` only succeeds from `RESOLVED`, and moves to `CLOSED`.
- `POST /tickets/:id/reopen` only succeeds from `RESOLVED` (also → `IN_PROGRESS`); `CLOSED` tickets reject every mutation.
- Every transition, AI categorization (or its failure), assignment, and reply is appended to `ticket_activity` by one shared `log_activity()` helper.

## AI Chatbot & Escalation Flow

1. The customer chats freely (`POST /chat/message`) with a general first-line agent (`ticket_router/services/agent_service.py: chat_with_general_agent`) - no ticket exists yet. A "Try an example" dropdown (`sample-tickets/tickets.json`, loaded via `ticket_router/ui/sample_tickets.py`) lets you send one of 20 realistic sample messages instead of typing one.
2. If it doesn't resolve the issue, the customer picks a priority and clicks **"Still need help? Create a ticket"** (`POST /chat/escalate`), sending the full transcript plus their priority choice.
3. `escalate_to_ticket()` (`backend/services/ticket_service.py`) persists the transcript as the ticket's first messages, then calls the *same* `route_ticket()` used before this refactor to get category/priority/department/summary - unchanged AI code, just called from the backend instead of directly from Streamlit.
4. If AI categorization fails, the ticket is still created (status `NEW`, department `Unassigned`) so the request is never lost - an admin triages it manually.
5. From there, the department's `skills/*.md` persona continues driving replies (see below), and the ticket follows the lifecycle rules above.

## API Overview

Full interactive docs (OpenAPI/Swagger) are served at `/docs` once the backend is running (e.g. `http://localhost:8000/docs`).

```
POST /auth/register              POST /admin/login
POST /auth/login                 PATCH /admin/tickets/:id/status
POST /auth/logout                PATCH /admin/tickets/:id/assign
POST /auth/forgot-password        PATCH /admin/tickets/:id/reassign
                                   POST /admin/tickets/:id/message
GET  /tickets                     GET  /admin/tickets
GET  /tickets/:id                 GET  /admin/tickets/:id
POST /tickets/:id/messages        GET  /admin/metrics
POST /tickets/:id/accept-solution GET  /admin/admins
POST /tickets/:id/reopen

POST /chat/message
POST /chat/escalate
```

## The Reusable Routing Function

Every code path that needs AI classification - the escalation flow, and the test suite - calls the exact same function:

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
2. **Forced structured output** — whichever model answers is called with a `route_ticket` function tool and `tool_choice` forcing that exact tool call, so the model cannot reply with free text.
3. **Pydantic validation** — every result is parsed and validated against [`ticket_router/models.py`](ticket_router/models.py)'s `TicketRouteResult`, regardless of how it arrived.
4. **Automatic single retry** — on validation failure, the AI is called again with the error appended as context.
5. **JSON repair** — [`ticket_router/services/json_repair.py`](ticket_router/services/json_repair.py) strips code fences, extracts the first balanced `{...}` block, and fixes trailing commas, for the case the model's tool-call arguments aren't clean JSON.
6. **Graceful failure** — if all else fails, a typed `AIResponseError` is raised and the caller (`escalate_to_ticket()`) still creates the ticket rather than losing it. **The app never crashes.**

## Retry Strategy

[`ticket_router/services/ticket_routing_service.py`](ticket_router/services/ticket_routing_service.py) implements the full pipeline: call → parse/validate (with repair fallback) → (if invalid) retry once with error context → parse/validate again → (if still invalid) raise a typed error. This is a single bounded retry, not an unbounded loop, keeping latency and cost predictable.

## Model Fallback

Retries alone don't help if the configured model itself is unavailable (rate limit, outage, decommissioned model, etc.). Fallback is **opt-in**: with `OPENAI_FALLBACK_MODELS` unset, [`OpenAIProvider`](ticket_router/ai/openai_provider.py) only ever tries `OPENAI_MODEL`, and a failure raises immediately - no silent extra API calls to a model you didn't ask for.

Set `OPENAI_FALLBACK_MODELS` to a comma-separated list to enable a chain, e.g.:

```env
OPENAI_FALLBACK_MODELS=gpt-4o,gpt-4-turbo,gpt-3.5-turbo
```

```
gpt-4o-mini (OPENAI_MODEL, tried first)
  → gpt-4o
  → gpt-4-turbo
  → gpt-3.5-turbo
```

- On failure (rate limit, timeout, 5xx, or a response with no tool call), it automatically falls through to the next model in the list, in order.
- **Authentication/permission errors fail fast** without burning the rest of the chain - a bad API key fails identically on every model, so there's no point retrying it.
- If every model in the chain fails, a single `AIUnavailableError` is raised.
- The same model chain drives the chat agents too (see below), via LangChain's `.with_fallbacks()` instead of a hand-rolled loop.

## Department Agents & skills.md

Once a ticket has a department, replies from that side are grounded in that department's own `skills.md` persona - e.g. a ticket routed to `Security Team` is handled by an agent grounded in [`skills/security_team.md`](skills/security_team.md), not a generic assistant. Each of the 8 teams has its own file under [`skills/`](skills/), defining that agent's role, tone, scope, and boundaries:

| Team | skills.md |
|---|---|
| Billing Team | [`billing_team.md`](skills/billing_team.md) |
| Support Team | [`support_team.md`](skills/support_team.md) |
| Engineering | [`engineering.md`](skills/engineering.md) |
| QA | [`qa.md`](skills/qa.md) |
| Security Team | [`security_team.md`](skills/security_team.md) |
| Sales Team | [`sales_team.md`](skills/sales_team.md) |
| Logistics | [`logistics.md`](skills/logistics.md) |
| Customer Success | [`customer_success.md`](skills/customer_success.md) |

[`ticket_router/services/agent_service.py`](ticket_router/services/agent_service.py) loads the right file for the routed team as a system prompt, driven through [`ticket_router/ai/chat_llm.py`](ticket_router/ai/chat_llm.py) - the same LangChain `ChatOpenAI` with `.with_fallbacks(...)` used everywhere else. The same module also defines `GENERAL_SUPPORT_SYSTEM_PROMPT` / `chat_with_general_agent()` for the pre-ticket, no-department-yet first-line bot.

## Edge Cases

| Case | Behavior |
|---|---|
| Angry / profanity-laden message | Classified normally; the model is instructed to never refuse based on tone. |
| Very short message (e.g. `"broken"`) | Still classified, with a lower confidence score. |
| Ambiguous message (e.g. `"I can't access my order"`) | Classified into the best-fit category, with reasoning that explains the choice over the alternative. |
| Empty input | Rejected with a clear error before any AI call is made. |
| Very long message | Truncated to 8,000 characters before being sent to the AI (`MAX_TICKET_LENGTH` in `ticket_router/models.py`). |
| Non-English message | Still classified, with lower confidence and a note of uncertainty in the reasoning. |
| AI categorization fails entirely | The ticket is still created (status `NEW`, department `Unassigned`) instead of being lost. |

## Testing

```bash
source .venv/bin/activate
pytest -v
```

54 tests:

- `tests/backend/` — FastAPI `TestClient` tests against a throwaway per-test SQLite file: registration/login/admin-login and role guards, escalation (including the AI-failure path), status-transition rules, department-scoped admin access, and dashboard metrics.
- `tests/test_validation.py` / `tests/test_retry.py` / `tests/test_openai_provider.py` — the original AI-layer tests, unmodified, run against fake AI providers (no live API calls).

## Code Quality

```bash
ruff check .      # lint
black .           # format
```

Strict Pydantic models, typed exceptions, PEP 8-conformant naming (`assigned_team` internally, aliased to `assignedTeam` on the wire to match the tool schema), and no hardcoded secrets anywhere in source.

## Screenshots

_Add screenshots of the customer chat/escalation flow, a ticket detail view, and the admin queue to `screenshots/` and reference them here, e.g.:_

```markdown
![Customer chat](screenshots/user-chat.png)
![Admin queue](screenshots/admin-queue.png)
```
