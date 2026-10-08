# Chat supports a "contradiccion" response type (benchmark improvement, TAR-011 follow-up)

## Scope
Make `app.data.ask_group_question` answer a contradictory ficha by exposing every cited version and a pending-review notice, never choosing a winner (acceptance test T05 behavior at chat level). Measure the 6 `contradiccion` benchmark records again.

## Non-goals
- The 7 `respuesta` records that currently abstain (separate problem: term matching/recall).
- Changing the 5 real fichas or `data/fichas.jsonl`. Real UI never loads synthetic data.
- Regenerating fichas with Ollama.

## Facts (explored)
- The 6 contradiction benchmark records target groups `SYN-*-CONTRADICTION` with evidence `SYN-*-V1/V2`. Those ids exist ONLY in `data/benchmark.jsonl`: no ficha, no DuckDB row, no fixture. Today they "fail" because the group does not exist, not only because the chat lacks the type.
- Real pipeline already produces `tipo_respuesta == "contradiccion"` fichas (`motor/generar.py`, `app/app.py:267` shows a warning); none of the 5 committed real fichas is a contradiction.
- `ask_group_question` takes `fichas_path`; JSONL fallback is used when the group is not in DuckDB. `GroupFicha.tipo_respuesta` and per-claim citations are already normalized.
- Decision: add a clearly synthetic `data/fichas_sinteticas.jsonl` (6 contradiction fichas), loaded only by the benchmark runner for `synthetic` records. The app default path stays `data/fichas.jsonl`.
- Caveat to report: the new benchmark gain measures the mechanism on synthetic fixtures, not real-data quality.

## Tasks
- [x] C1 Chat: `ChatResponse.contradiccion`, answer lists all versions with citations + pending-review line; tests first
- [x] C2 UI: chat renders the contradiction warning (app/app.py)
- [x] C3 Synthetic fichas file for the 6 SYN-*-CONTRADICTION groups
- [x] C4 Runner: observed type 3-way, synthetic records read synthetic fichas, contradiccion scored; tests
- [x] C5 Re-run real benchmark, regenerate report, record, full suite, commit(s), push

## Evidence
- C1-C4: worker-built; RED by stashing each source file (4/1/7 failures), GREEN: 15 chat + 15 runner tests; full suite 320 passed.
- C5: real benchmark re-run: type match 67.5% -> 82.5%; contradiccion 0/6 -> 6/6, recall 100%; respuesta unchanged 70.8% (7 still abstain). Report states the synthetic scope caveat.
