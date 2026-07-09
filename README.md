# Smart Support Ticket Router

An AI-powered support ticket triage system. Paste any customer support message and get back a structured, always-valid JSON classification: **category**, **priority**, **assigned team**, **one-line reasoning**, and a **confidence score** — in seconds instead of minutes.

Built with React + TypeScript + Vite + Tailwind on the frontend, Express + TypeScript on the backend, and [Groq](https://groq.com) (via its OpenAI-compatible API) for classification, with strict Zod validation, automatic retries, and JSON repair guaranteeing the backend never crashes and never returns malformed data.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Getting a Groq API Key](#getting-a-groq-api-key)
- [Installation](#installation)
- [Environment Variables](#environment-variables)
- [Running the Backend](#running-the-backend)
- [Running the Frontend](#running-the-frontend)
- [API](#api)
- [Prompt Engineering](#prompt-engineering)
- [JSON Reliability & Validation](#json-reliability--validation)
- [Retry Strategy](#retry-strategy)
- [Edge Cases](#edge-cases)
- [Sample Tickets & Demo Mode](#sample-tickets--demo-mode)
- [Testing](#testing)
- [Screenshots](#screenshots)

## Overview

Support teams spend a meaningful amount of time simply _sorting_ incoming tickets before anyone starts solving them. This project automates that sorting step: it takes raw, unstructured ticket text and returns a structured routing decision that a real support desk could act on immediately — with the reasoning included, so a human can verify it at a glance.

## Architecture

```
smart-ticket-router (repo root)
├── backend/            Express + TypeScript API
│   └── src/
│       ├── server.ts        thin bootstrap - no business logic
│       ├── app.ts           builds the Express app (importable by tests)
│       ├── config/          env loading + validation
│       ├── types/           shared TS types (Category, Priority, ...)
│       ├── utils/           logger, AppError, asyncHandler
│       ├── validation/      Zod schemas (request + AI result)
│       ├── prompts/         system prompt + few-shot examples
│       ├── ai/               AIProvider interface, GroqProvider (the app's only AI provider)
│       ├── services/         promptService, jsonRepairService, ticketRoutingService (retry/repair orchestration)
│       ├── middleware/       timing, errorHandler, notFoundHandler
│       └── routes/           /api/route-ticket, /api/health
├── frontend/           React + TypeScript + Vite + Tailwind SPA
│   └── src/
│       ├── pages/            HomePage, DemoPage
│       ├── components/       TicketInputForm, ResultCard, JsonViewer, ...
│       ├── hooks/             useRouteTicket
│       └── services/          api.ts (axios)
├── sample-tickets/     20 realistic tickets (source of truth for the example dropdown + demo mode)
└── docs/               AI-Concepts.md (plain-English explanation for reviewers/mentors)
```

The AI layer sits behind an `AIProvider` interface implemented by [`GroqProvider`](backend/src/ai/GroqProvider.ts), the app's only AI provider - this keeps the AI call, retry, and validation logic testable without making real network requests.

## Getting a Groq API Key

1. Create a free account at [console.groq.com](https://console.groq.com).
2. Open **API Keys** in the console and create a new key.
3. Copy it into `GROQ_API_KEY` in `backend/.env` (see [Environment Variables](#environment-variables)). Never commit this key.

## Installation

Requires Node.js 18+ and npm 9+ (npm workspaces).

```bash
git clone <this-repo>
cd smart-ticket-router
npm install          # installs root, backend, and frontend deps via npm workspaces
cp .env.example backend/.env
cp frontend/.env.example frontend/.env   # optional, defaults work for local dev
```

Edit `backend/.env` and set your `GROQ_API_KEY`.

## Environment Variables

`backend/.env`:

```env
PORT=5000
NODE_ENV=development

GROQ_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile
```

| Variable | Description | Default |
|---|---|---|
| `PORT` | Backend HTTP port | `5000` |
| `NODE_ENV` | `development`, `production`, or `test` | `development` |
| `GROQ_API_KEY` | Your Groq API key (see [Getting a Groq API Key](#getting-a-groq-api-key)) | — |
| `GROQ_MODEL` | Groq model id | `llama-3.3-70b-versatile` |

`frontend/.env`:

| Variable | Description | Default |
|---|---|---|
| `VITE_API_BASE_URL` | Backend API base URL | `http://localhost:5000/api` |

**No API key is ever hardcoded.** If `GROQ_API_KEY` is missing, the server still boots (health checks and the frontend work), but any classification request returns a clean `500 AI_UNAVAILABLE` error instead of crashing.

## Running the Backend

```bash
npm run dev -w backend     # tsx watch mode, http://localhost:5000
npm run build -w backend   # compiles to backend/dist
npm run start -w backend   # runs the compiled build
npm run test -w backend    # runs the Vitest suite
```

## Running the Frontend

```bash
npm run dev -w frontend    # Vite dev server, http://localhost:5173
npm run build -w frontend  # type-checks then builds to frontend/dist
```

## Running Both Together

```bash
npm run dev     # runs backend and frontend concurrently (from the repo root)
```

## API

### `POST /api/route-ticket`

Request:

```json
{ "message": "I was charged twice for my subscription this month." }
```

Success response (`200`):

```json
{
  "success": true,
  "data": {
    "category": "Billing",
    "priority": "Medium",
    "assignedTeam": "Billing Team",
    "reasoning": "Customer reports a duplicate subscription charge.",
    "confidence": 0.95
  },
  "processingTime": "243 ms"
}
```

Error responses:

- `400` — empty or malformed request body (`VALIDATION_ERROR`)
- `500` — AI provider unavailable / misconfigured (`AI_UNAVAILABLE`), or the AI could not produce a valid response after retries (`AI_RESPONSE_ERROR`)

```json
{ "success": false, "error": { "message": "...", "code": "AI_RESPONSE_ERROR" } }
```

### `GET /api/health`

Basic liveness check, returns `{ "success": true, "data": { "status": "ok" } }`.

## Prompt Engineering

The system prompt ([`backend/src/prompts/systemPrompt.ts`](backend/src/prompts/systemPrompt.ts)) is structured into explicit sections: role, objective, classification rules for all 11 categories, priority rules, team-assignment rules, reasoning rules, confidence rules, the output contract, and hard failure instructions ("never markdown, never prose, only call the tool"). It's reinforced with 12 few-shot examples ([`backend/src/prompts/fewShotExamples.ts`](backend/src/prompts/fewShotExamples.ts)) covering password resets, refunds, outages, crashes, duplicate charges, login failures, feature requests, shipping delays, broken APIs, security breaches, cancellations, and invoice issues. See [docs/AI-Concepts.md](docs/AI-Concepts.md) for the full rationale.

## JSON Reliability & Validation

Six layers of defense guarantee the API always returns valid, schema-conforming JSON:

1. **Prompt engineering** — the system prompt above.
2. **Forced structured output** — Groq's OpenAI-compatible Chat Completions API is called with a `route_ticket` function tool and `tool_choice` forcing that exact tool call, so the model cannot reply with free text.
3. **Zod validation** — every result is validated against [`backend/src/validation/ticketResultSchema.ts`](backend/src/validation/ticketResultSchema.ts) regardless of how it arrived.
4. **Automatic single retry** — on validation failure, the AI is called again with the error appended as context.
5. **JSON repair** — a fallback that strips code fences, extracts the first balanced `{...}` block, and fixes trailing commas, for the rare case a provider returns raw text instead of structured output.
6. **Graceful failure** — if all else fails, a typed `AIResponseError` is thrown and converted to a clean `500` JSON error by the global error handler. **The backend process never crashes.**

## Retry Strategy

`services/ticketRoutingService.ts` implements the full pipeline: call → validate/repair → (if invalid) retry once with error context → validate/repair again → (if still invalid) throw a typed error. This is a single bounded retry, not an unbounded loop, keeping latency and cost predictable.

## Edge Cases

| Case | Behavior |
|---|---|
| Angry / profanity-laden message | Classified normally; the model is instructed to never refuse based on tone. |
| Very short message (e.g. `"broken"`) | Still classified, with a lower confidence score. |
| Ambiguous message (e.g. `"I can't access my order"`) | Classified into the best-fit category, with reasoning that explains the choice over the alternative. |
| Empty input | Rejected with a `400` before any AI call is made. |
| Very long message | Truncated to 8,000 characters before being sent to the AI (documented in `validation/ticketRequestSchema.ts`). |
| Non-English message | Still classified, with lower confidence and a note of uncertainty in the reasoning. |

## Sample Tickets & Demo Mode

[`sample-tickets/tickets.json`](sample-tickets/tickets.json) contains 20 realistic tickets spanning all 11 categories. This file is the single source of truth, imported directly by the frontend for both the **example ticket dropdown** on the main page and **Demo Mode** — a dedicated page that steps through all 20 tickets (manually or on autoplay), showing the input, the AI's structured output, and the processing time for each. Open Demo Mode from the link at the bottom of the main page.

## Testing

```bash
npm run test -w backend
```

22 tests across three files, run against a mocked AI provider (no live API calls):

- `tests/validation.test.ts` — 10 consecutive tests asserting the Zod schema accepts well-formed AI output and rejects malformed output (missing fields, invalid enums, out-of-range confidence, wrong types).
- `tests/retry.test.ts` — empty-input rejection, JSON repair (code fences, trailing commas, prose-wrapped JSON), the single-retry-then-succeed path, the both-attempts-fail path, and the AI-unavailable path.
- `tests/routeTicket.integration.test.ts` — full HTTP-level checks via `supertest` for the 400, 200, and 500 response shapes.

## Screenshots

_Add screenshots of the main router UI, a result card, and Demo Mode to `screenshots/` and reference them here, e.g.:_

```markdown
![Main UI](screenshots/main-ui.png)
![Demo Mode](screenshots/demo-mode.png)
```
