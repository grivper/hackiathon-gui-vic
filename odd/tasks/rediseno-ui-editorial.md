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
