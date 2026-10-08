# TAR-019 — Contexto oficial

## Goal

Render an official context panel inside each priority-inbox group card. It displays World Bank indicators and USGS earthquake links matching the group's topic and timeframe. This provides editors with hard baseline facts without conflating historical data with breaking news.

## Scope

- Update the data contract (`app/data.py`): Add `contexto_oficial` and `evento_usgs_id` string fields to `InboxGroup`.
- Update the inbox query (`app/data.py:fetch_inbox_groups`): Select `p.contexto_oficial` and `p.evento_usgs_id`.
- Update the UI (`app/app.py`): Render an official context section or alert within `render_group_card`.
  - If `contexto_oficial` exists, display it clearly as "Contexto Oficial".
  - If `evento_usgs_id` exists, display a verified link to the USGS earthquake event.
- Update tests (`tests/test_bandeja_data.py`, `tests/test_bandeja_app.py`): Supply the new columns in mock DBs and verify they render correctly.

## Tasks

- [x] **CO-01 — Update data contract with context columns**
  - Add fields to `InboxGroup` and update `fetch_inbox_groups`.
  - Update tests to populate and verify these fields.
  - Evidence: focused suite `6 passed`; LSP diagnostics clean.
- [x] **CO-02 — Render the official context panel**
  - Extract and render the World Bank indicator text and the USGS event link in `render_group_card`.
  - Ensure missing context is handled gracefully (omitted or shown as unavailable).
  - Run focused tests and verify Streamlit UI.
  - Evidence: full suite `142 passed`; LSP diagnostics clean; native review blocked by `Codex error: The usage limit has been reached`. Commit `204d6bc`.

## Acceptance Criteria

- `InboxGroup` correctly exposes `contexto_oficial` and `evento_usgs_id`.
- The group card displays a distinct "Contexto oficial" section if data is present.
- A verified USGS earthquake event displays a clear UI indicator (e.g., a link or badge).
- The presentation explicitly separates historical annual context from current breaking news.
- The UI handles `NULL` or empty strings without crashing.
- No changes to `motor/`, `ingesta/`, or DuckDB generation logic.