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
- [x] G4 Prompt builder with injection defense (test-first: T07 canary in a synthetic headline)
- [x] G5 LLM client with fake and Ollama backends; model and params recorded
- [x] G6 `motor/generar.py` pipeline + `fichas` table + jsonl export + `make generar`, end-to-end with the fake LLM
- [ ] G7 Real run with Ollama when available, docs (interfaz-brief contract for `fichas`), bitacora TAR-009, commits

## Open decisions
- Resolved: Ollama 0.40.0 installed without root in `~/.local/ollama` (binary + `models/`; start with `OLLAMA_MODELS=~/.local/ollama/models ~/.local/ollama/bin/ollama serve`). Models: qwen2.5:3b-instruct-q4_K_M and qwen2.5:7b-instruct-q4_K_M.
- Model choice (Qwen2.5 7B vs Llama 3.1 8B) depends on Victor's latency measurement (TAR-022).

## Evidence
- G1: RED (collection error, module missing) then GREEN (8 passed); full suite 138 passed. Real data check: economia group returns 3 news + 4 World Bank indicators (latest non-null year, 2024); the USGS-linked group returns 2 news + event us6000ril5. Indicators are annual: the prompt/validator must keep year and unit visible (CU-02).
- G2: RED (collection error, module missing) then GREEN (19 passed); full suite 157 passed. Discard reasons: sin_cita, evidencia_inexistente, campo_inexistente, campo_nulo, cifra_no_sustentada, tipo_invalido, texto_vacio, afirmacion_invalida; schema failures and zero surviving claims degrade to `abstencion`. Figures may match rounded values; "1.400" is read both as 1,4 and 1400.
- G3: RED (collection error, module missing) then GREEN (10 passed); full suite 167 passed. `decidir_abstencion_grupo` (sin_evidencia), `consultar_indicador` (indicador_ausente / valor_nulo / anio_fuera_de_rango, exact lookup, no LLM), `alcance_de` (titulares vs datos oficiales). Real data has no null indicator values, so `valor_nulo` is covered by the synthetic test only. Contradiction handling (T05, "versiones") is not part of G3 and remains for the generation step.
- G4: RED (collection error, module missing) then GREEN (14 passed); full suite 181 passed. `construir_prompt` (system = rules + mandatory scope; user = sources as JSON between `<<<FUENTE ...>>>`/`<<<FIN_FUENTE>>>`; delimiters in source text neutralized; fields truncated to 400 chars; deterministic), `ESQUEMA_SALIDA` (JSON schema for Ollama), `obedecio_inyeccion` (canary check, T07). Limit: this proves the prompt is built defensively; whether a real 7-8B model resists the injection still needs the real run in G7.
- G5: RED (module missing) then GREEN (9 tests in tests/test_llm.py, HTTP stub instead of real Ollama); full suite 190 passed. `ClienteOllama` (stdlib HTTP, schema-constrained JSON, num_thread 4, num_ctx 4096, num_predict 512, temperature 0, seed 7, all overridable via LLM_* / OLLAMA_HOST env), `ClienteFalso`, `Respuesta` (records model, options, tokens, tok/s, duration; failures never raise), `motor/medir_llm.py` (median/p95 latency, valid JSON, valid-citation counts).
- Probe on this machine (i7-1165G7, 4 cores, CPU only), real economia group, 1395 prompt tokens: qwen2.5:3b 7.7 tok/s, 483 output tokens, 88 s total (7.6 s model load), answered `abstencion` with no claims (wrong: evidence was sufficient); qwen2.5:7b 3.6 tok/s, 307 tokens, ~140 s generation + 72 s first load, 2 claims both with valid citations but chose `contradiccion` although the headlines agree. Neither meets the 15 s median target on this CPU, and neither judged the group correctly on one sample (n=1, not a benchmark).
- Model comparison (this CPU, num_thread 4, num_ctx 4096, `medir_llm.py --n 4 --min-noticias 2`, groups of top score with >= 2 news; n=4 is exploratory, not a benchmark). Prompt rule 6 was first too abstention-prone (top groups have one headline; every model said "falta informacion"), so it was changed to "with at least one headline, state what it says attributed to the outlet; abstain only without any useful source" (test added).
  | model | median s | p95 s | tok/s | valid JSON | >=1 valid-cited claim |
  |---|---|---|---|---|---|
  | qwen2.5:1.5b q4_K_M | 18.3 | 33.2 | 15.3 | 4/4 | 2/4 |
  | qwen2.5:3b q4_K_M | 23.7 | 36.1 | 8.0 | 4/4 | 0/4 (abstains, fills `vacios` with field names) |
  | llama3.2:3b q4_K_M | 72.9 | 100.0 | 7.6 | 2/4 | 2/4 |
  | qwen2.5:7b q4_K_M | 113.4 | 158.9 | 3.7 | 4/4 | 2/4 |
  None meets the 15 s median on this CPU; none gives reliable citations with the current prompt. Next: improve the prompt/schema (G7) and consider pre-generating the final fichas offline.
- G6: RED (module missing) then GREEN (11 tests in tests/test_generar.py with `ClienteFalso`); full suite 202 passed. `generar_ficha` = evidencia -> abstencion -> prompt -> LLM -> canary check -> validator; the draft (`borrador`) is assembled by code only from surviving claims (`- texto [id · campo]`, plus vacios/versiones and the code-decided scope). Abstention reasons: sin_evidencia, llm_error, inyeccion, esquema_invalido, sin_sustento, modelo_abstuvo (state `requiere evidencia`). `fichas` table is upserted per `id_caso` (non-regenerated fichas survive) and `fichas.jsonl` is exported from the table; fichas already in `en revisión` / `aprobado como borrador` / `descartado` are never regenerated without `--forzar`. `make generar` (default `--top 5 --min-noticias 2`, override with `GRUPOS=`).
- G6 real run (qwen2.5:1.5b, 2 groups with >= 2 news, on a copy of motor.duckdb): pipeline completed, 38 s and 18 s per group, both ended in `modelo_abstuvo`, and the model filled `vacios` with field names instead of real gaps. The abstention path works as designed; draft quality is the G7 problem (prompt/schema tuning, 7B for the final fichas).
