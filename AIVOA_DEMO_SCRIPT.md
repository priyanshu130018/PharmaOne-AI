# AIVOA Technical Demo Script (5–10 Minutes)
## PharmaOne AI — AI-Powered Deviation Intake

This script provides an exact, step-by-step guide for presenting the PharmaOne AI technical demonstration to technical evaluators, compliance officers, and executive stakeholders.

---

### Step 1: Open Application
- **Action**: Navigate to `http://<SERVER_IP>:8080` in the browser.
- **Presenter Script**:
  > *"Welcome to the PharmaOne AI technical demonstration. What you see is a production-grade implementation of the AIVOA AI-Powered Deviation Intake workflow, built specifically for pharmaceutical and biomanufacturing quality operations."*

---

### Step 2: Explain Two-Panel Layout
- **Action**: Point to the left panel ("Log Deviation"), then to the right panel ("AI Deviation Assistant").
- **Presenter Script**:
  > *"The interface is structured in an ergonomic two-panel layout:*
  > *- **Left Panel**: The official GMP **Log Deviation** form containing all standard identification, product, parameter, and assessment fields.*
  > *- **Right Panel**: The **AI Deviation Assistant**, which serves as the primary intake interface. Users do not manually fill out the form from scratch; the AI assistant analyzes unstructured input and pre-populates the form for human review."*

---

### Step 3: Input Deviation (Upload PDF or Paste Text)
- **Action**: In the right panel, select the **Paste Text / Email** tab and paste the representative deviation:
  ```text
  During API manufacturing Batch B24001, the approved temperature range was 70–75°C. The actual temperature reached 82°C for approximately 15 minutes. Production was stopped and QA was notified.
  ```
  *(Alternative: upload a deviation PDF document using the **Upload PDF / Document** tab).*
- **Presenter Script**:
  > *"The assistant supports multiple ingestion channels: native PDF documents, scanned image PDFs via automated OCR fallback, or raw text and emails pasted directly into the panel."*

---

### Step 4: Show AI Processing State
- **Action**: Click the blue **Analyze Text** (or **Analyze Document**) button.
- **Presenter Script**:
  > *"Notice the clear, multi-stage progress indication. The system indicates active stages: normalizing input, invoking the LangGraph workflow, executing Groq extraction, and querying the vector RAG database for relevant SOPs. The button is disabled to prevent duplicate requests."*

---

### Step 5: Show PDF/Text Extraction
- **Action**: Point to the normalized character count and extraction status.
- **Presenter Script**:
  > *"The extraction service has cleaned the input, normalized line breaks, validated document headers, and extracted the raw text content without any memory leaks or file retention on disk."*

---

### Step 6: Show Structured AI Extraction
- **Action**: Point to the structured extraction summary card in the right assistant panel.
- **Presenter Script**:
  > *"Our LangGraph engine passed the raw text to Groq, which parsed the unstructured narrative into a strict Pydantic schema: separating concrete facts (Batch B24001, 82°C) from missing information and inferring the deviation type as equipment/process."*

---

### Step 7: Show Automatic Log Deviation Form Population
- **Action**: Direct attention to the left **Log Deviation** panel.
- **Presenter Script**:
  > *"Notice how the left form was automatically populated in real time through Redux state:*
  > *- Batch / Lot Number: `B24001`*
  > *- Parameter: `Temperature`*
  > *- Approved Range: `70–75°C`*
  > *- Actual Value: `82°C`*
  > *- Duration: `15 minutes`*
  > *- Immediate Action: `Production was stopped and QA was notified`*
  > *- QA Notified: checked `true`*
  > *Each AI-populated field features an **AI extracted** badge for total transparency."*

---

### Step 8: Show RAG Evidence & Context
- **Action**: Scroll to the **Reference Documents & SOP Citations** card in the assistant panel.
- **Presenter Script**:
  > *"The assistant queried our vector RAG knowledge base using semantic cosine similarity. It retrieved relevant SOPs—specifically SOP-QA-042 and calibration standards—providing the exact document name, section, and similarity match score. The AI does not hallucinate regulatory standards; it is grounded in pre-indexed quality documentation."*

---

### Step 9: Show AI Impact Recommendation
- **Action**: Point to the **Initial Impact** field and badge in the assistant panel.
- **Presenter Script**:
  > *"The workflow evaluated Critical Quality Attributes (CQAs) and recommended an initial impact area of `Product Quality / Compliance` based on temperature excursion limits."*

---

### Step 10: Show AI Severity Recommendation
- **Action**: Point to the **Initial Severity** badge (`Major`).
- **Presenter Script**:
  > *"The system recommended an initial severity of `Major`. This recommendation is driven by decision logic grounded in ICH Q9 Quality Risk Management methodology."*

---

