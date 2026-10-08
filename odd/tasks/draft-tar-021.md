# TAR-021 — Borrador y revisión

## Goal

Provide an interface for editors to generate, view, and review an editorial draft for a news group. The draft must include citations per affirmation. The review state must be tracked using five mandatory states, reinforcing that approving a draft does not mean publishing it.

## Scope

- Add a "Borrador editorial" section or expander to each group card in `app/app.py`.
- Define a `DraftResponse` dataclass in `app/data.py` mirroring the `fichas.jsonl` structure (`borrador`, `citas`, `afirmaciones`, `estado_revision`).
- Implement a mock `generate_group_draft(grupo_id)` function, pending Guille's TAR-009 integration.
- Maintain the draft and its current review state (`nuevo`, `en revisión`, `requiere evidencia`, `aprobado como borrador`, `descartado`) in `st.session_state`.
- Ensure tests verify the 5 valid states and safe state transitions.

## Tasks

- [x] **DR-01 — Add draft data contract**
  - Define `DraftResponse` and `generate_group_draft`.
  - Add focused tests verifying it returns a valid initial state (`nuevo`).
  - Evidence: focused suite `145 passed`; LSP clean.
- [x] **DR-02 — Render the draft and review UI**
  - Add a "Generar borrador" button.
  - Display the generated draft text with its mock citations.
  - Add a selectbox for the 5 editorial review states.
  - Show a warning that "aprobado como borrador" does not authorize publication.
  - Evidence: focused suite `145 passed`; LSP clean.

## Acceptance Criteria

- Editors can generate a draft for a group.
- The UI exposes the draft and a dropdown/radio to change its review state.
- The state must be exactly one of the 5 mandatory states.
- The UI clearly separates the draft approval from final publication.