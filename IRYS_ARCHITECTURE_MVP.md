# IRYS MVP ARCHITECTURE
## Robust Foundations for Paper Register Digitization

**Version:** 1.0  
**Status:** Raw MVP  
**Target Ship Date:** End of Mar 2026  
**Scope:** UG Hub + MEL Officer (Accra)  

---

## EXECUTIVE SUMMARY

Irys solves: **Speed + Centralization + Auditability**
- Kill manual data entry (photos → structured data)
- Centralize registers in one database
- Create audit trail for compliance

Current architecture works (MVP). This document restructures it for:
1. **Reliability** — proper error handling, retries, failure states
2. **Maintainability** — clear separation of concerns, testability
3. **Scalability** — foundation to add auth, multi-hub, analytics later
4. **Learning** — patterns that transfer directly to other projects

---

## PART 1: SYSTEM ARCHITECTURE

### 1.1 High-Level Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERACTION LAYER                    │
│  (React SPA on Vercel - Mobile/Desktop Browser)              │
│  - Event Setup (define schema)                               │
│  - Image Capture/Upload                                      │
│  - Image Preview/Crop                                        │
│  - Data Verification (editable table)                        │
│  - Export Confirmation                                       │
└──────────────────────────┬──────────────────────────────────┘
                           │ POST /extract (image + schema)
                           │ POST /verify (reviewed rows)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    EXTRACTION LAYER                          │
│  (FastAPI on Render - Backend API)                           │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Request Handler (extract_route.py)                   │   │
│  │ - Validate image (size, format, readability)         │   │
│  │ - Route to OCR provider                              │   │
│  └──────────────┬───────────────────────────────────────┘   │
│                 │                                            │
│  ┌──────────────▼──────────────────────────────────────┐   │
│  │ OCR Provider Selector (ocr_service.py)              │   │
│  │ - Primary: GLM OCR (cheap, reliable)                │   │
    │   │
│  │         │   │
│  └──────────────┬───────────────────────────────────────┘   │
│                 │                                            │
│  ┌──────────────▼──────────────────────────────────────┐   │
│  │ Data Normalization (data_normalizer.py)             │   │
│  │ - Parse OCR output (markdown/HTML/JSON)             │   │
│  │ - Extract table structure                           │   │
│  │ - Map columns to schema                             │   │
│  │ - Calculate confidence scores per field             │   │
│  │ - Return: { rows, confidence, errors }              │   │
│  └──────────────┬───────────────────────────────────────┘   │
│                 │                                            │
│  ┌──────────────▼──────────────────────────────────────┐   │
│  │ Optional: Semantic Header Mapping (llm_mapper.py)   │   │
│  │ - If headers are unclear/handwritten                │   │
│  │ - Use StepFun 3.5 Flash via OpenRouter to map columns          │   │
│  │ - Only triggered if confidence < threshold          │   │
│  └──────────────┬───────────────────────────────────────┘   │
│                 │                                            │
│                 ▼                                            │
│  Response: { rows, confidence_scores, mapping_applied }    │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  PERSISTENCE LAYER                          │
│  (Supabase Postgres)                                         │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Schema:                                              │   │
│  │ - registers (id, name, event_type, schema_def)      │   │
│  │ - sessions (id, register_id, uploaded_at, status)   │   │
│  │ - rows (id, session_id, extracted_data, edited)     │   │
│  │ - audit_log (id, session_id, action, timestamp)     │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  Request: POST /export-db (eventName, rows)                │
│  - Upsert register if not exists                           │
│  - Create session entry                                    │
│  - Batch insert rows                                       │
│  - Log audit trail                                         │
│  Response: { session_id, rows_inserted, status }          │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Component Breakdown

#### **Frontend (React SPA)**
**Location:** `irys-web/` (Vercel)  
**Tech Stack:** React 19 + Vite + TypeScript + Tailwind + Radix UI

**Components:**
- `App.tsx` — Main router, session state management
- `EventSetup.tsx` — Event configuration (define columns, types)
- `ImageUpload.tsx` — Photo capture (mobile camera + file upload)
- `ImagePreview.tsx` — **NEW** Preview/crop before extraction
- `ExtractionLoading.tsx` — Single unified loading state
- `VerificationScreen.tsx` — Editable table, confidence indicators
- `ExportConfirmation.tsx` — **NEW** Confirmation page (not just toast)

