# Irys Session Memory (Handoff)

## Date
- February 13, 2026

## What Was Implemented

1. User flow upgrades
- Added pre-extraction review stage: `capture -> review -> verify`.
- Added in-app exported data inspection (History screen):
  - List export batches for current event.
  - Open and render rows for selected export batch.

2. Session flow behavior
- Event created once, then loop:
  - Capture photo -> review -> extract -> verify/edit -> save.
- Added:
  - `Save & Continue`
  - `Save & End Session`
  - Capture screen session stats (`photosSaved`, `rowsSaved`).

3. Export tracking for in-app history
- Backend now tags exported rows with system columns:
  - `_irys_export_id`
  - `_irys_exported_at`
- Added backend endpoints:
  - `GET /exports/{event_name}`
  - `GET /exports/{event_name}/{export_id}`

4. Reliability work
- Removed frontend lint blockers:
  - eliminated explicit `any` usage with shared types (`irys-web/src/types.ts`).
  - fixed verification state-sync lint issue.
- Added tests:
  - Backend API tests (`tests/backend/*.py`) for health/export/history contracts.
  - Frontend flow tests (`irys-web/tests/App.flow.test.tsx`) for:
    - review before extraction
    - retake from review without extract call
    - history load/render

5. GLM-only extraction pipeline (important decision)
- API extraction path now uses only GLM-OCR (`extract_glm`).
- Removed provider switching logic (DocAI/Paddle no longer used by runtime API flow).
- Updated config/deploy docs to reflect GLM-only.

6. Startup engine gate (new UX)
- Added startup screen in frontend:
  - loading animation
  - text: **"Starting extraction engine"**
  - retry button if warmup fails
- App now blocks entry into event setup until backend warmup reports ready.
- Added backend warmup endpoint:
  - `POST /warmup`
- Added backend warmup state in:
  - `GET /health`
  - `GET /`

7. CORS fix for extraction failure
- Added `5173` origins to backend default CORS allowlist to avoid browser `Failed to fetch` during local dev.

## Current Status

- Frontend:
  - `npm run lint` passes.
  - `npm run build` passes.
  - `npm run test` passes (3/3 in `App.flow.test.tsx`).

- Backend:
  - `python -m pytest tests/backend -q` passes (8 passed).
  - `GET /health` currently returns:
    - `status: ok`
    - `ocr_provider: glm`
    - warmup state included
  - `POST /warmup` returns `200` with `{ ok: true, ocr_provider: "glm" }`.

## Files Added/Updated (Key)

- Backend
  - `api.py`
  - `db_utils.py`
  - `extract_glm.py`
  - `.env.example`
  - `requirements.txt`
  - `render.yaml`
  - `tests/backend/test_api_health.py`
  - `tests/backend/test_export_endpoints.py`
  - `tests/backend_unittest/test_api_contracts.py`

- Frontend
  - `irys-web/src/App.tsx`
  - `irys-web/src/types.ts`
  - `irys-web/src/components/ReviewScreen.tsx`
  - `irys-web/src/components/HistoryScreen.tsx`
  - `irys-web/src/components/CaptureScreen.tsx`
  - `irys-web/src/components/VerificationScreen.tsx`
  - `irys-web/src/components/StartupScreen.tsx`
  - `irys-web/tests/App.flow.test.tsx`
  - `irys-web/tests/setup.ts`
  - `irys-web/vitest.config.ts`
  - `irys-web/package.json`

## Known Notes / Residuals

- Backend still uses `@app.on_event("startup")`, which raises a FastAPI deprecation warning (lifespan API is preferred later).
- Old exports created before `_irys_export_id` tagging may not appear in grouped history view.
- Legacy DocAI/Paddle extractor files were removed; runtime and repository are GLM-only for extraction.

## Suggested Immediate Next Steps

1. Optional cleanup
- Remove unused OCR files and docs references if you want a strict GLM-only codebase physically (not just runtime).

2. Add dedicated extraction completion screen (if still desired)
- Current behavior goes directly to verification; no separate completion page yet.

3. Hard-refresh browser after pulling latest changes
- Ensures startup gate + new flow scripts are loaded.

## User Note (Personal Feedback)

- User said:
  - "Codex is awesome."
  - "I appreciate the help you're giving me very much."
  - Building with Codex feels less stressful and avoids getting stuck on bugs for long.

## User Vision and Direction (Important)

- User is learning to build real problem-solving products, starting with software.
- User shipped first app: **Atmo** (`atmo-v2.vercel.app`), an AI climate Q&A app, primarily as proof of execution from concept to deployed product.
- User is proud of shipping Atmo and sees **Irys** as stronger problem-solution fit:
  - solves manual data entry + data centralization.
- User explicitly does **not** want to depend entirely on vibecoding.
- User wants to understand code and logic deeply, contribute technical ideas, optimize systems, and write solid code.
- Current skill target:
  - stronger software engineering mindset,
  - learn TypeScript deeply (currently basic Python foundation).
- Reflection on current build style:
  - Atmo and Irys started with direct coding and less upfront planning,
  - resulted in messy/stacked architecture,
  - user now wants architecture-first/product-engineering discipline for paid products.
- Long-term aspiration:
  - combine **product engineering** + **applied AI research**,
  - build non-conventional, defensible, high-quality products,
  - pursue novel/ingenious methods rather than saturated conventional builds.
