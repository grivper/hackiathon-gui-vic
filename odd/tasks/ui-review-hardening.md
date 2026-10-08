# UI review hardening (stack 018-021)

## Goal
Fix the logic bug and contract mismatches found reviewing app/app.py and app/data.py on top of feat/draft-tar-021, before merging the stack.

## Facts
- `id_caso` in `fichas` equals `grupo_id`. Table `fichas` (id_caso, estado_revision, tipo_respuesta, ficha JSON, generado_en) may not exist yet (needs Ollama, TAR-022). Pipeline protects `estado_revision` on regeneration (motor/generar.py `estados_existentes`).
- Real citations are `{"id_evidencia", "campo"}`; evidence ids are `N-...`. Real `tipo_respuesta`: respuesta | abstencion | contradiccion, plus `motivo_abstencion`.
- Reproduced bug: regenerating a draft keeps "aprobado como borrador" because the selectbox keeps its own key.

## Tasks
- [x] T1 State bug: regenerating resets the review state (test-first, mock-based widget tests following existing `test_bandeja_app.py` style)
- [x] T2 Draft reads real `fichas` (read-only); no ficha -> honest "borrador no generado"; render abstention/contradiction; remove mock draft
- [x] T3 Citations traceable: show `id_noticia` in evidence detail; render citas as id_evidencia/campo
- [x] T4 Persist review state to `fichas.estado_revision` (short write connection), keep pipeline protection
- [x] T5 Chat mock clearly labeled as simulated; citations not fake-real
- [x] T6 Minor: distinguish evidence error vs no data, SQL aggregates for filter options, None date guard

## Evidence

Implemented on branch `fix/ui-review-hardening`. Changes are in the working tree,
**not committed** (commit/work-unit decisions are owned by the orchestrating
agent/human, not this implementation pass).

- T1+T2 (combined, since removing the mock `generate_group_draft`/button flow
  is what eliminates the regeneration bug): `app/data.py` gained `GroupFicha`,
  `fetch_group_ficha` (reads the real `fichas` table, returns `None` when the
  table or row is absent), `VALID_REVIEW_STATES`. `app/app.py`
  `render_group_draft` now fetches a fresh ficha every render (no caching)
  and renders respuesta/abstencion/contradiccion distinctly. The review
  selectbox key is scoped to `grupo_id` **and** `ficha.generado_en`, so a
  newly generated ficha for the same group never inherits a stale approval
  left in `st.session_state` from a previous generation.
  Tests: `tests/test_bandeja_data.py` (`test_fetch_group_ficha_*`,
  `test_persist_ficha_review_state_*`, 7 new) and `tests/test_bandeja_app.py`
  (`test_render_group_draft_*`, including
  `test_render_group_draft_scopes_the_selectbox_key_to_the_generation_timestamp_so_regenerating_does_not_inherit_approval`
  which directly reproduces and fixes the reported bug).
- T3: `render_group_evidence` now shows `ID de evidencia: {row.id_noticia}`
  per member; citas in the draft render as `id_evidencia · campo`.
- T4: `app/data.py` `persist_ficha_review_state(motor_path, grupo_id, new_state)`
  opens a short-lived read-write DuckDB connection, validates `new_state`
  against `VALID_REVIEW_STATES`, and is a no-op (never creates the table) if
  `fichas` does not exist. Wired into `render_group_draft`: only called when
  the selectbox value differs from the ficha's stored `estado_revision`.
  Fichas reads are never cached (no `@st.cache_data`).
- T5: chat expander renamed to "Consulta citada (simulada)" with a prominent
  `st.warning` ("Respuesta simulada: aún no usa el LLM ni la evidencia real
  (pendiente TAR-020/TAR-028)"); the "IA responderá basándose solo en la
  evidencia" claim was removed. Mock citations in `app/data.py`
  `ask_group_question` are now `"[simulado]"` instead of real-looking `E-N`
  ids, and the chat caption reads "Citas simuladas: ...". The draft's
  "basado exclusivamente en la evidencia" caption now only renders for a
  real, non-abstention ficha.
- T6: (a) `main()`'s per-group evidence loop now shows `st.warning("No se
  pudo cargar la evidencia de este grupo.")` on `duckdb.Error`, distinct from
  the silent `[]` previously used for both errors and empty results; (b)
  `fetch_inbox_filter_options` computes topics via `SELECT DISTINCT` and
  bounds via `MIN`/`MAX` in SQL instead of fetching every row, preserving the
  `ScoreUnavailableError` behavior (new tests added first against the old
  row-fetching implementation to confirm no regression, then kept green
  after the refactor); (c) `render_group_card` uses the existing
  `evidence_date_label` helper instead of an `f"{group_date:%d/%m/%Y}"`
  format spec, so a `None` `_group_date` renders "No disponible" instead of
  crashing.

Full suite: `.venv/bin/python -m pytest tests -q` → **160 passed** (was 145
before this work; 15 net new tests, no removed coverage — the former
`generate_group_draft`/`DraftResponse` mock tests were replaced 1:1 by real
ficha-reader tests).

## Closing evidence (orchestrator)
- Commit 11c3b61: all six tasks, full suite 160 passed.
- Extra fix found while verifying against motor/generar.py on main: real `afirmaciones` are dicts (texto, id_evidencia, campo); the reader now normalizes them to text (RED then GREEN).
- Verified against main: citation id_evidencia equals id_noticia for noticia items; ficha shape matches generar.py.
- Not verified end to end: no real ficha exists yet (needs make generar with Ollama or the fake backend); do this in TAR-028.