**State Management:**
- React Context for session (eventName, schema, uploadedImage, extractedRows)
- Local state for UI (loading, errors, editing)
- No Redux needed (MVP scope)

**API Integration:**
- `POST /extract` — send image + schema, get back rows + confidence
- `POST /export-db` — send verified rows, confirm export
- Error handling + retry logic

#### **Backend API (FastAPI)**
**Location:** Backend on Render  
**Tech Stack:** FastAPI + Python 3.11 + Pydantic

**Core Modules:**

```
backend/
├── main.py                    # FastAPI app, routes
├── config.py                  # Environment, settings, provider selection
├── routes/
│   ├── __init__.py
│   ├── extract.py             # POST /extract endpoint
│   └── export.py              # POST /export-db endpoint
├── services/
│   ├── __init__.py
│   ├── ocr/
│   │   ├── __init__.py
│   │   ├── provider.py        # OCR provider interface
│   │   ├── glm_ocr.py         # GLM OCR implementation
│   │   ├── google_docai.py    # Google Document AI fallback
│   │   └── paddle_ocr.py      # PaddleOCR local fallback
│   ├── extraction/
│   │   ├── __init__.py
│   │   ├── normalizer.py      # Parse OCR output → structured data
│   │   ├── confidence.py      # Calculate confidence scores
│   │   └── mapper.py          # Column mapping logic
│   ├── llm/
│   │   ├── __init__.py
│   │   └── header_mapper.py   # Semantic column mapping (StepFun 3.5 Flash via OpenRouter)
│   └── database/
│       ├── __init__.py
│       ├── client.py          # Supabase connection
│       └── queries.py         # Insert, fetch, update operations
├── models/
│   ├── __init__.py
│   ├── request.py             # Request schemas (Pydantic)
│   ├── response.py            # Response schemas
│   └── domain.py              # Core data models (Row, Session, Register)
├── utils/
│   ├── __init__.py
│   ├── errors.py              # Custom exceptions
│   ├── logger.py              # Logging + structured output
│   └── validators.py          # Input validation
└── tests/
    ├── __init__.py
    ├── test_ocr.py            # OCR provider tests
    ├── test_extraction.py      # Normalization + confidence tests
    └── test_database.py        # Database integration tests
```

**Key Modules Explained:**

**`ocr/provider.py` (Interface)**
```
Abstract base: OCRProvider
- abstract method: extract(image: File, schema: Schema) → ExtractedData
- implementations: GLMOCRProvider, GoogleDocAIProvider, PaddleOCRProvider
- allows swapping providers without changing routes
```

**`extraction/normalizer.py`**
```
Converts OCR output (markdown/HTML/JSON) → standardized rows
- Handles different OCR output formats
- Extracts table structure
- Maps columns to schema
- Returns: rows[], errors[], warnings[]
```

**`extraction/confidence.py`**
```
Calculates per-field confidence scores
- OCR provider confidence (if provided)
- Schema validation confidence (does field match type?)
- Cross-field consistency (does data make sense together?)
- Returns: confidence_score per row (0-1)
```

**`llm/header_mapper.py`**
```
Uses StepFun 3.5 Flash (via OpenRouter) for semantic mapping
- Triggered only if: OCR headers unclear OR confidence < threshold
- Maps extracted headers → schema fields using LLM
- Cost-optimized: only on uncertain cases
- Returns: mapping[] + confidence
```

**`database/queries.py`**
```
Supabase operations:
- upsert_register(name, schema_def) → register_id
- create_session(register_id) → session_id
- batch_insert_rows(session_id, rows[]) → count
- log_audit(session_id, action, metadata) → audit_id
- get_sessions(register_id) → sessions[]
- get_rows(session_id) → rows[]
```

#### **Database (Supabase Postgres)**

**Schema:**

