# Demo-ready real generation and UI integration (TAR-022, TAR-024, TAR-028)

## Goal

Replace the remaining mocked editorial flow with five pre-generated, citation-validated cases that the Streamlit UI reads from `data/motor.duckdb`, while preserving explicit abstention and human-review safeguards.

## Scope

- Verify or install Ollama on the demo machine and record a reproducible local latency measurement.
- Generate five final `fichas`, including at least one insufficient-evidence case, with the selected local model and code-side citation validation.
- Connect the existing evidence, query, and draft UI surfaces to the real `fichas`/`puntaje` contract.
- Update the task ledger, user-facing run instructions, and focused tests with each work unit.

## Non-goals

- Regenerating the committed data snapshot with `make datos`.
- Changing classification themes or scoring rules.
- Adding the optional package-upload screen (TAR-030).
- Claiming that draft approval authorizes publication.

## Constraints

- The repository snapshot remains the source of truth; `data/raw/` and DuckDB files stay uncommitted.
- `data/reporte_calidad.md` is currently regenerated locally from the pulled manifest and must not be included in a work-unit commit until snapshot ownership is resolved.
- LLM output is untrusted: citations and unsupported figures/entities remain validated in code.
- Final generation may be performed offline ahead of the demo because measured CPU latency exceeds the 15-second target.
- Every behavioral change uses focused test-first development and independent verification.

## Tasks

- [x] **DRI-01 — Establish the reproducible Ollama demo runtime (TAR-022).** Ollama 0.40.1 and `gemma3:4b` were installed and measured on Víctor's demo machine. Evidence remains preserved on `feat/demo-real-integration`; Guille must reconcile its n=3 result with the newer n=5 benchmark now on `main` before choosing the official TAR-022 status.
- [x] **DRI-02R — Reconcile five final citation-validated fichas onto latest main (TAR-024).** Materialized the already validated five-record `data/fichas.jsonl` artifact without replaying stale shared-file changes or rerunning Ollama/DuckDB; revalidated it and updated only current ledger/docs. Work-unit commit: `c4d3a49`.
- [ ] **DRI-03A — Read real fichas and answer from validated claims (TAR-028).** Reapply DuckDB-primary/JSONL-fallback retrieval, provenance-gated review persistence, and deterministic extractive chat on top of latest `main`, retaining the observed RED/GREEN contract and keeping the slice under 400 changed lines.
- [ ] **DRI-03B — Wire Streamlit review UX and cache safety (TAR-028).** Render real query/draft states, prevent JSONL fallback review persistence, invalidate on JSONL changes, enforce not-publishable copy for all insufficient evidence, update ledger/docs, and keep the UI slice under 400 changed lines.

## Acceptance criteria

- The demo machine has a documented, reproducible Ollama/model setup and measured latency evidence.
- Exactly five final cases are available to the demo flow, with at least one insufficient-evidence case.
- Every displayed claim/citation comes from the validated persisted contract; no UI fallback invents evidence.
- Streamlit reads real `fichas` and `puntaje` data and preserves the publication safety warning.
- Focused tests, full pytest, Notion dry-run, and an applicable Streamlit smoke check pass before closure.

## Progress and evidence

- 2026-10-08: Original work was preserved on `feat/demo-real-integration`. After overlapping upstream changes caused a second rebase conflict, the user chose to abort and reevaluate; clean integration continues from `origin/main` on `feat/demo-real-main-integration`.
- Startup rebuilt local DuckDB files from manifest `1e411af64147093fa76d3fc2c1ff178a5c70794c711bb912e1f3d0b38e2a9830` and completed classification, grouping, and scoring.
- DRI-01 evidence: Windows PowerShell setup and the exploratory n=3 probe remain preserved on `feat/demo-real-integration`. TAR-022 stays En curso until the official n=10 measurement requested by Guille is recorded; the 15-second target was already missed in exploratory runs.
- DRI-02R validation: materialized `data/fichas.jsonl` exactly from `feat/demo-real-integration`, without rerunning Ollama or mutating DuckDB. Structural validation confirmed exactly five unique records (`G-c7e0cc7bcfce`, `G-99f6cccc1c81`, `G-58502841e2c7`, `G-49282420d812`, and `G-9dd46610ff94`), valid `nuevo` review states, and 100% citation coverage for all non-abstentions. `G-9dd46610ff94` retains `estado_evidencia=insuficiente`. Focused citation/generation/acceptance tests: 56 passed in 6.08 s. Work-unit commit: `c4d3a49`.
