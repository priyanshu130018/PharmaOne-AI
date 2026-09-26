# PharmaOne AI — AI-Powered Deviation Intake

PharmaOne AI is the production-ready **foundation** for an AI-assisted
pharmaceutical **deviation intake** system. A reporter pastes a deviation
report or email, the AI assistant extracts structured fields and proposes a
risk classification, and a human reviews and edits everything before it is
saved. Every AI output is decision support only and is explicitly flagged as
requiring human review.

This repository contains a clean, layered monolith that builds and runs with a
single `docker compose up`, and is structured so the next steps (real LLM/RAG
pipeline, authentication, org/RLS, document ingestion) can be added behind the
existing contracts without rework.

<!--__README_BODY__-->

## Architecture

A single **layered monolith** with two deployable containers (backend API and
frontend SPA), plus a managed Postgres database (Supabase). No microservices.

```
Browser ──▶ Frontend container (nginx)
                 │  serves the React SPA
                 │  reverse-proxies /api ──▶ Backend container (FastAPI/uvicorn)
                                                   │
                                                   ▼
                                          Supabase Postgres
```

The backend follows a strict layering so responsibilities stay separated:

```
API (routes)         thin HTTP layer, request/response only
   │  depends on
Services             business logic / orchestration
   │
Repositories         all database access (SQLAlchemy)
   │
Models               ORM entities (SQLAlchemy 2.0)

Schemas (Pydantic)   define the API contract in/out
Workflows            AI orchestration (deviation intake)
Core                 config, enums, logging, exceptions
DB                   engine/session, declarative base
```

Key design choices: configuration is **environment-only with no fallback
defaults** (the app fails fast if a required variable is missing); the database
engine is created lazily so the container boots and reports liveness even before
the DB is reachable; the AI workflow is an **offline heuristic stub** today and
plugs a real LLM + RAG pipeline in behind the same `/deviations/process`
contract later.

## Folder structure

```
PharmaOne_AI/
├── backend/                 FastAPI layered application
│   ├── app/
│   │   ├── api/             routers (v1) + dependency wiring
│   │   ├── core/            config, enums, logging, exceptions
│   │   ├── db/              engine/session, declarative base
│   │   ├── models/          SQLAlchemy models (deviation, audit, knowledge)
│   │   ├── schemas/         Pydantic request/response contracts
│   │   ├── repositories/    database access layer
│   │   ├── services/        business logic
│   │   ├── workflows/       AI deviation-intake orchestration (stub)
│   │   └── main.py          app factory, middleware, lifespan
│   ├── alembic/             async migrations (+ 0001_initial)
│   ├── tests/               pytest suite (SQLite-backed)
│   ├── Dockerfile
│   ├── requirements.txt / requirements-dev.txt
│   └── alembic.ini / pytest.ini
├── frontend/                React + Redux Toolkit + Tailwind (Vite)
│   ├── src/
│   │   ├── app/             Redux store
│   │   ├── features/        deviations + assistant slices
│   │   ├── components/      UI (two-panel layout)
│   │   ├── api/             fetch client (relative /api/v1)
│   │   └── constants/       controlled vocabularies
│   ├── nginx/               default.conf.template (envsubst at runtime)
│   ├── Dockerfile
│   └── package.json / vite.config.js / tailwind.config.js
├── .env.example             all required variable names + placeholders
├── .gitignore
├── .dockerignore
├── docker-compose.yml
└── README.md
```

## Tech stack

Backend: Python 3.12, FastAPI, SQLAlchemy 2.0 (async) + asyncpg, Alembic,
Pydantic v2 / pydantic-settings. Frontend: React 18, Redux Toolkit, Vite,
Tailwind CSS, served by nginx. Database: PostgreSQL (Supabase). Containerized
with Docker and orchestrated by Docker Compose.

<!--__README_BODY2__-->

## Required environment variables

All configuration is read from the environment — there are **no hardcoded
defaults for required values** in application code. Copy `.env.example` to
`.env` and fill in real values. The backend raises a clear validation error at
startup if any required variable is missing.

