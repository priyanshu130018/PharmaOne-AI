# PharmaOne AI — AI-Powered Deviation Intake

**PharmaOne AI** is the production-grade implementation of the **AIVOA.AI AI-Powered Deviation Intake** specification.

It streamlines pharmaceutical manufacturing deviation reporting by ingesting uploaded documents (PDF, text) or pasted content (text, emails), extracting structured GMP fields via **LangGraph** and **Groq LLM**, retrieving relevant standard operating procedures (SOPs) via **Vector RAG**, and providing initial impact and severity recommendations. A human reviewer retains final authority to review, edit, or override any values before saving the final approved deviation to **PostgreSQL / Supabase**.

---

## Architecture

PharmaOne AI is built as a **clean, layered monolith** containerized with Docker Compose. No microservices are introduced.

### High-Level Deployment Architecture

```text
                           ┌──────────────────────────────────────────────┐
                           │               CLOUD SERVER                   │
                           │                                              │
    [ Browser User ] ────▶ │  [ Frontend Container: Nginx (Port 8080) ]   │
                           │     │                                        │
                           │     ├─ Serves React 18 + Redux SPA Shell     │
                           │     └─ Reverse-proxies /api ─────────────┐   │
                           │                                          │   │
                           │  [ Backend Container: FastAPI (Port 8000)│   │
                           │     │                                    │   │
                           │     ├─ REST API Endpoints ◀──────────────┘   │
                           │     ├─ Text & Scanned PDF OCR Pipeline       │
                           │     ├─ LangGraph Multi-Node Workflow         │
                           │     ├─ Vector RAG Retrieval Engine           │
                           │     └─ SQLAlchemy 2.0 Async Persistence      │
                           └─────────────────┬────────────────────────────┘
                                             │
                      ┌──────────────────────┴──────────────────────┐
                      ▼                                             ▼
           [ Cloud Supabase / Postgres ]                 [ Groq AI Cloud API ]
           - Authoritative Deviations                    - LLaMA 3.3 70B
           - AI Audit Trail Snapshots                    - Structured JSON
```

### Layered Monolith Design

```text
 ┌────────────────────────────────────────────────────────────────────────┐
 │ API Layer (FastAPI Routers)                                            │
 │  - /api/v1/deviations/extract-text  (Upload & OCR)                     │
 │  - /api/v1/deviations/process       (AI Analysis & RAG)                │
 │  - /api/v1/deviations               (CRUD & Save)                      │
 │  - /health & /api/v1/health/ready   (Liveness & Readiness)             │
 └──────────────────────────────────┬─────────────────────────────────────┘
                                    │ depends on
 ┌──────────────────────────────────▼─────────────────────────────────────┐
 │ Service Layer (Business Logic & Orchestration)                         │
 │  - ExtractionService (MIME validation, streaming size limit, cleanup)   │
 │  - OcrService (Tesseract & Poppler image fallback)                     │
 │  - ProcessingService (AI workflow dispatcher)                          │
 │  - RagService (Vector embeddings & cosine similarity matching)         │
 │  - DeviationService (Human review authority & sequential references)   │
 └──────────────────┬─────────────────────────────────┬───────────────────┘
                    │                                 │
 ┌──────────────────▼───────────────┐ ┌───────────────▼───────────────────┐
 │ LangGraph Workflow Engine        │ │ Repository & Persistence Layer    │
 │  - validate_input                │ │  - DeviationRepository            │
 │  - extract_deviation (Groq LLM)  │ │  - AuditRepository                │
 │  - validate_structured_output    │ │  - SQLAlchemy Async Session       │
 │  - retrieve_reference_context    │ └───────────────┬───────────────────┘
 │  - assess_impact                 │                 │
 │  - assess_severity               │ ┌───────────────▼───────────────────┐
 │  - prepare_final_assessment      │ │ Database Layer (PostgreSQL)       │
 └──────────────────────────────────┘ │  - Deviations Table & Aliases     │
                                      │  - AI Audit Traceability Columns  │
                                      └───────────────────────────────────┘
```

---

## Folder Structure

