# TAR-020 — Consulta citada

## Goal

Provide a Streamlit chat interface inside the priority-inbox group card. Editors can ask questions in Spanish about the group. The system provides a cited response or explains its abstention (CU-04).

## Scope

- Add a chat interface (`st.chat_message`, `st.chat_input`) in `app/app.py` for a selected group.
- Implement a mock backend function `ask_group_question` in `app/data.py` (or `app/chat.py`) that returns sample cited responses or abstentions, pending Guille's LLM generation integration (TAR-009).
- Update the UI to render the chat history for the active session and group.
- Verify through tests that the chat UI safely handles empty questions, maintains history, and handles mock citations.

## Tasks

- [x] **CH-01 — Add mock chat query contract**
  - Define `ChatResponse` dataclass.
  - Implement a mock `ask_group_question(grupo_id, question)` that returns predefined responses with fake citations or abstentions.
  - Evidence: tests run successfully; no syntax errors.
- [x] **CH-02 — Render the chat interface**
  - Add `st.chat_input` and `st.chat_message` inside a "Consulta" expander for the group card.
  - Maintain `st.session_state` chat history keyed by `grupo_id`.
  - Evidence: tests pass `143 passed`; LSP clean; native review blocked by `Codex error: The usage limit has been reached`. Commit `bfea715`.

## Acceptance Criteria

- The UI offers a chat input for the group.
- Chat history is preserved per group during the Streamlit session.
- The mock response clearly cites evidence or explicitly abstains ("No hay evidencia en este grupo para responder...").
- No real LLM calls are made yet (awaits Guille's TAR-009 output).