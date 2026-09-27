# PharmaOne AI — AI-Powered Deviation Intake

**PharmaOne AI** is the production-grade implementation of the **AIVOA.AI AI-Powered Deviation Intake** specification.

It streamlines pharmaceutical manufacturing deviation reporting by ingesting uploaded documents (PDF, text) or pasted content (text, emails), extracting structured GMP fields via **LangGraph** and **Groq LLM**, retrieving relevant standard operating procedures (SOPs) via **Vector RAG**, and providing initial impact and severity recommendations. A human reviewer retains final authority to review, edit, or override any values before saving the final approved deviation to **PostgreSQL / Supabase**.

---

## Architecture

PharmaOne AI is built as a **clean, layered monolith** containerized with Docker Compose. No microservices are introduced.

### High-Level Deployment Architecture

```text
                           ┌──────────────────────────────────────────────┐
                           │                 DEPLOYMENT                   │
                           │                                              │
    [ Browser User ] ────▶ │  [ Frontend: React 18 + Redux SPA Shell ]    │
                           │     │                                        │
                           │     └─ Direct REST API calls (/api/v1) ──┐   │
                           │                                          │   │
                           │  [ Backend: FastAPI (Port 8000) ]        │   │
                           │     │                                    │   │
                           │     ├─ REST API Endpoints ◀──────────────┘   │
                           │     ├─ Text & Scanned PDF OCR Pipeline       │
                           │     ├─ LangGraph Multi-Node AI Workflow      │
                           │     ├─ Vector RAG Retrieval Engine           │
                           │     └─ SQLAlchemy 2.0 Async Persistence      │
                           └─────────────────┬────────────────────────────┘
                                             │
                      ┌──────────────────────┴──────────────────────┐
                      ▼                                             ▼
           [ Cloud Supabase / Postgres ]                 [ Groq AI Cloud API ]
           - Authoritative Deviations                    - openai/gpt-oss-20b
           - AI Audit Trail Snapshots                    - Structured JSON
### End-to-End System Workflow

```mermaid
flowchart TD
    A[User Login] --> B[Supabase Auth]
    B --> C[Authenticated Session]
    C --> D[Dashboard / Deviations]

    D --> E[Upload PDF or Paste Text]
    E --> F{PDF contains extractable text?}

    F -->|Yes| G[Direct PDF Text Extraction]
    F -->|No| H[Hugging Face Vision OCR]

    G --> I[Structured AI Extraction]
    H --> I

    I --> J[Pydantic Validation]

    J --> K[BGE-small Query Embedding]
    K --> L[pgvector Similarity Search]

    L --> M[Retrieve Top-K Quality Context]
    M --> N[Deterministic Checks]
    N --> O[Groq Risk Assessment]

    O --> P[Impact / Severity / Reason / Evidence]

    P --> Q[Human Review]
    Q --> R{User edits?}

    R -->|Yes| S[Store User-Reviewed Values]
    R -->|No| T[Accept AI Recommendation]

    S --> U[Save Deviation]
    T --> U

    U --> V[Supabase PostgreSQL]
    V --> W[Dashboard / Reports]
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
 │  - OcrService (Hugging Face Inference API OCR fallback)                     │
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
│   ├── Dockerfile                  # Python 3.12-slim production container
│   ├── requirements.txt            # Pinned runtime dependencies
│   ├── requirements-dev.txt        # Test runner dependencies (pytest, aiosqlite)
│   ├── alembic.ini                 # Database migration config
│   ├── pytest.ini                  # Pytest async configuration
│   ├── alembic/                    # Migration scripts
│   │   └── versions/
│   │       ├── 0001_initial.py
│   │       ├── 0002_aivoa_deviation_fields.py
│   │       └── 0003_knowledge_vector_embeddings.py
│   ├── app/
│   │   ├── main.py                 # FastAPI application factory, CORS, exception handlers
│   │   ├── ai/                     # LangGraph AI pipeline (graph, extraction, risk_assessment, prompts, models)
│   │   ├── api/
│   │   │   ├── deps.py             # Dependency injection providers
│   │   │   └── v1/                 # Endpoints: deviations, health, reports, auth
│   │   ├── core/                   # Config (BaseSettings), Auth, Enums, Logging, Exceptions
│   │   ├── db/                     # Engine, sessionmaker, declarative base
│   │   ├── models/                 # SQLAlchemy models (Deviation, Audit, Knowledge, Org)
│   │   ├── rag/                    # Vector RAG (service, embeddings, retrieval)
│   │   ├── repositories/           # Data access objects (Deviation, Audit)
│   │   ├── schemas/                # Pydantic schemas (Extraction, Process, Deviation)
│   │   ├── scripts/                # CLI utilities (ingest_knowledge, seed_demo_users)
│   │   └── services/               # Deviation, extraction, PDF, OCR, ingestion, storage, report services
│   └── tests/                      # Automated test suite (100% passing)
│       ├── conftest.py
│       ├── test_auth_isolation.py
│       ├── test_cors.py
│       ├── test_demo_reliability.py
│       ├── test_deviations.py
│       ├── test_e2e_intake.py
│       ├── test_extraction.py
│       ├── test_health.py
│       ├── test_ocr_huggingface.py
│       ├── test_process.py
│       ├── test_storage_rag_ingestion.py
│       └── test_workflow.py
│
└── frontend/                       # React 18 + Vite SPA
    ├── package.json                # Dependencies: React, Redux Toolkit, Lucide icons
    ├── vite.config.js              # Vite bundler configuration
    ├── tailwind.config.js          # Tailwind CSS design system
    ├── vercel.json                 # Cloud SPA routing configuration
    └── src/
        ├── App.jsx                 # Multi-view layout (Dashboard, Deviations)
        ├── app/store.js            # Redux store configuration
        ├── api/client.js           # API communication client
        ├── constants/vocab.js      # Controlled GMP vocabularies
        ├── features/               # Redux slices: auth, deviations, assistant, aiProcessing
        ├── components/             # UI: DashboardView, LogDeviationForm, AiAssistantPanel, LoginPage
        └── components/__tests__/   # Vitest suite (100% passing)
