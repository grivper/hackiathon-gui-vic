# DuckDB load with quality report (T01) and mirrored setup

## Scope
Load the processed snapshot into a local DuckDB and produce a quality report (T01). Both teammates must get identical data from git, and setup must be one idempotent command that agents can run on their own.

## Design (user approved the direction)
- `data/processed/*` + `data/manifest.json` + `data/diccionario.md` are committed (frozen dev snapshot, ~9 MB). `data/raw/` and `data/*.duckdb` stay out of git.
- `data/senales.duckdb` is derived: built by `make db` from the committed CSV/GeoJSON. Never committed.
- `make db` is idempotent: it stores the manifest SHA-256 in a `meta` table and skips the rebuild when it matches (`--forzar` rebuilds).
- `make arrancar` = `make instalar` + `make db`.
- Mirror check: the manifest hash is printed in the quality report; same hash means same data.
- T01 (challenge): a file with invalid dates and nulls must be validated, errors separated, nulls kept, and the load must not abort.
- Agent automation: `AGENTS.md` session-start rule: after `git pull --rebase`, run `make arrancar`, announcing it first. Only one person regenerates the snapshot (`make datos`) and commits it.

## Tasks
- [ ] T1 `motor/cargar_db.py` + `make db` / `make arrancar`: tables noticias, indicadores, eventos, excluidos, meta; invalid rows go to a rejects table, nulls kept
- [ ] T2 Quality report (`data/reporte_calidad.md` and a table): counts, null rates, invalid dates, duplicate URLs/IDs, monthly coverage, World Bank grid completeness, manifest hash; non-zero exit only on fatal problems
- [ ] T3 Tests (fixture with bad dates and nulls proving T01 behavior, idempotency by hash)
- [ ] T4 .gitignore + commit the snapshot (processed, manifest, diccionario) and AGENTS.md session-start rule
- [ ] T5 Real run, README, DEC-005, register T01 result in the bitacora, commit
