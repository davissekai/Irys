# IRYS ARCHITECTURE MVP v2
## Lean, Robust Internal MVP Plan

**Version:** 2.0 (Trimmed)
**Date:** February 12, 2026
**Goal:** Reliable internal deployment for staff use now, with clean path to production scale later.

---

## 1) Scope Boundary

### In Scope (Now)
- Reliable end-to-end workflow for staff:
  - Setup event schema
  - Upload/capture register image
  - Run extraction
  - Verify/edit extracted rows
  - Export to database successfully
- Strong failure handling and retry UX
- Basic auditability and operational visibility
- Tight alignment with existing code and deployment

### Out of Scope (Later)
- Full async job queue
- Full auth/RBAC and multi-tenant permissions
- Advanced analytics dashboard
- Heavy backend folder re-architecture before stability proof
- Full confidence-scoring engine across all fields

---

## 2) Current Architecture Baseline (As-Built)

### Frontend
- `irys-web` React + Vite + TypeScript + Tailwind
- Core flow already exists in `irys-web/src/App.tsx`:
  - `setup -> capture -> verify`
  - Calls `POST /extract`
  - Calls `POST /export-db`

### Backend
- FastAPI service in `api.py`
- OCR provider:
  - GLM (`extract_glm.py`) only
- Optional semantic mapping in `llm_mapper.py`
- Persistence in `db_utils.py` (dynamic per-event tables)

### Deployment
- Frontend: Vercel (`irys-web`)
- Backend: Render (`api.py` via uvicorn)
- Database: Supabase Postgres

---

## 3) Target MVP v2 Architecture (Lean)

```text
Browser (Staff)
  -> POST /extract (image + columns)
FastAPI API (Render)
  -> OCR provider (GLM only)
  -> Normalize + optional semantic header map
  -> Return rows + extraction metadata
Browser verification UI (edit rows)
  -> POST /export-db (eventName + rows + idempotency_key)
FastAPI
  -> Validate payload
  -> Persist atomically
  -> Write audit log
Supabase Postgres
```

Design intent:
- Keep sync extraction for MVP
- Harden request lifecycle, validation, idempotency, and observability
- Introduce minimal normalized metadata tables without overhauling everything

---

## 4) Data Model (MVP v2)

### Keep
- Existing row payload flexibility (JSON-like row structures)

### Add (Minimal normalized metadata)
1. `events`
- `id` (uuid pk)
- `event_name` (text unique)
- `schema_definition` (jsonb)
- `created_at`

2. `sessions`
- `id` (uuid pk)
- `event_id` (fk -> events.id)
- `status` (`extract_started|extract_succeeded|extract_failed|export_succeeded|export_failed`)
- `ocr_provider`
- `row_count`
- `error_message` (nullable)
- `created_at`, `updated_at`

3. `audit_log`
- `id` (uuid pk)
- `session_id` (fk -> sessions.id)
- `action` (text)
- `metadata` (jsonb)
- `created_at`

4. `export_idempotency`
- `id` (uuid pk)
- `idempotency_key` (text unique)
- `session_id` (fk -> sessions.id)
- `request_hash` (text)
- `created_at`

Note:
- Dynamic per-event tables can remain temporarily to avoid migration risk.
- Once stable, move to a single normalized `rows` table.

---

## 5) API Contract (MVP v2)

### `GET /health` (new)
- Returns: `{"status":"ok","timestamp":"...","version":"..."}`

### `POST /extract` (existing, hardened)
Request:
- multipart `file`
- form `columns` (JSON array)
- optional `eventName`

Response:
- `session_id`
- `table: { headers, rows }`
- `row_count`
- `column_count`
- `ocr_provider`
- optional `warnings[]`

Behavior:
- Validate image type/size early
- Create session record at start
- Update session status on success/failure

### `POST /export-db` (existing, hardened)
Request:
- `eventName`
- `rows`
- `session_id`
- `idempotency_key`

Response:
- `success`
- `session_id`
- `rows_inserted`
- `message`

Behavior:
- Reject invalid payloads with clear messages
- Enforce idempotency on `idempotency_key`
- Transactional write + audit log entry

---

## 6) Reliability Requirements (MVP v2)

### Validation
- File type allowlist: `image/jpeg`, `image/png`, `image/webp`, `application/pdf` (if needed)
- File size cap (e.g., 10 MB)
- Required columns non-empty
- Export rows must be array of objects

### Timeouts and retries
- Keep extraction timeout env-driven (`EXTRACT_TIMEOUT_SECONDS`)
- Frontend retry path for extraction failure
- Export retry safe via idempotency key

### Error handling
- Standard error shape from API:
  - `code`
  - `message`
  - `request_id`
- User-facing messages stay simple; logs stay detailed

---

## 7) Observability (MVP v2)

### Backend structured logs
Per request log:
- `request_id`
- endpoint
- status_code
- duration_ms
- session_id (if available)
- ocr_provider
- row_count
- error_code (if any)

### Audit events (minimum)
- `extract_started`
- `extract_succeeded`
- `extract_failed`
- `export_started`
- `export_succeeded`
- `export_failed`

### KPI checks (manual dashboard or SQL for now)
- Extraction success rate
- Export success rate
- Median extraction duration
- Top extraction failure reasons

---

## 8) Frontend Adjustments (MVP v2)

1. Add explicit error states for:
- invalid image
- timeout
- empty extraction result
- export failure

2. Carry `session_id` from extraction to export

3. Generate and send `idempotency_key` on export

4. Keep current 3-stage flow (`setup/capture/verify`)
- No extra confirmation page required for MVP
- Toast/banner + clear success message is enough

5. Ensure env names are consistent:
- `VITE_API_BASE_URL`
- `VITE_API_TIMEOUT_MS`

---

## 9) Delivery Plan (1-2 Weeks)

### Phase A: Contract + Hardening (2-3 days)
- Add `/health`
- Add request IDs
- Standardize response/error schema
- Add input validation on `/extract` and `/export-db`

### Phase B: Session/Audit Persistence (2-3 days)
- Add `events`, `sessions`, `audit_log`, `export_idempotency`
- Wire session lifecycle in `/extract`
- Wire idempotent export in `/export-db`

### Phase C: Frontend Integration (2 days)
- Propagate `session_id`
- Send `idempotency_key`
- Improve failure/retry UX states

### Phase D: Testing + Pilot (2-3 days)
- Backend tests for extract/export happy and fail cases
- Export idempotency tests
- End-to-end test with real workplace samples
- Staff pilot and bugfix pass

---

## 10) Definition of Done (Internal MVP)

- Staff can complete full flow repeatedly without data loss
- Duplicate export clicks do not duplicate records
- Every extraction/export attempt has session + audit trail
- Clear operator-facing errors and retry path
- Health endpoint and logs allow fast debugging
- Pilot users can use it without developer supervision

---

## 11) Post-MVP Upgrade Path

When usage grows, add in this order:
1. Auth + role separation
2. Move dynamic event tables to normalized `rows` table
3. Async extraction queue for long jobs
4. Analytics and reporting
5. External API integrations

---

## 12) Immediate Next Build Tasks

1. Add `/health` endpoint + request IDs in `api.py`
2. Define DB migration SQL for `events/sessions/audit_log/export_idempotency`
3. Update `/extract` to create and return `session_id`
4. Update `/export-db` to accept `session_id` + `idempotency_key`
5. Update frontend request payloads in `irys-web/src/App.tsx`
6. Add 6 core tests (extract success/fail, export success/fail, idempotency, validation)

This keeps the MVP robust for workplace staff while avoiding premature platform complexity.
