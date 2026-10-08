# Development benchmark runner and T09 editorial brief check (TAR-011, part 2)

## Scope
Close TAR-011: (1) run the 40 development queries of `data/benchmark.jsonl` through the real query path (`app.data.ask_group_question`) and report measured results; (2) check acceptance test T09 (editorial brief: useful format, pertinent citations, facts vs inferences distinguished) against the five validated fichas.

## Non-goals
- Fixing chat/engine weaknesses the benchmark exposes (report them; fixes are separate decisions).
- Regenerating fichas or running Ollama. Editing `data/benchmark.jsonl`.

## Facts (explored)
- `data/benchmark.jsonl`: 40 records (24 respuesta, 10 abstencion, 6 contradiccion); fields include `target_group_id`, `expected_response_type`, `required_evidence_ids`, `forbidden_claims`.
- `ask_group_question(grupo_id, question, motor_path, signals_path, fichas_path)` returns `ChatResponse(respuesta, abstencion, citas)`; it is deterministic and extractive; it never returns a contradiction type.
- Prototype run: 17 respuesta ok, 10 abstencion ok, 7 respuesta expected but abstained, 6 contradiccion expected but abstained. Only 18 of 40 targets have a ficha in `data/fichas.jsonl`.
- `forbidden_claims` are free text; they cannot be checked automatically and are reported as manual-review items.

## Tasks
- [x] B1 Runner `motor/evaluar_benchmark.py` + tests: per-record result and summary (response-type match, required-evidence recall, citations all belong to the group, abstention carries no citations); writes `documentacion/evidencia-benchmark.md`
- [x] B2 Run it against the real data and record the numbers honestly (no tuning of the benchmark to pass)
- [x] B3 T09: check the five fichas for format, citations, facts vs inferences; record verdict in `bitacora/pruebas.yaml`
- [ ] B4 Update TAR-011 notes/state, full suite, Notion dry-run, commit(s), push

## Evidence
- B1: worker-built `motor/evaluar_benchmark.py` + `tests/test_evaluar_benchmark.py`; RED (ImportError) then GREEN 10 passed; full suite 300 passed.
- B2: real run over 40 records: type match 67.5% (respuesta 70.8%, abstencion 100%, contradiccion 0%), mean evidence recall 27.1%, clean abstention 100%. Matches the earlier prototype (27/40). Report: `documentacion/evidencia-benchmark.md`.
- B3: T09 recorded as Pasó with observations in `bitacora/pruebas.yaml`.