```

---

## Required Environment Variables

All configuration is strictly environment-driven. The application fails fast at startup with clear validation errors if any required variable is absent.

| Variable | Target | Purpose | Example / Format |
| :--- | :---: | :--- | :--- |
| `ENVIRONMENT` | Backend | Runtime profile (`development`, `staging`, `production`, `test`) | `production` |
| `BACKEND_PORT` | Backend / Compose | Port the FastAPI backend binds to | `8000` |
| `FRONTEND_PORT` | Frontend / Compose | Port the frontend binds to in local hosting | `8080` |
| `API_BASE_URL` | Backend | Public API base URL used for OpenAPI documentation | `http://your-server-ip:8000` |
| `CORS_ORIGINS` | Backend | Allowed browser origins (comma-separated list) | `http://your-server-ip:8080` |
| `DATABASE_URL` | Backend | Async PostgreSQL connection string | `postgresql+asyncpg://postgres:pass@db.ref.supabase.co:5432/postgres` |
| `SUPABASE_URL` | Backend | Cloud Supabase project endpoint | `https://your-ref.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | Backend | Supabase service role key (backend secret only) | `eyJhbGciOi...` |
| `GROQ_API_KEY` | Backend | Groq Cloud AI API key (backend secret only) | `gsk_...` |
| `GROQ_MODEL` | Backend | Groq LLM model identifier | `openai/gpt-oss-20b` |
| `HUGGINGFACE_API_KEY` | Backend | Hugging Face Inference API key (BAAI/bge-small-en-v1.5 embeddings & OCR) | `hf_...` |
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

## Application Modules & User Experience

PharmaOne AI provides an enterprise pharmaceutical quality management interface adhering to FDA 21 CFR Part 11 and EU GMP Annex 11 principles.

### Global Navigation Bar
The top navigation bar provides unified routing across the QMS platform:
- **`Dashboard` (`/dashboard`)**: Functional live operational overview.
- **`Deviations` (`/deviations`)**: Functional AI-powered deviation intake workspace.
- **`CAPAs`**, **`Change Control`**, **`Audits`**, **`Documents`**, **`Reports`**: Enterprise placeholder modules cleanly designated as coming soon without dead-end routes.

The active navigation item is visually highlighted, and browser URL changes are synchronized via HTML5 history state.

### 1. Operational Dashboard (`/dashboard`)
The Dashboard delivers a company-tenant-scoped real-time quality overview powered strictly by live database figures via `GET /api/v1/reports/summary` and `GET /api/v1/deviations`:
- **Company Tenant Scope**: Strictly isolates data by the authenticated user's organization (`current_user.company_id`). Users from Vasundha Pharma Chem Limited cannot view data from other companies.
- **Summary Metric Cards**:
  - **Total Deviations**: All deviations recorded for the active operating company.
  - **Critical Deviations**: High-risk events impacting product quality or patient safety.
  - **Major Deviations**: Significant deviations requiring formal CAPA investigation.
  - **Minor Deviations**: Low-risk procedural or documentation variations.
- **Recent Deviations (Left Panel)**: Tabular summary listing Deviation ID, Title, Severity, Status, and Date. Rows remain non-clickable per data model specifications.
- **Review Required (Right Panel)**: Triage list filtered to deviations requiring active attention (`status !== "closed"`), displaying severity badges and submission dates.
- **Deviation Activity Breakdown (Bottom Panel)**: Real-time visual metrics illustrating distribution by category (`summary.by_type`) and lifecycle stage (`summary.by_status`).
- **Compliant Empty States**: When zero deviations exist for a tenant, clean compliant notices ("No deviations recorded yet." with a direct "Log Deviation" shortcut) appear instead of fabricated or hardcoded placeholder data.

### 2. AI-Powered Deviation Intake (`/deviations`)
A balanced two-column workspace faithfully aligned with pharmaceutical workflow standards:
- **Left Panel (Log Deviation Form)**: Complete form containing Title, Description, Date/Time Occurred, Deviation Type, Immediate Action, Root Cause, Impact Assessment, and Severity Rating.
- **Right Panel (AI Deviation Assistant)**:
  - Document & Text Ingestion (PDF upload with automatic optical character recognition for scanned records, or direct text/email pasting).
  - One-click **Analyze with AI Assistant** running LangGraph workflow, Groq LLM extraction, and BGE-small Vector RAG retrieval.
  - Interactive multi-turn AI Assistant chat at the bottom of the panel for real-time risk assessment inquiries, procedural clarifications, and evidence checks.
  - **Human Review & Non-Overwrite Authority**: Reviewers can edit any AI suggestion; modified fields retain priority and are tagged with `Modified` badges, while pristine suggestions display `AI extracted`.

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
[ extract_deviation ] ──────────▶ (Groq LLM openai/gpt-oss-20b / Structured JSON)
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

- **Groq LLM**: Fast inference utilizing `openai/gpt-oss-20b` producing structured JSON schemas.
- **Fail-Safe Heuristic Fallback**: If the external Groq API times out or credentials are misconfigured, the graph immediately activates a heuristic rule-based regex extractor (`_heuristic_fallback_extraction`), ensuring the user interface remains fully operational without 500 errors.

---

## Vector RAG Reference Retrieval

The production RAG engine (`backend/app/services/rag_service.py` & `backend/app/services/ingestion_service.py`) provides grounded regulatory context to eliminate hallucination:

- **Authoritative Storage & Database**:
  - **Supabase Storage Bucket**: `knowledge-base/reference-documents/` serves as the authoritative cloud document repository for regulatory guidance and SOP PDFs (e.g., `Form-450-Deviation-Report-Form.pdf`, `ICH_Q9(R1)_Guideline_Step4_2025_0115_0.pdf`, `QUALITY CONTROL SAMPLE SUBMISSION AND TRACKING FORM.pdf`).
  - **PostgreSQL Vector Store**: Document chunks and dense embeddings are persisted in `knowledge_documents` and `knowledge_chunks` tables with the PostgreSQL `pgvector` extension.
- **Dense Embedding Model (BGE-Small Only)**:
  - Generates dense vector embeddings using **`BAAI/bge-small-en-v1.5`** exclusively via Hugging Face Serverless Inference (`https://router.huggingface.co/hf-inference/models/BAAI/bge-small-en-v1.5`).
  - Dimension: Exactly **384 dimensions**, unit Euclidean ($L_2$) normalized.
  - Exclusivity: Strictly bound to `BAAI/bge-small-en-v1.5`. No fallback to any alternative embedding model.