```text
PharmaOne-AI/
├── docker-compose.yml              # Multi-container orchestration (Backend + Frontend)
├── .env.example                    # Template of required cloud environment variables
├── .dockerignore                   # Build context exclusions (strictly excludes .env)
├── .gitignore                      # Git tracking exclusions
├── README.md                       # Complete technical guide and documentation
├── AIVOA_DEMO_SCRIPT.md            # Step-by-step 5-10 minute technical demo script
│
├── backend/                        # FastAPI Layered Monolith
│   ├── Dockerfile                  # Python 3.12-slim + Tesseract OCR + Poppler utils
│   ├── requirements.txt            # Pinned runtime dependencies
│   ├── requirements-dev.txt        # Test runner dependencies (pytest, aiosqlite)
│   ├── alembic.ini                 # Database migration config
│   ├── pytest.ini                  # Pytest async configuration
│   ├── alembic/                    # Migration scripts
│   │   └── versions/
│   │       ├── 0001_initial.py
│   │       └── 0002_aivoa_deviation_fields.py
│   ├── app/
│   │   ├── main.py                 # FastAPI application factory, CORS, exception handlers
│   │   ├── api/
│   │   │   ├── deps.py             # Dependency injection providers
│   │   │   └── v1/                 # Endpoints: deviations, health, reports
│   │   ├── core/                   # Config (BaseSettings), Enums, Logging, Exceptions
│   │   ├── db/                     # Engine, sessionmaker, declarative base
│   │   ├── models/                 # SQLAlchemy models (Deviation, Audit, Knowledge)
│   │   ├── repositories/           # Data access objects (Deviation, Audit)
│   │   ├── schemas/                # Pydantic schemas (Extraction, Process, Deviation)
│   │   ├── services/               # Extraction, OCR, RAG, Deviation business services
│   │   └── workflows/              # LangGraph deviation intake graph
│   └── tests/                      # Automated test suite (52 tests, 100% passing)
│       ├── conftest.py
│       ├── test_deviations.py
│       ├── test_extraction.py
│       ├── test_workflow.py
│       ├── test_health.py
│       ├── test_process.py
│       ├── test_e2e_intake.py
│       └── test_demo_reliability.py
│
└── frontend/                       # React 18 + Vite SPA
    ├── Dockerfile                  # Multi-stage build (Node 20 -> Nginx 1.27)
    ├── package.json                # Dependencies: React, Redux Toolkit, Lucide icons
    ├── vite.config.js              # Vite bundler configuration
    ├── tailwind.config.js          # Tailwind CSS design system
    ├── nginx/
    │   └── default.conf.template   # Dynamic envsubst template with 20MB upload limit
    └── src/
        ├── App.jsx                 # Two-panel responsive desktop layout
        ├── app/store.js            # Redux store configuration
        ├── api/client.js           # API communication client
        ├── constants/vocab.js      # Controlled GMP vocabularies
        ├── features/               # Redux slices: deviations, assistant, aiProcessing
        ├── components/             # UI: LogDeviationForm, AiAssistantPanel, AssistantResult
        └── components/__tests__/   # Vitest suite (12 tests, 100% passing)
```

---

## Required Environment Variables

All configuration is strictly environment-driven. The application fails fast at startup with clear validation errors if any required variable is absent.

| Variable | Target | Purpose | Example / Format |
| :--- | :---: | :--- | :--- |
| `ENVIRONMENT` | Backend | Runtime profile (`development`, `staging`, `production`, `test`) | `production` |
| `BACKEND_PORT` | Backend / Compose | Port the FastAPI backend binds to | `8000` |
| `FRONTEND_PORT` | Frontend / Compose | Port the Nginx web server binds to | `8080` |
| `API_BASE_URL` | Backend | Public API base URL used for OpenAPI documentation | `http://your-server-ip:8000` |
| `CORS_ORIGINS` | Backend | Allowed browser origins (comma-separated list) | `http://your-server-ip:8080` |
| `DATABASE_URL` | Backend | Async PostgreSQL connection string | `postgresql+asyncpg://postgres:pass@db.ref.supabase.co:5432/postgres` |
| `SUPABASE_URL` | Backend | Cloud Supabase project endpoint | `https://your-ref.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | Backend | Supabase service role key (backend secret only) | `eyJhbGciOi...` |
| `GROQ_API_KEY` | Backend | Groq Cloud AI API key (backend secret only) | `gsk_...` |
| `GROQ_MODEL` | Backend | Groq LLM model identifier | `llama-3.3-70b-versatile` |
| `HUGGINGFACE_API_KEY` | Backend | HuggingFace embedding API key | `hf_...` |
| `MAX_UPLOAD_SIZE_BYTES` | Backend | Maximum file upload size in bytes (default: 10MB) | `10485760` |
| `OCR_ENABLED` | Backend | Enable OCR fallback for scanned/image PDFs | `true` |
| `VITE_API_BASE_URL` | Frontend | Optional build-time API URL (empty = relative `/api/v1`) | `""` |

> [!IMPORTANT]
> Never commit `.env` to source control. Secrets (`GROQ_API_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `DATABASE_URL`) are never exposed to the frontend browser bundle.

