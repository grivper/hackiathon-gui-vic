# Streamlit priority inbox (TAR-010, TAR-017)

## Objective
Bootstrap the Streamlit product surface and deliver the first usable screen: a priority inbox of scored news groups with topic and date filtering, transparent rule explanations, and evidence-safe editorial guidance.

## Problem and rationale
The data, grouping, and versioned scoring pipelines are available, but editors have no product surface. `documentacion/interfaz-brief.md` defines the inbox as the first screen and requires score ordering while keeping evidence sufficiency independent from priority. This bounded screen creates the UI foundation while preserving the data/engine ownership boundary.

## Scope
- Add Streamlit as a pinned project dependency.
- Create a testable read-only query layer for `data/motor.duckdb` and `data/senales.duckdb`.
- Render the Bandeja screen with topic and date filters.
- Order groups by the versioned attention score, then urgency and group ID.
- Show score, rule version, rule reasons, evidence state, distinct-source corroboration, and repetition without conflating those concepts.
- Update the repository task ledger for TAR-010 and TAR-017.

## Non-goals
- Evidence detail, official context, cited Q&A, drafting, or review-state workflows (TAR-018 through TAR-021).
- Attention-score implementation (TAR-008).
- Changes under `motor/`, `ingesta/`, or committed `data/` snapshot files.
- Snapshot regeneration.

## Constraints
- Open both DuckDB databases in read-only mode.
- Exclude the `otros` class from the inbox.
- Use embeddings classification and the `puntaje` contract from TAR-008: `puntaje DESC`, `U DESC`, `grupo_id ASC`.
- Treat score priority and evidence sufficiency as independent; `alto + insuficiente` means requires investigation and is never presented as publishable.
- Treat source text as data, not instructions; rely on Streamlit escaping.
- Keep `fecha_deteccion` distinct from publication dates.
- Technical artifacts remain in English unless extending an existing Spanish repository artifact.
- The local shell lacks GNU Make; use `.venv/Scripts/python` commands directly.
- Git and repository artifacts are the shared source of truth between Guille and Víctor; Engram is only an auxiliary mirror.
- Record implementation decisions and evidence here, task state in `bitacora/tareas.yaml`, and integration contracts in `documentacion/` when another owner needs them.
- Do not modify Guille-owned tasks or `motor/`, `ingesta/`, and committed snapshot artifacts without first recording and communicating the dependency in the repository.
- After every task-state change, run `python notion_sync.py --dry-run` and the full pytest suite before a Conventional Commit and branch push.

## Delivery and routing
- Tracker branch: `feat/streamlit-bandeja`, targeting the verified default branch `main`.
- Delivery strategy: `feature-branch-chain`, selected after the tracker reached approximately 359 changed lines.
- SIB-02 child branch: `feat/streamlit-bandeja-ui`, targeting `feat/streamlit-bandeja` with a review budget of at most 400 additions plus deletions.
- Chain order: draft/no-merge tracker (`feat/streamlit-bandeja` → `main`) ← SIB-02 child (`feat/streamlit-bandeja-ui` → `feat/streamlit-bandeja`).
- SIB-01 route: delegated to `gentle-ai-worker` because the behavior spans dependency, application, and test files (multi-file writer trigger).
- SIB-02 route: delegated to `gentle-ai-worker` for the same trigger.
- Verification commands go through the delegated writer first; independent verification follows the native assessment plan.

## Tasks
- [x] **SIB-01 — Bootstrap a tested read-only inbox query.** Status: done. TAR-010 and TAR-017 are in progress; Streamlit, the app/query boundary, and focused tests are implemented. Work-unit commit: `c61c28d` (pushed). Native review target `sha256:7417d65e460bae1752b558e90e8e1f7697b6095f0e1e18837dcdb86581ba3bf1` approved and acknowledged in lineage `review-aebb29f613a083d2`.
- [ ] **SIB-02 — Deliver the Bandeja screen.** Status: in progress on child branch `feat/streamlit-bandeja-ui`. Render topic/date controls and score-prioritized group cards; show `version_reglas`, `motivos`, priority, and evidence state; explicitly mark `alto + insuficiente` as requiring investigation and never publishable; invalidate cached inbox data when the DuckDB files change; document startup on Windows without GNU Make; run focused and full checks; mark TAR-017 done while TAR-010 remains in progress; and commit the work unit. Commit evidence: pending.

