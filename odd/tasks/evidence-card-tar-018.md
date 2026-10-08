# TAR-018 — Evidence detail card

## Goal

Add a read-only evidence detail to each priority-inbox group so an editor can inspect source provenance, corroboration, repetition, publication date, detection date, and unresolved verification needs without exposing article text or changing motor outputs.

## Scope

- Add a typed evidence query over `motor.grupo_noticias` joined to `senales.noticias`.
- Render evidence metadata inside the Streamlit group card.
- Distinguish publication date from detection date and handle missing publication dates explicitly.
- Preserve the existing definition of corroboration as distinct provenance, not article count.
- Keep `motor/`, `ingesta/`, committed snapshots, and DuckDB outputs unchanged.

## Tasks

- [x] **EC-01 — Add the read-only evidence data contract**
  - Test evidence rows, deterministic ordering, nullable publication dates, and read-only behavior.
  - Implement the typed repository query.
  - Evidence: RED observed by the writer; focused suite `6 passed`; independent verifier found no issues; LSP diagnostics clean; commit `72bd364`.
- [x] **EC-02 — Render the evidence detail safely**
  - Test pure presentation rules for dates and verification guidance.
  - Add the Streamlit evidence expander and wire it to each group.
  - Run focused and full verification, update TAR-018, and record the work-unit commit.
  - Evidence: RED observed by the writer; focused suite `10 passed`; full suite `140 passed`; independent AppTest rendered 50 groups and 50 evidence expanders with no exceptions; LSP diagnostics clean; commit `382cb56`.

## Acceptance criteria

- Each group exposes its member headlines and source links when available.
- The UI identifies provenance used for corroboration and does not conflate it with article count.
- Publication/original date and detection date are labeled separately.
- Missing publication dates are shown as unavailable, never replaced silently by detection date.
- Insufficient evidence continues to require investigation and is never presented as publishable.
- All database access remains read-only.

## Review workload

Expected low-to-medium review load across `app/data.py`, `app/app.py`, and focused tests. Keep the two behavior units as separate Conventional Commits; open one PR unless the final diff exceeds the repository review budget.
