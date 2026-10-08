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
- [x] T1 (partial) Evaluation harness added; tuned temas.yaml REVERTED, see evidence. Original T1 text: Apply tuned `motor/temas.yaml`; test for the evaluation harness (tune/val split) so the gain is reproducible
- [ ] T2 Rebuild motor (clasificar/agrupar/puntuar) and regenerate `data/evaluacion_clasificacion.md`
- [ ] T3 Reconcile `G-9dd46610ff94`: decide and apply (regenerate ficha on Victor's machine, or swap the demo case), re-run benchmark
- [ ] T4 Update bitacora/docs, full suite, Notion dry-run, commit(s), push

## Evidence / outcome: tuning REJECTED on second evidence set

The tuned `motor/temas.yaml` was applied, measured, and then reverted. `motor/evaluar.py` keeps the
reproducible tune/validation split (7 new tests, suite 327 passed).

A pre-existing guard test, `tests/test_clasificar.py::test_embeddings_reales_acuerdan_80pct_con_etiquetas_dev_mini`
(24 dev-written headlines, independent of the 93 blind labels, asserting >= 0.8), failed with the
tuned file. It exists precisely to catch regressions when touching temas.yaml/thresholds, and it did.

| variant | 93 labels (val / total) | dev-mini |
| --- | --- | --- |
| base (current) | 0.290 / 0.339 | **21/24 (88%)** |
| seeds only (v5) | 0.311 / 0.361 | 19/24 |
| + score 0.20 | 0.342 / 0.421 | 17/24 |
| + turismo narrowed | 0.346 / 0.431 | 17/24 |
| + margin 0.03 (candidate) | 0.367 / 0.490 | 18/24 (guard FAILS) |
| score 0.20 only, no seeds | - | 20/24 |
| margin 0.03 only, no seeds | - | 20/24 |
| health-in-servicios_publicos only | 0.289 / 0.337 | 19/24 |

Every variant degrades dev-mini; none reaches the 0.8 guard except the current file. The two clearest
losses are unambiguous cases ("El Metro de Panama amplia su horario", "Apagones prolongados generan
quejas"), which the candidate sends to `otros`. Even the conceptually motivated change alone (human
labellers put state health under servicios_publicos) does not help either set: 0.339 -> 0.337 and 21 -> 19.

Conclusion: the macro-F1 gain on the 93 blind labels does not generalize to a second independent set,
so it is not a real improvement. The thresholds and seeds stay as they are. Per-class supports in the
93-label sample are tiny (turismo n=2, regulacion n=3), which makes macro-F1 unstable; a trustworthy
retune needs more labels, not more tuning. No downstream artifact changed: motor, scores, the five
demo fichas and the benchmark are untouched, and Ollama regeneration is no longer needed.