## Acceptance criteria
- The app starts with `streamlit run app/app.py` from the activated Windows virtual environment.
- The inbox reads current groups without mutating either DuckDB file.
- Results use embeddings, exclude `otros`, and can be filtered by topic and inclusive date range.
- Ranking follows TAR-008 exactly: `puntaje` descending, then `U` descending, then `grupo_id` ascending.
- Each result shows `version_reglas` and `motivos`, and distinguishes article count, distinct-source corroboration, score priority, evidence state, and repetition.
- A high-priority result with insufficient evidence is labeled as requiring investigation and never as publishable.
- Empty and unavailable-data states are explicit and do not fabricate results.
- Focused tests, full pytest, and `notion_sync.py --dry-run` pass before each task-closing commit.

## Progress and evidence
- 2026-10-07: Repository, interface brief, task ledger, and current data/motor state reviewed. Manifest hash confirmed as `dd87ee41678220046d145506ebf51d7966470540c432388a58015d95416900f6`.
- 2026-10-07: Local setup completed with direct Python commands because GNU Make is unavailable. Generated report timestamp drift was diagnosed as non-semantic and restored with user approval.
- 2026-10-07: TAR-010 and TAR-017 moved to `En curso`. Verification: `notion_sync.py --dry-run` reported no errors; full suite passed (`72 passed`); `git diff --check` passed. The configured verification subagent was unavailable, so these bounded checks ran in the parent session.
- 2026-10-07: SIB-01 implementation added `streamlit==1.54.0`, a read-only DuckDB query boundary, a minimal Spanish Streamlit shell, and temporary-database tests. Observed TDD: RED (`ModuleNotFoundError: app`), then GREEN (`3 passed`); writer full suite `75 passed`; Notion dry-run and `git diff --check` passed.
- 2026-10-07: Parent spot check passed (`3 passed`), Streamlit started headlessly on port 8517, both DuckDB SHA-256 values stayed unchanged, and LSP diagnostics were clean for all three Python files.
- 2026-10-07: Native reliability review lineage `review-e4cdfa14b87ef2b9` is blocked before verdict because the reviewer transport reported quota exhaustion (retry horizon approximately 72 hours). Native assessment therefore requires an independent verifier, but the configured `gentle-ai-verify` agent failed twice without executing tools. No review verdict or independent-verifier evidence exists; SIB-01 remains open.
- 2026-10-07: Shared incomplete checkpoint `c61c28d` pushed to `origin/feat/streamlit-bandeja`; this preserves code and evidence for teammate continuation without claiming SIB-01 complete.
- 2026-10-07: Local model profiles changed `review-reliability` and `gentle-ai-verify` to OpenAI-backed roles. Frozen lineage `review-aebb29f613a083d2` resumed, approved target `sha256:7417d65e460bae1752b558e90e8e1f7697b6095f0e1e18837dcdb86581ba3bf1`, and its exact acknowledgement burned the authority. Native assessment now reports `candidate.consumed: true`, medium risk, and no separate verifier required.
- 2026-10-07: The approved reliability review reported one informational follow-up (`R3-stale-inbox-cache`, `app/app.py:16-20`): cached inbox results can outlive updated DuckDB files. This does not reopen SIB-01; SIB-02 will bind cache invalidation to database changes.
- 2026-10-07: Guille completed TAR-008 on `main` with score rules v0.3. Tracker commit `623a857` integrated that contract without rewriting the published tracker history. SIB-02 now consumes the `puntaje` table and supersedes the temporary recency/corroboration ranking.
- 2026-10-07: SIB-02 native review lineage `review-82ae33f0d0c0dad1` is blocked before verdict because the reviewer transport reported quota exhaustion ("The usage limit has been reached"). The work-unit commit is pushed but awaits independent verification or terminal review when capacity returns.

## Next step
Adapt the current SIB-02 UI candidate to TAR-008's score and evidence contract on `feat/streamlit-bandeja-ui`, keeping the child diff within 400 additions plus deletions and preserving the ownership boundary around `motor/`, `ingesta/`, and `data/`.
