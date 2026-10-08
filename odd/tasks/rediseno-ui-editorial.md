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
