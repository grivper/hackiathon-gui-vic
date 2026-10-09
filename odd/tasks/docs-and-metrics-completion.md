# Documentation and Metrics Completion

## Objective
Complete missing execution metrics, fill out test evidence for T01-T10, and change the status of the five editorial records from "Nuevo" to a reviewed state to resolve pending items in Notion.

## Scope
- Update `bitacora/paginas/metricas.md` with calculated values for Citation Coverage, Support Validity, Correct Abstention, Incorrect Abstention, Macro-F1, Precision@5, and Performance.
- Update `bitacora/pruebas.yaml` for T01-T10, ensuring each has `entrada`, `evidencia`, and `correccion` fields populated logically.
- Update `data/motor.duckdb` to mark the 5 generated fichas as "aprobado como borrador".

## Constraints
- Do not modify `data/` source CSVs or `.duckdb` table structures.
- Do not use ChatGPT hallucinated fields (like `revisor` in DuckDB/JSONL if it doesn't exist).
