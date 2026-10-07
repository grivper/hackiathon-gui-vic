# Thematic classification and event grouping (TAR-007)

## Scope
Classify the news into the 6 challenge themes (economia, logistica_canal, turismo, servicios_publicos, eventos_naturales, regulacion) plus `otros`, and group headlines about the same event. Embeddings (sentence-transformers, multilingual, CPU) are the main method; TF-IDF is the baseline. Evaluate with macro-F1 on a human-labeled blind sample.

## Facts (explored)
- 30154 news in DuckDB `noticias`, ~99.8% Spanish, `tema` empty except 151 GDELT rows (search topic, not a verified label).
- Missing deps: scikit-learn, sentence-transformers (+ torch). CPU only: 8 cores, 15 GB RAM, ~17 GB disk free.
- Challenge requirements: at least one real ML/NLP capability; macro-F1 or precision/recall on human labels with sample size and labeling method; T02 (three records of the same event group without losing sources, no tripled importance/corroboration); CU-03 (an agency repeated by several outlets counts as ONE provenance).

## Design
- Themes live in `motor/temas.yaml` (name, description, seed phrases in Spanish): editable by the teammate (his task: define the 6 themes). No labels needed to run: zero-shot by cosine similarity to theme prototypes, with a threshold and margin -> `otros` (abstention) when weak.
- Embeddings cached as `.npy` keyed by model name (derived artifact, gitignored). Model: `paraphrase-multilingual-MiniLM-L12-v2`, downloaded by `make modelos` so the demo works offline.
- Baseline: TF-IDF with the same seeds (centroid similarity). Once the human labels exist, add a supervised TF-IDF + logistic regression for comparison.
- Outputs are DuckDB tables: `clasificacion` (id_noticia, metodo, tema, score, segundo_tema, margen) and for grouping `grupos` / `grupo_noticias` (group id, size, distinct provenances, date range, representative headline).
- Grouping: embedding similarity within a time window (days), complete or average linkage with a threshold; provenance = distinct source key (outlet; wire/agency content counts once).
- Blind labeling sample: `motor/muestra_etiquetado.py` writes ~100 stratified recent headlines WITHOUT model output for the teammate to label; `motor/evaluar.py` computes macro-F1, per-class precision/recall and confusion for each method.

## Tasks
- [ ] T1 Dependencies, `make modelos`, `make clasificar`, `motor/temas.yaml`
- [ ] T2 `motor/clasificar.py`: embeddings cache, zero-shot classifier with abstention, TF-IDF baseline, tables in DuckDB
- [ ] T3 `motor/agrupar.py`: event grouping with provenance counting, T02/CU-03 behavior
- [ ] T4 `motor/muestra_etiquetado.py` + `motor/evaluar.py` (macro-F1 on human labels)
- [ ] T5 Tests, real run, README, bitacora (TAR-007, T02), commits
