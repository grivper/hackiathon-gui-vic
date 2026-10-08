# Acceptance tests T03-T06 and T08 (TAR-011, part 1)

## Scope
Run the acceptance tests of the challenge that the engine can already answer: T03 recirculated old news, T04 annual World Bank figure, T05 incompatible claims, T06 query without answer, T08 high-priority case. Each becomes a deterministic pytest test over the real pipeline (fake LLM, small fixtures) and, when it exposes a defect, a minimal fix. T09 (brief) and T10 (offline demo) depend on the UI and the benchmark of 40 queries is a separate decision; both are out of scope here.

## Facts (explored)
- Pipeline: `evidencia.reunir_evidencia` -> `abstencion` -> `prompt` -> `llm` (fake in tests) -> `citas.validar_citas` -> `generar.generar_ficha`. Fixtures and the `dbs` fixture pattern live in `tests/test_generar.py`.
- `puntuar` already exposes components and rule text in `motivos`; N (novelty) drops for `es_repeticion`.
- Evidence news items carry `fecha_publicacion` and `fecha_deteccion`; the draft text (`generar._borrador`) does not show dates.
- Ollama is not running on this machine now: real-model runs are out of scope for this part.
- T01, T02, T07 already passed in `bitacora/pruebas.yaml`.

## Tasks
- [x] P1 T06 query without answer: abstention, no invented figure or citation (test-first; may already be GREEN)
- [x] P2 T04 annual World Bank figure keeps country, year and unit, not described as today's figure
- [x] P3 T08 high-priority case exposes components and rule; priority never publishes (estado_revision stays `nuevo`)
- [x] P4 T05 incompatible claims: both versions, scope and pending review shown
- [x] P5 T03 old recirculated news: original date shown, not presented as new event
- [ ] P6 Record T03-T06, T08 in `bitacora/pruebas.yaml`, update TAR-011 notes, full suite, commit(s)

## Evidence
- P1 T06: GREEN on first run (characterization, no meaningful RED: abstention already existed). 3 tests in `tests/test_aceptacion.py`.
- P2 T04: RED on `test_T04_el_codigo_agrega_pais_anio_y_unidad_aunque_el_modelo_los_omita` (draft depended on the model writing year/unit; country only appeared inside the evidence id). Fix: `evidencia` now carries `pais_iso3`; `generar._borrador` appends country, year, unit and "dato anual" for indicator citations, by code. GREEN; full suite 258 passed.
- P3 T08: GREEN on first run (characterization): components, rules text and priority already exposed; no publication state exists (`app.data.VALID_REVIEW_STATES`); priority does not bypass abstention.
- P4 T05: RED (draft had both versions and scope but no pending-review line). Fix: `generar._borrador` adds "Revisión pendiente" for `contradiccion`, by code. GREEN; suite 263 passed.
- P5 T03: RED (draft showed no dates). Fix: `generar._contexto_noticia` writes original publication date, or "detectada ... fecha de publicación no disponible", and flags >30 days between publication and detection as "vuelve a circular, no es un evento nuevo". U already used the original date (agrupar coalesce), confirmed by test. GREEN; suite 266 passed.