- **Runtime Vector Search & Ranking**:
  - Runtime RAG executes `RagService.asearch()` querying PostgreSQL `knowledge_chunks` using pgvector cosine distance (`KnowledgeChunk.embedding.cosine_distance(query_embedding)`).
  - **Minimum Similarity Threshold**: Strictly enforced **`0.20`** minimum cosine similarity (`max_dist = 0.80`). Chunks below 0.20 are discarded to prevent irrelevant or dilutive regulatory context.
  - **Top K**: Top 3 most relevant reference chunks retrieved.
- **Strict AIVOA Fail-Safe & Error Handling**:
  - If Hugging Face inference is unavailable or fails, `RagService` returns a controlled error without crashing or inventing context (`EmbeddingGenerationError` -> `([], False, notes)`).
  - Deterministic 384-dimensional dense projection is explicitly isolated to offline/test execution without pretending to be production embeddings.
- **Zero Local PDF Runtime Dependency**:
  - The runtime application does **not** read local PDFs (`data/rag_sources/` is purged).
  - Document ingestion is an admin/deployment utility (`python -m backend.app.scripts.ingest_knowledge`) that downloads directly from Supabase Storage `knowledge-base/reference-documents/`, extracts text, chunks, computes BGE-small embeddings, and persists to PostgreSQL.