---

## Cloud Deployment Instructions (Docker Compose)

Deploy directly on any cloud virtual machine (Ubuntu, Debian, AWS EC2, GCP Compute Engine, Azure VM, DigitalOcean):

### 1. Prerequisites on Cloud Server
```bash
# Verify Docker and Docker Compose plugin are installed
docker --version
docker compose version
```

### 2. Clone Repository & Configure Environment
```bash
git clone https://github.com/priyanshu130018/PharmaOne-AI.git
cd PharmaOne-AI

# Create production .env file from template
cp .env.example .env

# Edit .env with your cloud Supabase database URL, Groq key, and server ports
nano .env
```

### 3. Build & Launch Containers
```bash
# Build Docker images cleanly
docker compose build

# Start containers in detached mode
docker compose up -d
```

### 4. Apply Database Migrations
```bash
# Run Alembic migrations against cloud PostgreSQL/Supabase
docker compose exec backend alembic upgrade head
```

### 5. Verify Container Health & Connectivity
```bash
# Check container status (both should report healthy)
docker compose ps

# Test Backend Health endpoint (returns HTTP 200)
curl -i http://localhost:8000/health

# Test Database Readiness probe (verifies live PostgreSQL connectivity)
curl -i http://localhost:8000/api/v1/health/ready

# Inspect production container logs
docker compose logs -f --tail=100 backend
```

Access the web interface at `http://<YOUR_SERVER_IP>:8080`.

---

## API Endpoint Summary

All application endpoints are versioned under `/api/v1`. A root-level `/health` probe is also exposed for cloud orchestrators.

| Method | Endpoint | Purpose | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Liveness Probe | Root health alias returning HTTP 200 without touching DB. |
| `GET` | `/api/v1/health` | Liveness Probe | API liveness returning environment, version, and status. |
| `GET` | `/api/v1/health/ready` | Readiness Probe | Verifies live PostgreSQL database connectivity (`SELECT 1`). |
| `POST` | `/api/v1/deviations/extract-text` | Extraction Pipeline | Ingests PDF document or pasted text/email, runs OCR if scanned, returns normalized text. |
| `POST` | `/api/v1/deviations/process` | AI Assistant | Executes LangGraph graph: Groq extraction, Vector RAG retrieval, impact & severity recommendations. |
| `POST` | `/api/v1/deviations` | Save Final Deviation | Persists human-reviewed authoritative deviation and stores AI audit snapshots. |
| `GET` | `/api/v1/deviations` | List Deviations | Paginated list with filtering by `status`, `severity`, and `deviation_type`. |
| `GET` | `/api/v1/deviations/{id}` | Retrieve Deviation | Retrieves single deviation record by UUID with AI audit fields. |
| `PUT` | `/api/v1/deviations/{id}` | Update Deviation | Modifies reviewed deviation record. |
| `DELETE` | `/api/v1/deviations/{id}` | Delete Deviation | Cascading delete of deviation record. |
| `GET` | `/api/v1/reports/summary` | Analytics Summary | Aggregated counts grouped by status, severity, and type. |

Interactive OpenAPI Swagger documentation is available at `http://<SERVER_IP>:8000/docs`.

---

## AI Workflow & LangGraph Implementation