### Step 11: Show Reason & Regulatory Disclaimer
- **Action**: Point to the **AI Assessment Reason** text and the prominent **ICH Q9 Human Review Warning**.
- **Presenter Script**:
  > *"Notice the explicit warning at the bottom of the card:*
  > *'Decision Support Only — Final impact and severity must be confirmed by authorized quality personnel.'*
  > *We never claim the AI makes autonomous regulatory decisions."*

---

### Step 12: Edit at Least One AI-Generated Field
- **Action**: In the left form, click into the **Site / Plant** field and type:
  `Plant 1 - API Synthesis Suite 2`
  Then click into the **Detailed Description** and append:
  `Engineering confirmed primary heating element failure.`
- **Presenter Script**:
  > *"The human reviewer has complete freedom to edit any field. Notice that as soon as I edit a field, the badge updates from 'AI extracted' to 'Modified', tracking human intervention."*

---

### Step 13: Override Severity or Impact
- **Action**: On the **Initial Severity** dropdown, change `Major` to `Minor`. In the **Assessment Reason** box, add:
  `Human Reviewer Override: Redundant secondary sensor confirmed core bulk temperature remained within acceptable safety margins.`
- **Presenter Script**:
  > *"Here is the most critical compliance principle: **The human reviewer is authoritative.** I am overriding the AI's 'Major' recommendation to 'Minor' with an engineering rationale. The system allows this override seamlessly."*

---

### Step 14: Save Deviation
- **Action**: Scroll to the bottom of the form and click the green **Save Deviation** button.
- **Presenter Script**:
  > *"With all mandatory GMP fields validated, the Save button is enabled. Let's submit the final deviation."*

---

### Step 15: Show Successful Save
- **Action**: Point to the green success toast notification showing:
  `Deviation DEV-2026-000001 saved successfully.`
- **Presenter Script**:
  > *"The deviation was submitted and assigned an official, sequential GMP tracking reference: `DEV-2026-000001`."*

---

### Step 16: Explain Database Persistence & Audit Trail
- **Action**: Explain the dual-persistence model.
- **Presenter Script**:
  > *"In the database (PostgreSQL / Supabase):*
  > *- The official recorded severity is **Minor** (the user's authoritative choice).*
  > *- Crucially, the AI's original recommendation (**Major**), along with its citations and rationale, is permanently preserved in audit columns (`ai_recommended_severity`, `ai_evidence`).*
  > *This guarantees complete 21 CFR Part 11 and EU GMP Annex 11 traceability."*

---

### Step 17: Explain Frontend Architecture
- **Presenter Script**:
  > *"The frontend is a lightweight React 18 single-page application built with Vite and Tailwind CSS. It uses Redux Toolkit with three dedicated slices: `deviationSlice` for form state and user override tracking, `assistantSlice` for file upload and ingestion, and `aiProcessingSlice` for stage-by-stage workflow tracking."*

---

### Step 18: Explain FastAPI Endpoints
- **Presenter Script**:
  > *"The backend is built with FastAPI following a strict layered architecture:*
  > *- `POST /api/v1/deviations/extract-text`: Ingests files or text, enforces strict 10MB limits, runs OCR if scanned, and cleans up temporary files immediately.*
  > *- `POST /api/v1/deviations/process`: AI orchestration endpoint returning structured extraction and RAG citations without persisting anything.*
  > *- `POST /api/v1/deviations`: Persists the finalized, human-approved deviation.*
  > *- `GET /health` & `GET /api/v1/health/ready`: Liveness and database readiness probes."*

---

### Step 19: Explain LangGraph Nodes
- **Presenter Script**:
  > *"The AI workflow is modeled in LangGraph as an asynchronous state graph with 7 sequential nodes:*
  > *1. `validate_input`*
  > *2. `extract_deviation`*
  > *3. `validate_structured_output`*
  > *4. `retrieve_reference_context`*
  > *5. `assess_impact`*
  > *6. `assess_severity`*
  > *7. `prepare_final_assessment`*
  > *If any step encounters an issue, the graph degrades gracefully to rule-based fallback without throwing 500 errors."*

---

### Step 20: Explain Groq LLM
- **Presenter Script**:
  > *"We utilize Groq Cloud running openai/gpt-oss-20b with low-latency LPUs. This delivers sub-second inference with guaranteed adherence to our Pydantic JSON schemas."*

---

### Step 21: Explain RAG Engine
- **Presenter Script**:
  > *"Our RAG service maintains pre-computed vector embeddings for pharmaceutical SOPs and ICH guidelines. It performs cosine similarity matching to return the top 3 relevant chunks with full citations, preventing LLM hallucinations."*

---

### Step 22: Explain Human Review Policy
- **Presenter Script**:
  > *"To conclude: PharmaOne AI is an assistant, not an autonomous agent. The human expert remains in the loop at all times. The AI extracts facts, provides regulatory context, and offers an initial recommendation, but only the authorized human reviewer can approve and commit the final record to the database."*
