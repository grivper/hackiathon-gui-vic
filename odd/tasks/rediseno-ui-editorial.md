# Editorial UI redesign (documentacion/REDISENO_UI.md)

## Goal
Apply the visual redesign to the Streamlit inbox. Visual only: no change to scoring, data, rules (v0.3), filters, order or texts.

## Decisions
- The app has no separate "ficha" view (evidence, chat and draft live in expanders inside each card). The doc's ficha page is NOT built: it would change navigation/structure. Card keeps the expanders.
- Pure HTML/CSS builders live in `app/estilos.py` (testable, all dynamic text escaped). `app/app.py` only calls them.
- Score and R/I/U/N/E components are on a 0-100 scale (reglas_puntaje.yaml), bars use that scale.

## Tasks
- [x] T1 `app/estilos.py`: CSS, hero, card, component bars + tests (escaping, clamping)
- [x] T2 Wire into `app/app.py` (hero KPIs, filters, ranked cards); existing tests keep passing
- [x] T3 Verify: pytest, notion dry-run, app boots

## Evidence
- pytest: 332 passed. `notion_sync.py --dry-run`: no errors.
- AppTest (app dir on sys.path, as `streamlit run`): no exceptions, 50 cards rendered, hero KPIs wired to the filtered groups.
- Not checked: real browser visual pass. Fonts load from Google Fonts (offline demo falls back to Georgia/sans-serif).

## Annex v2 (documentacion/REDISENO_UI_FICHA_ANEXO.md)
Style-only pass inside the expanders: `.info` replaces blue `st.info` (verification guidance, official context), `.empty` replaces the "Borrador no generado" info, evidence cards with `.evid` + `.kv` grid (source button kept between them), light expander/chat CSS, `.streamlit/config.toml` forces the light theme. No tabs, no new navigation, expander names and logic untouched.
- Existing tests that asserted `st.info` for these two spots now assert the HTML via `st.markdown` (implementation detail, same text).
- pytest: 338 passed; dry-run OK; AppTest: no exceptions, 51 evidence cards, 50 empty-draft states.
- Not checked: real browser (chat input / sub-expander contrast, theme) .

## Correction: the design has two pages (Bandeja-html.zip / Ficha-html.zip)
The exported mockups show the structure the user actually wants: a compact inbox row with an "Abrir ficha" button, and a separate full ficha page. Annex v2's "no ficha page" statement is superseded.
- Bandeja: ranked rows (rank, tema, fecha, titular, chips, "Atención" score + bar) and a native button per row.
- Ficha: dark header with "Volver a la bandeja", alert, Resumen, Evidencia y procedencias, Contexto oficial, Consulta (two expanders), and the aside (score 72px, Prioridad/Evidencia tiles, R/I/U/N/E, Reglas).
- Navigation uses `st.session_state["ficha_id"]`; filter keys are re-asserted each run so "Volver" restores them.
- Bug found and fixed: R/I/U/N/E are stored 0-1, not 0-100. The previous pass rendered every bar at ~1% width.
- Topic ids get a human label (`servicios_publicos` -> "Servicios públicos").
- pytest: 344 passed (incl. new AppTest navigation tests). Dry-run OK. Verified in Chrome at 1440px: both pages match the mockups.

## Pass 3: match Bandeja_referencia.html / Ficha_referencia.html (user chose the two-page structure)
Full-bleed dark header (100vw), cream filter bar, title + note on one row, each inbox row is one white card with the button inside it, evidence card is one boxed unit (title, id, source button, grid), alert/info/empty icons as inline SVG. Content stays capped at 1280px centred, as in the mockups.

## Pass 4: edge strip and back button (user screenshot)
- Cause of the strip: the page scrollbar gutter (about 10px) stayed paper-coloured next to the full-bleed dark header; below ~1360px the header padding also went negative, clipping the text and adding a horizontal scrollbar.
- Fix: hide the scroll gutter (wheel/touch/keys still scroll), `max()` padding, container padding 40px so header text and content align, no horizontal overflow.
- "Volver a la bandeja" is now a solid cream pill at the top-left of the header, plus a second one at the end of the ficha. Verified in Chrome at 1100px and 1440px; clicking it returns to the inbox.