```sql
-- Registers: definitions of what we're tracking
CREATE TABLE registers (
  id UUID PRIMARY KEY,
  event_name TEXT NOT NULL UNIQUE,
  schema_definition JSONB NOT NULL,  -- {columns: [{name, type, required}]}
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Sessions: each time someone uploads a register
CREATE TABLE sessions (
  id UUID PRIMARY KEY,
  register_id UUID REFERENCES registers(id) ON DELETE CASCADE,
  uploaded_at TIMESTAMP DEFAULT NOW(),
  status TEXT CHECK (status IN ('pending', 'extracted', 'verified', 'exported')),
  confidence_average FLOAT,
  row_count INT,
  created_by TEXT,  -- username (nullable for MVP)
  notes TEXT
);

-- Rows: extracted data points
CREATE TABLE rows (
  id UUID PRIMARY KEY,
  session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
  row_number INT,  -- position in original table
  extracted_data JSONB NOT NULL,  -- {column_name: value}
  edited_data JSONB,  -- user edits (if any)
  confidence_scores JSONB,  -- {column_name: confidence_score}
  is_verified BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Audit log: who did what and when
CREATE TABLE audit_log (
  id UUID PRIMARY KEY,
  session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
  action TEXT NOT NULL,  -- 'uploaded', 'extracted', 'edited_row', 'exported'
  metadata JSONB,  -- additional context
  actor TEXT,  -- username or 'system'
  timestamp TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_sessions_register_id ON sessions(register_id);
CREATE INDEX idx_rows_session_id ON rows(session_id);
CREATE INDEX idx_audit_register_id ON audit_log(session_id);
```

**Why this schema:**
- Normalized (no data duplication)
- Audit trail built-in (complies with MEL requirements)
- Flexible (schema_definition is JSONB, can evolve)
- Queryable (easy to aggregate, filter, analyze)

#### **Deployment (Current)**
- **Frontend:** Vercel (React SPA, rewrite rules for SPA routing)
- **Backend:** Render (FastAPI, auto-deploy from git)
- **Database:** Supabase (managed Postgres, auto-backups)
- **Image Storage:** Vercel Blob (ephemeral, deleted after extraction)

---

## PART 2: USER FLOW (REFINED)

### 2.1 Complete User Journey

#### **Actor 1: Hub Staff (Data Entry)**