The AI extraction and evaluation pipeline is implemented as a deterministic **LangGraph `StateGraph`** (`backend/app/workflows/deviation_intake.py`):

```text
  START
    ↓
[ validate_input ]
    ↓
[ extract_deviation ] ──────────▶ (Groq LLM LLaMA 3.3 70B / Structured JSON)
    ↓
[ validate_structured_output ] ─▶ (Pydantic StructuredDeviation validation)
    ↓
[ retrieve_reference_context ] ─▶ (Vector RAG Cosine Matching over SOPs)
    ↓
[ assess_impact ] ──────────────▶ (Evaluates CQAs & contamination risks)
    ↓
[ assess_severity ] ────────────▶ (Recommends Minor / Major / Critical per ICH Q9)
    ↓
[ prepare_final_assessment ] ───▶ (Compiles ProcessResponse with evidence & citations)
    ↓
   END
```

- **Groq LLM**: Fast inference utilizing `llama-3.3-70b-versatile` producing structured JSON schemas.
- **Fail-Safe Heuristic Fallback**: If the external Groq API times out or credentials are misconfigured, the graph immediately activates a heuristic rule-based regex extractor (`_heuristic_fallback_extraction`), ensuring the user interface remains fully operational without 500 errors.

---

## Vector RAG Reference Retrieval

The RAG engine (`backend/app/services/rag_service.py`) provides grounded regulatory context to eliminate hallucination:
- **Reference Knowledge Base**: Pre-indexed SOPs and guidelines covering:
  - Cleanroom particulate limits and HVAC differential pressure (`SOP-QA-042`)
  - Autoclave sterilization hold times and SAL $10^{-6}$ sterility assurance (`SOP-PR-108`)
  - Cold-chain temperature excursion hold times (`SOP-QC-210`)
  - Sensor calibration drifts and out-of-tolerance impact (`SOP-EQ-104`)
- **Retrieval Mechanism**: Tokenized term-frequency normalized unit vectors with cosine similarity matching.
- **Metadata Retention**: Retrieved citations maintain exact document name, section, chunk ID, and numerical similarity score presented to the reviewer.

---

## Human Review & Regulatory Authority

In strict compliance with **FDA 21 CFR Part 11**, **EU GMP Annex 11**, and **ICH Q9 (Quality Risk Management)**:
1. **AI Output is Decision Support Only**: AI-recommended impact and severity are **proposals**, not final classifications.
2. **Reviewer Authority**: The human operator has complete freedom to modify any pre-populated field, downgrade or upgrade severity, or alter the rationale.
3. **No Overwrite Policy**: The frontend state management tracks `userEditedFields`. Once a user edits a field, subsequent AI suggestions will **never** overwrite the user's input.
4. **Visual Badges**: Fields populated by AI display an `AI extracted` badge; user-modified fields display a `Modified` badge.

---

## Database Persistence & Audit Traceability

When the user clicks **Save Deviation** (`POST /api/v1/deviations`):
- **Authoritative Values**: The user-approved values in the form are stored in the primary database columns (`severity`, `impact`, `title`, `description`, etc.).
- **Audit Trail Snapshots**: The original AI recommendations and retrieved evidence are permanently preserved in dedicated audit columns:
  - `ai_recommended_severity`
  - `ai_recommended_impact`
  - `ai_reason`
  - `ai_evidence`
  - `ai_extraction`
- **Sequential Reference Numbers**: Every deviation is assigned a monotonic reference (`DEV-YYYY-XXXXXX`).

---

## Verification & Automated Testing

The entire repository is covered by automated unit, integration, and reliability test suites:

```bash
# Run backend test suite (52 tests across all modules)
cd backend
pytest -v

# Run frontend test suite (12 tests across components and Redux slices)
cd ../frontend
npm test -- --run

# Run frontend production build
npm run build
```

---

## Known Limitations

1. **OCR Performance**: High-resolution scanned documents processed via Tesseract OCR in container environments require reasonable CPU allocation.
2. **Live External AI Credentials**: Live Groq LLM calls and Supabase persistence require active API keys configured in `.env`. In offline or disconnected environments, the built-in heuristic extractor and SQLite in-memory database ensure 100% operational resilience.
