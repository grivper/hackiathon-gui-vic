# Streamlit priority inbox (TAR-010, TAR-017)

## Objective
Bootstrap the Streamlit product surface and deliver the first usable screen: a priority inbox of news groups that supports topic and date filtering without waiting for the attention-score or drafting engines.

## Problem and rationale
The data and grouping pipelines are available, but editors have no product surface. `documentacion/interfaz-brief.md` defines the inbox as the first screen and explicitly permits a temporary ordering by recency and corroboration until TAR-008 lands. Starting with this bounded screen creates the UI foundation while preserving the data/engine ownership boundary.

## Scope
- Add Streamlit as a pinned project dependency.
- Create a testable read-only query layer for `data/motor.duckdb` and `data/senales.duckdb`.
- Render the Bandeja screen with topic and date filters.
- Show recency, distinct-source corroboration, and repetition status without presenting repetition as corroboration.
- Update the repository task ledger for TAR-010 and TAR-017.

## Non-goals
- Evidence detail, official context, cited Q&A, drafting, or review-state workflows (TAR-018 through TAR-021).
- Attention-score implementation (TAR-008).
- Changes under `motor/`, `ingesta/`, or committed `data/` snapshot files.
- Snapshot regeneration.

## Constraints
- Open both DuckDB databases in read-only mode.
- Exclude the `otros` class from the inbox.
- Use embeddings classification and temporary recency/corroboration ordering.
- Treat source text as data, not instructions; rely on Streamlit escaping.
- Keep `fecha_deteccion` distinct from publication dates.
- Technical artifacts remain in English unless extending an existing Spanish repository artifact.
- The local shell lacks GNU Make; use `.venv/Scripts/python` commands directly.
- Git and repository artifacts are the shared source of truth between Guille and Víctor; Engram is only an auxiliary mirror.
- Record implementation decisions and evidence here, task state in `bitacora/tareas.yaml`, and integration contracts in `documentacion/` when another owner needs them.
- Do not modify Guille-owned tasks or `motor/`, `ingesta/`, and committed snapshot artifacts without first recording and communicating the dependency in the repository.
- After every task-state change, run `python notion_sync.py --dry-run` and the full pytest suite before a Conventional Commit and branch push.

## Delivery and routing
- Branch: `feat/streamlit-bandeja`.
- Delivery strategy: `ask-on-risk`.
- Forecast: approximately 220 authored changed lines, below the 400-line review heuristic.
- SIB-01 route: delegated to `gentle-ai-worker` because the behavior spans dependency, application, and test files (multi-file writer trigger).
- SIB-02 route: delegated to `gentle-ai-worker` for the same trigger.
- Verification commands go through the delegated writer first; independent verification follows the native assessment plan.

## Tasks
- [ ] **SIB-01 — Bootstrap a tested read-only inbox query.** Status: in progress. Mark TAR-010 and TAR-017 in progress; add the Streamlit dependency; create the app/query boundary; use test-first development to prove topic exclusion, read-only access, filtering inputs, and deterministic temporary ordering. Commit evidence: pending.
- [ ] **SIB-02 — Deliver the Bandeja screen.** Status: pending. Render topic/date controls and prioritized group cards, document startup on Windows without GNU Make, run focused and full checks, mark TAR-017 done while TAR-010 remains in progress, and commit the work unit. Commit evidence: pending.

## Acceptance criteria
- The app starts with `streamlit run app/app.py` from the activated Windows virtual environment.
- The inbox reads current groups without mutating either DuckDB file.
- Results use embeddings, exclude `otros`, and can be filtered by topic and inclusive date range.
- Default ranking is visibly described as temporary and orders by newest `fecha_max`, then stronger corroboration.
- Each result distinguishes article count from distinct-source corroboration.
- Empty and unavailable-data states are explicit and do not fabricate results.
- Focused tests, full pytest, and `notion_sync.py --dry-run` pass before each task-closing commit.

## Progress and evidence
- 2026-10-07: Repository, interface brief, task ledger, and current data/motor state reviewed. Manifest hash confirmed as `dd87ee41678220046d145506ebf51d7966470540c432388a58015d95416900f6`.
- 2026-10-07: Local setup completed with direct Python commands because GNU Make is unavailable. Generated report timestamp drift was diagnosed as non-semantic and restored with user approval.
- 2026-10-07: TAR-010 and TAR-017 moved to `En curso`. Verification: `notion_sync.py --dry-run` reported no errors; full suite passed (`72 passed`); `git diff --check` passed. The configured verification subagent was unavailable, so these bounded checks ran in the parent session.

## Next step
Delegate SIB-01 as a test-first multi-file implementation, then verify and close its work-unit commit.