```
1. NAVIGATE TO IRYS
   └─ Open irys-web URL in browser
   └─ Land on "Select Event" screen (lists past registers)
      OR "New Event" button

2. SELECT OR CREATE EVENT
   └─ Option A: Select existing "Workshop Registration - Day 1"
      └─ Routes to UPLOAD
   └─ Option B: Create new event
      └─ Routes to EVENT SETUP

3. EVENT SETUP (if new)
   ┌─ Sees: "Define schema for this register"
   ├─ Inputs:
   │  - Event name: "Workshop Registration - Day 1"
   │  - Column 1: "Name" (text)
   │  - Column 2: "ID" (number)
   │  - Column (n)++ 
   ├─ Action: "INITIALIZE SESSION" button
   └─ Backend creates register + session entry
   └─ Routes to UPLOAD

4. UPLOAD REGISTER
   ┌─ Sees: "Upload Register" with session name
   ├─ Large drag-drop zone: "Tap to take photo OR drop image here"
   ├─ Actions:
   │  - Tap: Opens device camera (mobile)
   │  - Drop: Accepts JPEG, PNG, PDF
   │  - File picker: Click to browse
   ├─ On file selected:
   │  - Validate: Size < 50MB, format in (JPEG, PNG, PDF)
   │  - On success: Routes to IMAGE PREVIEW
   │  - On error: Toast "Invalid file. Please try again."
   └─ Waiting for input state

5. IMAGE PREVIEW (NEW)
   ┌─ Sees: Full-screen image preview
   ├─ Left side: Original image
   ├─ Right side: Crop controls (optional)
   ├─ Bottom: "This what you uploaded? YES / NO / RETAKE"
   ├─ If YES: Submit image for extraction
   ├─ If NO: Return to UPLOAD
   ├─ If RETAKE: Clear + return to UPLOAD
   └─ Routes to EXTRACTING on YES

6. EXTRACTING DATA (LOADING)
   ┌─ Sees: Single loading screen
   ├─ Spinner + "Running pipeline..."
   ├─ Backend process:
   │  - Send image to OCR provider (GLM)
   │  - Parse output (markdown/HTML/JSON)
   │  - Normalize to schema (map columns)
   │  - Calculate confidence scores
   │  - Optional: If unclear headers, use StepFun 3.5 Flash for mapping
   ├─ On success: Routes to VERIFICATION
   ├─ On error: 
   │  - Toast "Extraction failed: [reason]"
   │  - Button: "Retry extraction" or "Upload different image"
   └─ Max timeout: 30 seconds (fail gracefully)

7. VERIFICATION (DATA REVIEW)
   ┌─ Sees: Two-panel layout
   ├─ Left panel: Original image (for reference)
   ├─ Right panel: Editable data table
   │  - Columns: Name, ID, , etc.
   │  - Rows: Extracted data (n rows in screenshot)
   │  - Editable cells: User can click/tap to edit
   │  - Confidence badges: Green (high) / Yellow (medium) / Red (low)
   │  - "Add empty row" button (for manual additions)
   ├─ Top: "Verify Data | [X] rows"
   ├─ Bottom:
   │  - "← Back" button (return to UPLOAD)
   │  - "✓ Export Database" button (confirm + save)
   ├─ Interaction:
   │  - Click cell → inline editor (text input, date picker, etc.)
   │  - Edit → cell saves immediately (optimistic update)
   │  - Delete row → "Are you sure?" confirmation
   │  - Add row → blank row appended to table
   └─ Routes to EXPORT CONFIRMATION on "Export Database"

8. EXPORT CONFIRMATION (NEW)
   ┌─ Sees: Confirmation page
   ├─ Content:
   │  - "✓ Successfully exported"
   │  - "Session ID: [uuid]"
   │  - "Saved to: Workshop Registration - Day 1"
   │  - Summary table: quick view of what was saved
   ├─ Actions:
   │  - "← View database" (link to database)
   │  - "Start new register" (return to event selection)
   │  - "Upload same register again" (re-initialize session)
   ├─ 
   └─ End of session

HAPPY PATH TIMELINE: ~3-5 minutes
- Upload: <5 sec
- Preview: 20 sec
- Extraction: 5-15 sec (OCR latency)
- Verification: 60-90 sec (user review + edits)
- Export: 5 sec
```

#### **Actor 2: MEL Officer (Oversight + Export)**

```
1. NAVIGATE TO DASHBOARD
   └─ Open irys-web/dashboard (separate route, auth TBD)
   └─ Land on "Overview"

2. VIEW REGISTERS
   ┌─ Sees: List of all registers
   │  - Workshop Registration - Day 1 (3 sessions, 18 rows)
   │  - Workshop Registration - Day 2 (2 sessions, 12 rows)
   │  - Student Onboarding (5 sessions, 47 rows)
   ├─ Columns: Event name, sessions, total rows, last updated
   └─ Click register → VIEW SESSIONS

3. VIEW SESSIONS (for one register)
   ┌─ Sees: All uploads of "Workshop Registration - Day 1"
   │  - Session 1: Uploaded 2026-02-05 10:23 AM | 6 rows | Status: Exported
   │  - Session 2: Uploaded 2026-02-05 02:45 PM | 5 rows | Status: Exported
   │  - Session 3: Uploaded 2026-02-05 05:10 PM | 7 rows | Status: Extracted
   ├─ Columns: Timestamp, row count, status, actions
   ├─ Actions per session:
   │  - View rows (in-page table)
   │  - Download CSV
   │  - Download PDF
   │  - View audit log
   │  - Re-export (if failed before)
   └─ Click session → VIEW ROWS + AUDIT TRAIL

4. VIEW ROWS (for one session)
   ┌─ Sees: All rows from a session (editable, for corrections)
   ├─ Can edit if needed (correction workflow)
   ├─ Can delete rows (with confirmation)
   ├─ Can add notes/comments
   ├─ Audit trail on right: who extracted, when, confidence score
   └─ Click "Download CSV" → Export as CSV file

5. EXPORT DATA
   ┌─ Options:
   │  A) Single session → CSV
   │  B) All sessions of one register → aggregated CSV
   │  C) Date range across all registers → filtered CSV
   ├─ MEL officer chooses scope
   ├─ System generates + downloads file
   └─ Audit log entry: "MEL Officer exported [X] rows"
```

