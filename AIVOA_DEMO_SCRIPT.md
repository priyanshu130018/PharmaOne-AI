# AIVOA Technical Demo Script (5–10 Minutes)
## PharmaOne AI — AI-Powered Deviation Intake

This script provides an exact, step-by-step guide for presenting the PharmaOne AI technical demonstration to technical evaluators, compliance officers, and executive stakeholders.

---

### Step 1: Open Application & Authenticate
- **Action**: Navigate to `http://<SERVER_IP>:8080` in the browser and log in with the demo account:
  - **Email**: `priyanshu@gmail.com`
  - **Password**: `123456789`
- **Presenter Script**:
  > *"Welcome to the PharmaOne AI technical demonstration. What you see is a production-grade implementation of the AIVOA AI-Powered Deviation Intake workflow, built specifically for pharmaceutical quality operations under FDA 21 CFR Part 11 and EU GMP Annex 11 principles."*

---

### Step 2: Navigate to Deviations Workspace & Explain Layout
- **Action**: Click **Deviations** in the top navigation bar.
- **Presenter Script**:
  > *"The intake workspace uses a clear two-column layout:*
  > *- **Left Column (Authoritative Log Deviation Workspace)**: Contains the official GMP deviation form with all mandatory identification, product, parameter, and assessment fields. After submission, the comprehensive Deviation Severity Report is rendered here.*
  > *- **Right Column (AI Deviation Assistant Chatbot)**: A conversational AI assistant equipped with direct document intake (📎 attachment button) and natural language form manipulation."*

---

### Step 3: Ingest Deviation Document or Text
- **Action**: In the right-hand AI assistant chat composer, click the paperclip icon (`📎`) to upload a deviation report PDF, or paste an incident summary directly into the chat:
  ```text
  During API manufacturing Batch B24001, the approved temperature range was 70–75°C. The actual temperature reached 82°C for approximately 15 minutes. Production was stopped and QA was notified.
  ```
- **Presenter Script**:
  > *"The assistant accepts native PDF documents, scanned records via automated OCR fallback, or raw incident narratives pasted directly into the composer. Let's send this incident description to the assistant."*

---

### Step 4: Show Automated Form Population & Green Highlighting
- **Action**: Point to the assistant's confirmation response, then direct attention to the left form.
- **Presenter Script**:
  > *"Notice what happened instantly:*
  > *1. The AI parsed the unstructured text into strict GMP parameters (Batch B24001, Temperature, Approved Range 70–75°C, Actual Value 82°C, Duration 15 minutes, QA Notified checked).*
  > *2. The left form was automatically populated through Redux.*
  > *3. Every AI-populated field is visually highlighted with a light-green background, green border, and an 'AI updated' indicator with a pulsing dot for complete transparency."*

---

### Step 5: Natural-Language Form Updates with Structured Audit
- **Action**: In the chatbot composer, type:
  ```text
  Change the site to Demo Manufacturing Site and batch to LOT-2026-051.
  ```
- **Presenter Script**:
  > *"Users can interact with the assistant in natural language to update any field. Notice the structured response:*
  > *'✓ Changes applied'*
  > *listing Site / Plant and Batch / Lot Number. Simultaneously, the left form updates those exact fields and reapplies the green visual highlight."*

---

### Step 6: Human Review & Non-Overwrite Authority
- **Action**: In the left form, click into the **Site / Plant** field and append:
  ` - Suite B`
  Then change **Initial Severity** from `Major` to `Minor`.
- **Presenter Script**:
  > *"Here is the critical compliance principle: **The human reviewer is authoritative.** As soon as I manually edit a field, the green highlight clears for that field and the system marks it as human-reviewed. Subsequent AI recommendations will never silently overwrite user-confirmed entries."*

---

### Step 7: Save Deviation & View Severity Report
- **Action**: Click the blue **Save Deviation** button on the left form.
- **Presenter Script**:
  > *"With all mandatory fields verified, let's submit the deviation. Upon saving:*
  > *1. The deviation is persisted to PostgreSQL and assigned a sequential reference: `DEV-2026-000001`.*
  > *2. Directly below the form on the left, the **Deviation Severity Report** renders the full AI Risk Assessment: Impact area, Recommended Severity, Rationale, and grounded SOP evidence retrieved via vector RAG."*

---

### Step 8: Explain Persistence & 21 CFR Part 11 Traceability
- **Presenter Script**:
  > *"In PostgreSQL / Supabase, the dual-persistence model stores:*
  > *- The authoritative, user-approved values in the primary columns.*
  > *- The original AI recommendations, rationale, and citations in dedicated audit columns (`ai_recommended_severity`, `ai_recommended_impact`, `ai_evidence`).*
  > *This guarantees complete 21 CFR Part 11 audit traceability."*

---

### Step 9: Operational Dashboard
- **Action**: Click **Dashboard** in the top navigation bar.
- **Presenter Script**:
  > *"The Dashboard aggregates live metrics scoped strictly to the user's company tenant (Vasundha Pharma Chem Limited). Users can monitor total deviations, severity breakdowns, and triage active investigations in real time."*

---

### Step 10: Technical Architecture Summary
- **Presenter Script**:
  > *"Under the hood:*
  > *- **Frontend**: React 18 single-page application built with Vite, Tailwind CSS, and Redux Toolkit.*
  > *- **Backend**: FastAPI layered monolith containerized with Docker Compose.*
  > *- **AI Pipeline**: Deterministic LangGraph state graph executing Groq LLM extraction and BGE-small dense embeddings with pgvector cosine similarity search.*
  > *- **OCR**: Hugging Face Inference API vision fallback for scanned documents, with zero local binary dependencies.*
  > *- **Testing**: 143 automated tests across backend (108) and frontend (35) with 100% passing rate."*