- **Full Traceability**: Retrieved chunks maintain complete source metadata: document title, chunk ID, section, page, and similarity score, rendered in the AI Assistant review panel.

---

## Authentication, Multi-Tenancy & RBAC

PharmaOne AI integrates **Supabase Auth** with strict enterprise role-based access control (RBAC) and complete multi-tenant company data isolation:

- **Supabase Auth & Session Verification**:
  - Email/password authentication handled via Supabase Auth API (`POST /api/v1/auth/login`).
  - Bearer JWT tokens verified server-side on all protected endpoints (`get_current_user` dependency).
  - Public endpoints: `/health`, `/api/v1/health`, `/api/v1/auth/demo-users`.
- **Multi-Tenant Company Data Isolation**:
  - Each user belongs to a distinct pharmaceutical operating company.
  - Queries (`GET /api/v1/deviations`, `GET /api/v1/reports/summary`) and mutations (`POST /api/v1/deviations`, `PUT /api/v1/deviations/{id}`, `DELETE /api/v1/deviations/{id}`) strictly enforce `Deviation.company_id == current_user.company_id`.
  - A user in Company A (e.g. Priyanshu at Vasundha Pharma Chem Limited) cannot see, query, or modify deviations from Company B (e.g. Competitor Pharma Limited).
- **Role-Based Access Control (RBAC)**:
  - Supported roles: `QA Manager`, `Production User`, `QC User`.
- **21 CFR Part 11 Immutable Audit Trail**:
  - All critical compliance events are logged to the database: `LOGIN`, `LOGOUT`, `ACCESS_DENIED`, `DEVIATION_CREATED`, `DEVIATION_UPDATED`.
- **Demo Login (DEMO ONLY — Not for Production Use)**:
  - **Email**: `priyanshu@gmail.com`
  - **Password**: `123456789`
  - **Role**: *QA Manager* at **Vasundha Pharma Chem Limited**
  - **Employee ID**: `DEMO-001`
  - **Department**: Quality Assurance
  - **Site**: Demo Manufacturing Site
- **User Authentication & Navigation Flow**:
  1. **Open website** (`/`) → redirects to Login screen (`/login`)
  2. **Login** with `priyanshu@gmail.com` / `123456789`
  3. **Dashboard** (`/dashboard`) → Company-scoped deviation metrics, recent logs, and triage
  4. **Deviations** (`/deviations`) → AI intake, RAG evaluation, human review & save
  5. **Logout** → Clears Supabase session & Redux state, redirects to `/login`
- **Idempotent User Provisioning Script**:
  ```bash
  cd backend
  python -m app.scripts.seed_demo_users
  ```

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

The entire repository is covered by automated unit, integration, and cloud-reliability test suites:

- **Backend**: **98 automated tests** (100% passing across 11 test modules) covering REST endpoints, CORS headers, extraction pipeline, Hugging Face OCR, BGE-small vector embeddings, Supabase Storage ingestion, pgvector similarity search, LangGraph deviation intake workflow, Supabase Auth token validation, RBAC enforcement, and tenant company isolation.
- **Frontend**: **25 automated tests** (100% passing across 5 component, Redux store, Dashboard, and Auth routing suites) verifying UI state management, non-overwriting badge tracking, intake forms, assistant interaction, Dashboard metrics, single Priyanshu demo login, and routing flows.
- **Total**: **123 automated tests** (100% passing).

```bash
# Run backend test suite (98 tests across all modules)
cd backend
pytest -v

# Run frontend test suite (25 tests across components, Redux slices, and auth routing)
cd ../frontend
npm test

# Run frontend production build
npm run build
```

---

## Known Limitations

1. **OCR & Embeddings**: Scanned documents and dense embeddings are processed via Hugging Face Serverless Inference API (`BAAI/bge-small-en-v1.5`), subject to API key configuration. Neither Tesseract nor local binary dependencies are used.
2. **Live External AI Credentials**: Live Groq LLM calls and Supabase persistence require active API keys configured in `.env`. In offline or test environments, the built-in heuristic extractor and isolated deterministic projection ensure 100% test resilience without crashing.