### 2.2 Error Handling Flows

#### **Image Upload Validation**

```
User uploads file
├─ Check: File size < 50MB?
│  └─ No → Error toast: "File too large. Max 50MB."
│  └─ Yes → Continue
├─ Check: File format in (JPEG, PNG, PDF)?
│  └─ No → Error toast: "Unsupported format. Use JPG, PNG, or PDF."
│  └─ Yes → Continue
├─ Check: File is readable (not corrupted)?
│  └─ No → Error toast: "File appears corrupted. Try again."
│  └─ Yes → Routes to IMAGE PREVIEW
```

#### **OCR Extraction Failure**

```
Backend runs OCR on image
├─ OCR returns no data?
│  └─ Error: "Could not read image. Please ensure image is clear."
│  └─ Action: "Retry with better photo" or "Upload different image"
│
├─ OCR returns partial data (e.g., only 3 of 6 columns)?
│  └─ Confidence score low
│  └─ Optional: Trigger StepFun 3.5 Flash semantic mapping
│  └─ Present extracted data to user with yellow warnings
│  └─ User can proceed or retry
│
└─ OCR times out (> 30 seconds)?
   └─ Error: "Extraction took too long. Please try again."
   └─ Action: "Retry" or "Upload different image"
```

#### **Database Export Failure**

```
User clicks "Export Database"
├─ Validate: All required fields filled?
│  └─ No → Error toast: "Missing required fields: [Name, ID]"
│  └─ Yes → Continue
│
├─ Attempt insert to Supabase
├─ Success → Routes to EXPORT CONFIRMATION
│
└─ Failure (network error, database error, etc.)
   └─ Error toast: "Export failed. Please retry."
   └─ Action: "Retry export" (idempotent)
   └─ If retry fails: "Contact support. Session ID: [uuid]"
```

### 2.3 Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                         USER (Staff/MEL)                         │
└──────────────────────────┬───────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
   [UPLOAD]         [PREVIEW]          [VERIFY]
   (Image)          (Confirm)          (Edit)
        │                  │                  │
        └──────────────────┴──────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │  FRONTEND STATE        │
              │  (React Context)       │
              │ - eventName            │
              │ - schema               │
              │ - image                │
              │ - extractedRows        │
              │ - userEdits            │
              └────────────┬───────────┘
                           │
              ┌────────────▼───────────┐
              │  POST /extract         │
              │ (image + schema)       │
              └────────────┬───────────┘
                           │
              ┌────────────▼───────────────────┐
              │  BACKEND EXTRACTION PIPELINE   │
              │                                │
              │  1. Validate image             │
              │  2. Select OCR provider        │
              │  3. Run OCR                    │
              │  4. Normalize output           │
              │  5. Calculate confidence       │
              │  6. Optional: LLM mapping      │
              │  7. Return rows + confidence   │
              └────────────┬───────────────────┘
                           │
              ┌────────────▼──────────────┐
              │  FRONTEND STATE UPDATE    │
              │ - extractedRows[]         │
              │ - confidenceScores[]      │
              │ - showVerificationScreen  │
              └────────────┬──────────────┘
                           │
                           ▼
                   [VERIFICATION UI]
                (User reviews + edits)
                           │
              ┌────────────▼─────────────┐
              │  POST /export-db         │
              │ (eventName + rows)       │
              └────────────┬─────────────┘
                           │
              ┌────────────▼────────────────┐
              │  BACKEND PERSISTENCE       │
              │                            │
              │  1. Upsert register        │
              │  2. Create session entry   │
              │  3. Batch insert rows      │
              │  4. Log audit trail        │
              │  5. Return confirmation    │
              └────────────┬───────────────┘
                           │
              ┌────────────▼──────────────┐
              │  FRONTEND CONFIRMATION    │
              │  "6 rows exported"        │
              │  [Session ID]             │
              │  [Next steps]             │
              └────────────┬──────────────┘
                           │
                           ▼
              [EXPORT CONFIRMATION PAGE]
              (End of flow / Restart)
