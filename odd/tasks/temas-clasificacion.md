# Improve topic classification quality (TAR-015)

## Scope
Apply the validated topic/threshold tuning that raises embeddings macro-F1 from 0.339 to 0.490 on the 93 human labels, and reconcile every downstream artifact it changes (scores, demo fichas, benchmark).

## Non-goals
- Changing the LLM prompt (`motor/prompt.py`): reviewed and intentionally left as is; it was already iterated against the real model and a longer prompt previously broke JSON output.
- Re-labelling the sample or adding labels.
- Regenerating the committed data snapshot.

## Facts (explored)
- Method: 93 labels split by index parity into tune (47) and validation (46); only changes improving BOTH halves were kept.
- Base 0.339 (tune 0.398 / val 0.290) -> candidate 0.490 (tune 0.608 / val 0.367). Margin 0.04+ overfits (val collapses) and was rejected. Contrast groups rejected twice (val 0.170).
- Changes: servicios_publicos description now includes state health services (matches human labelling); turismo narrowed to tourism-as-business (it was absorbing sports/culture); generic seeds added per topic; umbral_score 0.25 -> 0.20; umbral_margen 0.01 -> 0.03. `otros` share 61% -> 47%.
- Downstream: 4 of the 5 demo fichas keep topic/score/priority. `G-9dd46610ff94` (scooters/ATTT) moves servicios_publicos/66/medio -> otros/36/bajo; its news item sits between servicios_publicos and regulacion with margin 0.012. 3 benchmark records target that group. Lower margins do not save it (the seeds alone move it).
- Ollama is NOT available on this machine: regenerating that ficha requires Victor's machine.

## Tasks
- [ ] T1 Apply tuned `motor/temas.yaml`; test for the evaluation harness (tune/val split) so the gain is reproducible
- [ ] T2 Rebuild motor (clasificar/agrupar/puntuar) and regenerate `data/evaluacion_clasificacion.md`
- [ ] T3 Reconcile `G-9dd46610ff94`: decide and apply (regenerate ficha on Victor's machine, or swap the demo case), re-run benchmark
- [ ] T4 Update bitacora/docs, full suite, Notion dry-run, commit(s), push