| Variable | Used by | Description |
| --- | --- | --- |
| `ENVIRONMENT` | backend | `development` \| `staging` \| `production` \| `test` |
| `BACKEND_PORT` | backend, compose | Port the API binds to |
| `FRONTEND_PORT` | frontend, compose | Port nginx serves the SPA on |
| `API_BASE_URL` | backend | Public base URL of the API (OpenAPI metadata) |
| `CORS_ORIGINS` | backend | Comma-separated list of allowed browser origins |
| `DATABASE_URL` | backend | Async DSN, e.g. `postgresql+asyncpg://user:pass@host:5432/postgres` |
| `SUPABASE_URL` | backend | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | backend | Supabase service role key (secret) |
| `GROQ_API_KEY` | backend | Groq API key (secret) |
| `GROQ_MODEL` | backend | Groq chat model identifier |
| `HUGGINGFACE_API_KEY` | backend | HuggingFace API key (secret) |
| `VITE_API_BASE_URL` | frontend build | Optional; empty ⇒ relative `/api/v1` |

Secrets are never committed (`.env` is git-ignored) and are never baked into
Docker images — they are injected at container start from `.env`.

## Deploy with Docker (cloud server)

The stack is designed to run on a cloud server, not just localhost.

1. Install Docker Engine + the Compose plugin on the server.
2. Clone the repository and create the environment file:
   ```bash
   cp .env.example .env
   # edit .env — set the real Supabase DSN, keys, ports, and your public
   # origin(s) in CORS_ORIGINS and API_BASE_URL
   ```
3. Build and start both containers:
   ```bash
   docker compose up -d --build
   ```
4. Apply database migrations once the backend is up:
   ```bash
   docker compose exec backend alembic upgrade head
   ```
5. Check status and logs:
   ```bash
   docker compose ps
   docker compose logs -f backend
   ```

The frontend is served on `FRONTEND_PORT` and reverse-proxies `/api` to the
backend over the internal Docker network, so only the frontend port needs to be
publicly exposed. Both containers define health checks; Compose waits for the
backend to be healthy before starting the frontend. Point your domain / TLS
terminator (e.g. a load balancer or an nginx/Caddy in front) at the frontend
port.

To stop: `docker compose down` (add `-v` only if you also want to remove
volumes).

<!--__README_BODY3__-->

## Local development (without Docker)

Backend:
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
# export the required variables (or use a .env in ./backend)
uvicorn app.main:app --reload --port "${BACKEND_PORT:-8000}"
```

Frontend (in a second terminal):
```bash
cd frontend
npm install
npm run dev        # Vite dev server on :5173, proxies /api to the backend
```
The Vite dev server proxies `/api` to `http://localhost:8000` by default; set
`VITE_DEV_API_TARGET` to point elsewhere.

## Running tests

The backend test suite runs fully offline against a local SQLite database (no
Postgres, network, or API keys needed — the test harness sets the required env
vars itself):
```bash
cd backend
pip install -r requirements-dev.txt
pytest
```
Coverage includes deviation CRUD + filtering, the AI process→review→save flow,
report aggregation, and health/readiness endpoints.

## Important API endpoints

Base path: `/api/v1`.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Liveness (no DB dependency) |
| `GET` | `/health/ready` | Readiness (checks DB connectivity) |
| `POST` | `/deviations/process` | AI assistant: extract fields + risk assessment (nothing saved) |
| `POST` | `/deviations` | Create a final, human-reviewed deviation |
| `GET` | `/deviations` | List/filter deviations (`status`, `severity`, `deviation_type`, paging) |
| `GET` | `/deviations/{id}` | Retrieve one deviation |
| `PUT` | `/deviations/{id}` | Update a reviewed deviation |
| `DELETE` | `/deviations/{id}` | Delete a deviation |
| `GET` | `/reports/summary` | Aggregate counts by status / severity / type |

Interactive API docs (Swagger UI) are available at `/docs` when the backend is
running.

## AI assistant behaviour (important)

`POST /deviations/process` currently returns an **offline heuristic stub**
(`is_stub: true`, `provider: "stub"`) that classifies deviation type, severity,
and impact from keywords and extracts fields with light parsing. It returns
`requires_human_review: true` and labels its risk basis as *configurable/demo
criteria*, not a regulatory lookup. Nothing is persisted by this endpoint — the
reporter reviews and edits the suggestions, then saves via `POST /deviations`,
which stores the final values plus the AI snapshots for audit. The real
LangGraph + Groq + RAG pipeline plugs in behind this same contract with no
change to the frontend or the save flow.

## Scope

This is a foundation focused on the deviation intake module: deviation CRUD, the
AI process→review→save flow, minimal audit records, knowledge-document metadata
tables, and reporting. Authentication, org/RLS multi-tenancy, document
ingestion/OCR, and the live LLM/RAG pipeline are deliberately out of scope for
this stage and are prepared for as documented next steps.



