# Attention score and evidence state (TAR-008)

## Scope
Score every event group with the challenge formula `P = 30R + 25I + 20U + 15N + 10E` (components normalized 0-1, documented criteria, versioned rules file) and compute an evidence state independent of the score (`insuficiente` / `parcial` / `suficiente`). Deterministic code only: no LLM, no true/false labeling of news.

## Facts (explored)
- Inputs in `data/motor.duckdb`: `grupos` (grupo_id, n_noticias, n_procedencias, fecha_min/max, titulo_representativo, corroboracion, es_repeticion), `grupo_noticias` (procedencia), `clasificacion` (tema per news, metodo embeddings|tfidf). Official context in `data/senales.duckdb`: `indicadores` (Banco Mundial), `eventos` (USGS).
- 25069 groups, 25050 have a single provenance (almost all TVN), so most evidence states will honestly be `insuficiente`.
- Publication dates are NULL for most sitemap news; groups use detection date. Score must use a fixed reference date (not "now") for reproducibility.
- Challenge: ranges bajo [0,40) / medio [40,70) / alto [70,100]; ties: higher U, then id; show rules version.

## Design
- `motor/reglas_puntaje.yaml` (version `v0.1`): weights, U age brackets, R/I/N/E criteria, keyword lists, national-domain list, primary-source list, range thresholds. Changing weights = new version string.
- `motor/puntuar.py`: pure functions per component + CLI (`--forzar`, `--fecha-ref`, `--db`, `--out`), idempotent with an input hash like `agrupar.py`. Writes `puntaje` (grupo_id, tema, R, I, U, N, E, puntaje, prioridad, estado_evidencia, version_reglas, motivos) and `meta_puntaje` into `data/motor.duckdb`.
- Criteria: R 1.0 national outlet + one of the 6 themes, 0.5 theme but non-national outlet, 0 for `otros`; I by scope keywords (nacional / sectorial / local); U by age of `fecha_max` vs reference date (<24h 1.0, 1-3d 0.7, 3-7d 0.4, >7d 0.1); N 1.0 for a new event, low for repetition, duplicates never add; E by independent provenances + primary source + linked official data (Banco Mundial / USGS), capped at 1.
- Evidence state: `suficiente` needs corroboracion >= 2 and a primary or official link; `parcial` needs either; else `insuficiente`.
- Group theme = majority theme of its news (embeddings method).

## Tasks
- [x] T1 `motor/reglas_puntaje.yaml` + loader and validation (weights sum 100, ranges without overlap)
- [x] T2 Component functions R, I, U, N, E + total, priority, tie-break, evidence state (test-first, fixtures)
- [x] T3 `motor/puntuar.py` pipeline and CLI, DuckDB tables `puntaje` and `meta_puntaje`, `make puntuar` in `make motor`
- [x] T4 Real run, docs (interfaz-brief, README), bitacora TAR-008, commits

## Evidence
- Commit 6316121 on feat/puntaje-atencion (code + 33 tests; full suite 105 passed). Real run 35 s: 25069 groups, 612 alto / 5035 medio / 19422 bajo; evidence 6 suficiente / 1816 parcial / 23247 insuficiente.
- Open point: official-data link for E is thematic (any economia/servicios_publicos group gets it), which lifts single-source TVN groups to `parcial`. Pending user decision.
