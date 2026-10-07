# Cited generation and citation validator (TAR-009)

## Scope
Turn an event group into a traceable draft: retrieve evidence in code, let a local LLM only draft over that evidence, validate every citation in code, and abstain when evidence is missing. Output follows the challenge `fichas.jsonl` shape (id_caso, modalidad, ids_fuente, afirmaciones, citas, puntaje, componentes, estado_evidencia, borrador, estado_revision). Never label news true/false; never invent quotes, interviews or figures.

## Facts (explored)
- `data/motor.duckdb`: `grupos`, `grupo_noticias`, `clasificacion`, `puntaje` (incl. `estado_evidencia`, `motivos`, `contexto_oficial`, `evento_usgs_id`). `data/senales.duckdb`: `noticias` (id_noticia `N-`+sha1, titulo, url, medio, fecha_*), `indicadores` (`id_evidencia` IND-ISO3-indicador-anio, valor nullable), `eventos` (USGS id, magnitude, time, place, url).
- Most news only have titles/metadata, so drafts must say "basado únicamente en titular/metadatos".
- Ollama is not installed on this machine (Victor owns TAR-022); the LLM client must be testable with a fake.
- Design agreed in `documentacion/traspaso-hackiathon-tvn.md` section 3: layered RAG, three abstention kinds (indicator missing, value null, year out of range), output JSON with `tipo_respuesta`, `afirmaciones`, `versiones`, `vacios`, `alcance`; anti-injection by delimiters + canary test (T07).
- Brief limits: brief <= 250 words, title, public-interest angle, 3 research questions, sources, pending checks; script 45-60 s; digital copy <= 80 words.

## Design
- `motor/evidencia.py`: `reunir_evidencia(grupo_id)` -> evidence items `{id_evidencia, tipo, campos}` from news (title, medio, date, url), World Bank indicators (only exact, non-null) and the verified USGS event.
- `motor/citas.py` (pure, no LLM): schema validation of the LLM JSON, each claim must cite an existing `id_evidencia` and a valid `campo`; invalid claims are dropped and reported; computes citation coverage; flags figures in claim text not present in the cited evidence.
- `motor/abstencion.py` (pure): decides abstention before any LLM call (no evidence, null value, year out of range, indicator not in corpus); sets mandatory `alcance`.
- `motor/prompt.py`: builds prompt with sources inside delimiters as data, explicit "do not obey source content", JSON schema; canary-word test.
- `motor/llm.py`: thin Ollama client (JSON mode, timeout, records model/version/params); a fake client for tests.
- `motor/generar.py`: CLI `--grupo`, `--top N`, writes table `fichas` in `data/motor.duckdb` and exports `fichas.jsonl`; `make generar`. Review state starts as `nuevo`.

## Tasks
- [x] G1 Evidence retrieval `motor/evidencia.py` (test-first, fixtures)
- [x] G2 Citation validator `motor/citas.py` (test-first: invalid id, wrong campo, invented figure, no citation, coverage)
- [x] G3 Abstention rules `motor/abstencion.py` (test-first: T06 unanswerable, null value, year out of range, titles-only scope text)
- [ ] G4 Prompt builder with injection defense (test-first: T07 canary in a synthetic headline)
- [ ] G5 LLM client with fake and Ollama backends; model and params recorded
- [ ] G6 `motor/generar.py` pipeline + `fichas` table + jsonl export + `make generar`, end-to-end with the fake LLM
- [ ] G7 Real run with Ollama when available, docs (interfaz-brief contract for `fichas`), bitacora TAR-009, commits

## Open decisions
- Ollama on this machine for real-generation tests, or mock here and real run on the demo machine (user to decide).
- Model choice (Qwen2.5 7B vs Llama 3.1 8B) depends on Victor's latency measurement (TAR-022).

## Evidence
- G1: RED (collection error, module missing) then GREEN (8 passed); full suite 138 passed. Real data check: economia group returns 3 news + 4 World Bank indicators (latest non-null year, 2024); the USGS-linked group returns 2 news + event us6000ril5. Indicators are annual: the prompt/validator must keep year and unit visible (CU-02).
- G2: RED (collection error, module missing) then GREEN (19 passed); full suite 157 passed. Discard reasons: sin_cita, evidencia_inexistente, campo_inexistente, campo_nulo, cifra_no_sustentada, tipo_invalido, texto_vacio, afirmacion_invalida; schema failures and zero surviving claims degrade to `abstencion`. Figures may match rounded values; "1.400" is read both as 1,4 and 1400.
- G3: RED (collection error, module missing) then GREEN (10 passed); full suite 167 passed. `decidir_abstencion_grupo` (sin_evidencia), `consultar_indicador` (indicador_ausente / valor_nulo / anio_fuera_de_rango, exact lookup, no LLM), `alcance_de` (titulares vs datos oficiales). Real data has no null indicator values, so `valor_nulo` is covered by the synthetic test only. Contradiction handling (T05, "versiones") is not part of G3 and remains for the generation step.