```

---

## PART 3: RELIABILITY FOUNDATIONS

### 3.1 Error Handling Strategy

**Principle:** Fail gracefully. Always give user an escape route.

**For OCR Extraction:**
- Primary: GLM OCR (fast, cheap)


**For Database Export:**
- Validate data schema before attempting insert
- Use transactions (insert register + session + rows atomically)
- On failure: Retry once automatically. If still fails, return session ID + error message.
- User can retry manually without losing data.

**For Network Issues:**
- Frontend has 45-second timeout on `/extract` endpoint
- If timeout: Show "Taking longer than expected. Retry?"
- On retry: Resend same image (idempotent operation)

### 3.2 Logging + Observability

**Backend logs (FastAPI):**
```
Each request:
- Timestamp
- Request ID (UUID, used for debugging)
- Endpoint
- User (nullable for MVP)
- OCR provider selected
- OCR response time
- Confidence scores (min/max/avg)
- Errors (if any)
- Status code
```

**Database audit log:**
```
Each operation:
- Session ID
- Action (uploaded, extracted, edited_row_X, exported)
- Actor (username or 'system')
- Metadata (OCR provider used, confidence, row count)
- Timestamp
```

**Metrics to track (simple, MVP level):**
- Extraction success rate (%)
- Average extraction time (seconds)
- Average confidence score
- Fallback rate (how often did we need Google or PaddleOCR?)
- Export success rate (%)

### 3.3 Data Integrity

**Row-level validation:**
- Name: Must be non-empty string
- ID: Must be numeric
- Time-in/Time-out: Must be valid time format
- All required fields must be present before export

**Schema consistency:**
- Register schema is locked at creation (can't change columns mid-way)
- Extraction must return columns matching schema
- User edits must still conform to schema types

**Idempotency:**
- `/extract` endpoint is idempotent (same image → same result)
- `/export-db` endpoint is idempotent (same rows → same result)
- Prevents double-exports if user clicks button twice

---

## PART 4: DEPLOYMENT + OPERATIONS (MVP)

### 4.1 Current Deployment

```
┌──────────────────┐         ┌──────────────────┐         ┌──────────────────┐
│   Vercel         │         │   Render         │         │   Supabase       │
│  (Frontend)      │────────▶│  (Backend API)   │────────▶│  (Database)      │
│                  │         │                  │         │                  │
│ React SPA        │         │ FastAPI Python   │         │ Postgres         │
│ Vite build       │         │ auto-deployed    │         │ auto-backed up   │
│ Tailwind CSS     │         │ from git         │         │                  │
└──────────────────┘         └──────────────────┘         └──────────────────┘
        │                            │                            │
        └────────────────────────────┴────────────────────────────┘
              .env configuration (API URL, Supabase keys)
```

### 4.2 Environment Configuration

**Frontend (.env.local):**
```
VITE_BACKEND_API_URL=https://irys-api.onrender.com
VITE_APP_NAME=Irys
```

**Backend (.env):**
```
# Server
API_PORT=8000
API_HOST=0.0.0.0
ENV=production

# OCR Provider Selection
OCR_PRIMARY_PROVIDER=glm  # glm 


# GLM OCR (primary)
GLM_API_KEY=xxxx
GLM_MODEL=glm-4v-flash  # or glm-4v

# LLM for header mapping
OPENROUTER_API_KEY=xxxx
OPENROUTER_MODEL=stepfun-3.5-flash

# Supabase
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=xxxx (service role, kept private)