## Pass 5: chat order (user screenshot)
`st.chat_input` was called between the history loop and the new-message render, so Streamlit drew the first messages above the input and every new Q&A below it. Messages now go into a container created before the input. Regression test added (container is created before the input). Verified in Chrome with two consecutive questions: all four messages above the input.

## Pass 6: "Abrir fuente original" blank after click (user screenshot)
After the click the link button showed an empty dark pill: its text took a dark colour in a state the CSS did not cover (visited/focus/active). Button colours are now pinned in every state (`:link`, `:visited`, `:focus`, `:active`, `:hover`) with `!important` on the text. Not reproducible in the automation Chrome (it renders correctly there), so verified by computed colours after a real click plus a CSS regression test; `:visited` itself cannot be forced.

## Pass 7: chat with fixed height + example questions
The chat history now lives in a fixed-height scrollable box (`CHAT_HISTORY_HEIGHT`, 380px) so the expander never grows. While the history is empty the box shows example questions built from the ficha's own cited claims (`suggest_questions` in app/data.py), as buttons that send the question. Each example is answerable by construction (it shares a term with a cited claim). Without a ficha it says there is no draft yet instead of inventing examples. Verified in Chrome with 12 messages: box stays 378px, scrolled to the newest message, input stays put.

## Pass 8: "Resumen del reporte" breakdown (documentacion/RESUMEN_REPORTE.md)
The summary paragraph is now five rows (badge, criterion chips/label, value + thin 0-1 bar), parsed from the same motor text (`resumen_reporte_html` in app/estilos.py; falls back to the plain text if the format changes). The side panel no longer repeats R/I/U/N/E: it keeps score, Prioridad/Evidencia tiles and "Reglas vX.Y". The spec's last note ("the side panel already shows bars") contradicts its IMPORTANT section; followed IMPORTANT. Presentation only: the text and values are unchanged.

## Pass 9: larger text
All CSS font sizes between 11 and 16px went up by 2px (metadata, chips, labels, notes, body) and native Streamlit text got explicit sizes (paragraphs 17px, captions 15px, labels 15px, inputs and buttons 17px, expander titles 18px). Headlines and big numbers unchanged. Verified in Chrome on both pages.

## Pass 10: rank numbers
Ranks 1-9 are zero-padded (01..09) and the rank cell no longer wraps: two-digit numbers (10, 11, ...) sit side by side on one line (nowrap, min-width 64px, tabular figures).

## Pass 11: ficha did not open for some inbox rows (user screenshot)
Bug in this feature: the ficha page looked its group up in the UNFILTERED inbox, which is capped at 50 rows (`fetch_inbox_groups(limit=50)`). A row visible under a filter (e.g. Tema = economía, rank 05) but outside the global top 50 was not found and the app bounced back to the inbox. The lookup now uses the same filters as the inbox (kept in session state). Regression test picks a real group that only appears under a filter. Verified in Chrome with Tema = economía, opening "Cooperación en seguridad y economía…".
Known limit (by design, not changed): every query returns at most 50 groups; the motor holds 25,136 scored groups.

## Pass 12: readable topic filter
The Tema dropdown listed raw ids (`economia`, `servicios_publicos`). It now shows the same human labels as the cards ("Economía", "Servicios públicos") through `format_func`; the value used by the queries is still the raw id. Test added (labels readable, selecting by id still works).

## Pass 13: "Generar borrador con IA" button (one group at a time)
User decision: generate per entry on demand instead of batch, with three guards (Ollama check, only that ficha written, never overwrite a human review).
- `motor/generar.py: guardar_ficha`: upserts one row and merges the jsonl by `id_caso` (other lines kept even if the local table lacks them).
- `app/generacion.py`: `estado_ollama` (server + model) and `generar_borrador` (refuses reviewed states without calling the model; a `llm_error` is not persisted so it can be retried; a legitimate abstention is saved).
- UI: `render_generate_draft` in the empty state; disabled with the reason when Ollama is down; spinner while generating; warning/error messages for the two refusal paths.
- Tests: tests/test_generacion.py (10) and 6 UI tests. Verified in Chrome: generated one real draft (Festival Navideño), jsonl went from 7 to 8 lines with no deletions; the verification change to data/fichas.jsonl was reverted, not committed.
- A ficha that already exists gets no button (regenerating is deterministic at temperature 0, so it would only reproduce the same text); the reviewed-state guard is enforced in the function as well.
