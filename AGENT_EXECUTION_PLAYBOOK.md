# Agent Execution Playbook
## A Practical Operating System for Shipping Reliable Software

Use this with any AI coding agent to get consistently high-quality outcomes.

---

## 1) Core Philosophy

1. Build for user outcomes, not just code completion.
2. Prefer clarity over cleverness.
3. Optimize for momentum with guardrails.
4. Small robust steps beat big fragile rewrites.
5. Every change must be explainable by intent, tradeoff, and test evidence.

---

## 2) Standard Work Cycle

For every task, follow this loop:

1. Understand
- Restate the user goal in one sentence.
- Identify constraints (time, platform, existing architecture).
- Identify what "done" means.

2. Ground
- Inspect actual code/files before proposing changes.
- Confirm current behavior from source, not memory.
- Find likely failure points and dependencies.

3. Decide
- Choose minimal viable approach first.
- State tradeoffs and why this choice is best now.
- Avoid introducing architecture not needed for the current stage.

4. Implement
- Make targeted edits.
- Keep interfaces stable unless change is required.
- Keep code legible and typed.

5. Verify
- Run lint/build/tests.
- Add/adjust tests for changed behavior.
- Validate runtime behavior when relevant.

6. Report
- What changed.
- Why it changed.
- Evidence it works.
- Remaining risks/next steps.

---

## 3) Problem-Solving Heuristics

1. Fix root causes first
- Example: browser "Failed to fetch" often means CORS/config mismatch, not OCR logic failure.

2. Remove decision branches you don't need
- If product choice is GLM-only, remove docai/paddle runtime branching.

3. Design by user flow state machine
- Model app as explicit states and transitions.
- Example: `booting -> setup -> capture -> review -> verify -> history`.

4. Reliability before novelty
- For MVP: robust error handling and idempotency beat advanced architecture.

5. Defer complexity intentionally
- Keep a clear "now vs later" boundary.

---

## 4) Architecture-First Prompting Pattern

Use this exact prompt style with agents:

1. Goal
- "Implement X so users can Y."

2. Scope
- "In scope: A, B. Out of scope: C, D."

3. Constraints
- "Keep existing flow except Z."

4. Acceptance criteria
- "Done when tests pass and behavior N, M are observable."

5. Verification commands
- "Run lint/build/tests and show results."

This prevents vague implementation and reduces rework.

---

## 5) Code Quality Rules

1. Types
- Avoid `any`.
- Define shared API/data types centrally.

2. State management
- Avoid effect-driven state loops that cause cascades.
- Prefer controlled inputs or keyed remount where appropriate.

3. API contracts
- Keep request/response explicit and stable.
- Return actionable error details.

4. Backward-safe evolution
- Add new fields/endpoints without breaking existing consumers.

5. Observability
- Include health/warmup/status endpoints for operational clarity.

---

## 6) Testing Strategy (Lean but Effective)

Always maintain:

1. Lint gate
- Static quality and hook correctness.

2. Build gate
- Type and bundling integrity.

3. Backend contract tests
- Validate endpoint success + failure contracts.

4. Frontend critical-flow tests
- Test user-path states, not just isolated helpers.

Focus first on critical user paths, then widen coverage.

---

## 7) Mobile-First UX Rule

When a view has two dense panes:
- Mobile: stack vertically, primary content first.
- Desktop: side-by-side.

Design for thumb-driven scanning and editing, then scale up to desktop.

---

## 8) Release Readiness Checklist

Before shipping:

1. Flow sanity
- Startup, happy path, failure/retry path all work.

2. Contract sanity
- API returns expected shape on success/failure.

3. Data sanity
- No duplicate inserts from retry/rapid-click behavior.

4. Ops sanity
- Health endpoint works.
- Warmup or startup readiness behavior is clear.

5. Test sanity
- lint/build/tests all green.

---

## 9) Anti-Vibecoding Guardrails

Do not accept:
- "It should work" without verification.
- hidden magic behavior without docs/types.
- massive unscoped rewrites for small goals.
- skipping tests because feature "looks okay."

Require:
- explicit plan,
- explicit interfaces,
- explicit evidence.

---

## 10) Debugging Protocol

When a bug appears:

1. Reproduce
- Capture exact user symptom and route/state.

2. Localize
- Determine: frontend state issue, API issue, infra/config issue, or data issue.

3. Confirm with evidence
- Logs, endpoint responses, failing tests.

4. Fix minimally
- Patch cause, not surface symptom.

5. Add regression test
- Ensure same bug cannot silently return.

---

## 11) Collaboration Contract for Agents

Ask the agent to always provide:

1. Current understanding.
2. Planned edits before editing.
3. Files changed.
4. Verification run and results.
5. Remaining risks.

This keeps work auditable and legible.

---

## 12) Reusable Task Template

Copy/paste this into any agent:

```text
Goal:
[one-sentence user outcome]

Scope:
In: [...]
Out: [...]

Constraints:
- Keep existing architecture unless explicitly changed.
- Minimize diff surface.
- Add/adjust tests for changed behavior.

Deliverables:
1) Code changes
2) Test updates
3) Verification outputs
4) Concise change summary with risks

Acceptance:
- lint/build/tests pass
- behavior [X,Y,Z] confirmed
```

---

## 13) Product Engineering Mindset

For every feature:

1. User problem
- What friction disappears?

2. Business value
- Why this now?

3. Reliability impact
- What can fail and how do users recover?

4. Technical debt impact
- What did we simplify or complicate?

5. Measurable success
- Which metric should move?

---

## 14) What Makes This Approach Effective

1. It balances speed and rigor.
2. It anchors decisions in user flow and runtime reality.
3. It minimizes regressions via lightweight but strict gates.
4. It keeps architecture intentional, not accidental.
5. It scales from solo MVPs to team delivery.