# Logging
LOG_LEVEL=INFO  # DEBUG | INFO | WARNING | ERROR
```

### 4.3 Health Checks + Monitoring (Simple MVP)

**Vercel:** Auto-checks frontend deployment, notifies on build failure  
**Render:** Health check endpoint `/health` returns `{ status: "ok", timestamp }`  
**Supabase:** Built-in monitoring + backups  

**Manual checks (daily):**
- Visit irys-web URL, upload test image, confirm extraction works
- Check Render logs for errors
- Check Supabase for backup status

---

## PART 5: SCALING PATHS (Post-MVP)

**What you'll add as you learn from real usage:**

### 5.1 Phase 2 (Apr-Jun 2026)
- **Auth + role-based access** (staff can only see their uploads, MEL officer sees all)
- **Multi-hub support** (different hubs have separate data spaces)
- **Confidence-driven workflows** (auto-verify high-confidence rows, flag low-confidence for review)
- **Better OCR accuracy** (fine-tune model for handwritten registers)

### 5.2 Phase 3 (Jul+ 2026)
- **Async job queue** (extract → job → notify when done, instead of long request)
- **Batch processing** (upload 10 images at once, process in background)
- **Analytics dashboard** (how many registers, trends, error rates)
- **Export to Excel/PDF** (beyond just CSV)
- **API for external integrations** (other tools can query Irys data)

### 5.3 Connection to Gaia
- **OCR patterns learned here** → Apply to emissions bill extraction
- **Database schema patterns** → Gaia uses same normalized approach
- **Confidence scoring** → Gaia needs it for emissions data confidence
- **Audit trail infrastructure** → Carbon accounting requires provenance

---

## PART 6: TESTING STRATEGY (MVP Scope)

### 6.1 What to Test

**Backend unit tests:**
```
✓ OCR provider interface (mock providers, test fallback logic)
✓ Data normalization (test markdown → rows conversion)
✓ Confidence scoring (test calculation logic)
✓ Schema validation (test column type enforcement)
✓ Database queries (test CRUD operations)
```

**Frontend integration tests:**
```
✓ Event setup flow (create schema, see it saved)
✓ Image upload (valid + invalid files)
✓ Extraction call (mock API, test loading state)
✓ Verification UI (edit rows, add row, delete row)
✓ Export call (mock API, test confirmation)
```

**Manual end-to-end test:**
```
✓ Real image upload → extraction → verification → export → Supabase confirmation
✓ Test with hub staff + MEL officer
✓ Test on mobile + desktop browsers
✓ Test error cases (bad image, network failure, validation error)
```

### 6.2 Test Priorities (MVP)
1. **OCR accuracy** — does extraction get the right data? (manual testing with real registers)
2. **Database integrity** — does data actually save to Supabase correctly?
3. **User flow happy path** — can staff complete the full flow?
4. **Error recovery** — can user recover from extraction failure?

---

## SUMMARY TABLE: MVP Scope vs. Post-MVP

| Feature | MVP | Post-MVP |
|---------|-----|----------|
| **Users** | Hub staff + MEL officer (no auth) | Auth + role-based access |
| **Registers** | Single hub (UG) | Multi-hub support |
| **OCR** | GLM primary + fallbacks | Fine-tuned model + confidence-driven verification |
| **Database** | Direct request/response | Async job queue |
| **Data Export** | CSV only | CSV, Excel, PDF, API |
| **Audit Trail** | Basic logging | Rich audit + change history |
| **Analytics** | None | Dashboard with trends |
| **Scaling** | 1-10 registers/month | 100+ registers/month |

---

## EXECUTION CHECKLIST (Feb-Mar 2026)

- [ ] Backend database schema deployed to Supabase
- [ ] FastAPI routes implemented (`/extract`, `/export-db`)
- [ ] OCR provider selection + fallback logic working
- [ ] Data normalization pipeline tested
- [ ] Frontend components built (EventSetup, Upload, Preview, Verify, Confirmation)
- [ ] Frontend ↔ Backend integration complete
- [ ] Image Preview screen added
- [ ] Export Confirmation page added
- [ ] End-to-end flow tested with real users (hub staff + MEL officer)
- [ ] Deployed to production (Vercel + Render + Supabase)
- [ ] Monitoring + logging in place
- [ ] Handoff documentation ready

---

## Key Principles (Reference)

1. **Fail gracefully** — Always give users an escape route. Never trap them in an error state.
2. **Audit everything** — MEL officer needs to know who did what and when.
3. **Keep it simple** — MVP solves the immediate problem. Innovation comes later.
4. **Learn from real users** — Ship MVP, watch how hub staff + MEL officer use it, iterate.
5. **Connect to Gaia** — Extract patterns (OCR, DB schema, confidence scoring) that apply to emissions infrastructure.

---

**Document Owner:** Davis  
**Last Updated:** Feb 12, 2026  
**Next Review:** After MVP ships (Apr 2026)
