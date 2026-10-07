---
name: hackiathon-gui-vic
description: Project-specific development instructions for hackiathon-gui-vic (HackIAthon, TVN Media challenge).
---

# hackiathon-gui-vic

## Purpose

- What this project does: Prototype for the HackIAthon TVN Media challenge. It turns scattered sources into an investigable topic with evidence and a responsible draft (layered RAG: embeddings organize, a local LLM only drafts, code validates citations, scores and abstains).
- Who uses it: Two-person team (Guille: data, engine, AI; Victor: product, UI, Notion, tests). Deadline: Thursday 2026-10-08 23:59 (Panama).

## Stack

- Languages and frameworks: Python, DuckDB, sentence-transformers, scikit-learn (TF-IDF baseline), Streamlit, pytest.
- Package manager: pip with `requirements.txt` and `.venv` (`make instalar`).
- Database and external services: DuckDB (local), Ollama (local LLM, no external LLM API), Notion (project log via `notion_sync.py`), GitHub (private repo).
- Deployment platform: Pending (offline demo on a local machine).

## Architecture

- Main source directories and their responsibilities: `ingesta/` (source download and snapshot), `bitacora/` (decisions, tasks, tests and Notion pages as YAML/Markdown), `bitacora.py` (log CLI), `notion_sync.py` (repo to Notion), `documentacion/` (challenge text and handoff), `tests/`, `odd/tasks/` (feature plans).
- Important boundaries or conventions: The repo is the source of truth for the project log; Notion only mirrors it. Never edit synced Notion content by hand, it is overwritten.
- Existing patterns to preserve: Epic state and progress are derived on sync (`EPI-` ids), not edited by hand.

## Development and verification

- Install and run commands (venv active): `make arrancar` (instalar + db), `make db`, `make datos` (only the snapshot owner).
- Test, lint, typecheck, and build commands: `make test` or `.venv/bin/python -m pytest tests -q`; `python notion_sync.py --dry-run` validates the log files.
- Manual checks required for this project: Pending.

## Reference documents

- Architecture and requirements: `documentacion/traspaso-hackiathon-tvn.md`, `documentacion/reto-tvn-media.md`.
- UI or design system: Pending.
- Data and security: Never commit `.env` or any `.env.*` with real tokens; no secrets in git. Scrape metadata only, do not redistribute article text.

## Project-specific rules

- **Standing authorization (granted by the user): auto-sync.** Every time a task changes state, or the user says they are stopping, leaving, or ending the session, the agent does the following itself, in order, without asking, and reports one short summary at the end:
  1. Record the progress: `python bitacora.py estado TAR-xxx "Hecho"` (or edit `bitacora/*.yaml`).
  2. Verify: `python notion_sync.py --dry-run` and `.venv/bin/python -m pytest tests -q`. If either fails, stop and report; do not commit.
  3. Commit with a Conventional Commit message. Stage only intended files, never `.env` or any `.env.*`.
  4. `git pull --rebase`, then `git push` on the current branch.
  5. `python notion_sync.py`, only if a local `.env` with a Notion token exists. Otherwise skip it and tell the user that the person holding the token must sync (the sync state is local; two people syncing duplicates pages).
- **Safety limits.** Stop and report, never improvise, on any of these: rebase or merge conflict, failing check, push rejected, a secret in the diff, or Notion returning an error. Never force-push, never rewrite history that was already pushed, never push to `main` unless the user asked for it.
- **Session start (standing authorization).** Run `git pull --rebase` before starting work, so the teammate's changes are not overwritten. Then, announcing it to the user first in one line ("voy a correr make arrancar para dejar el entorno y la base DuckDB al día"), activate the venv and run `. .venv/bin/activate && make arrancar` (installs dependencies and builds `data/senales.duckdb`). It is idempotent: it skips the rebuild when `data/manifest.json` has the same SHA-256 as the one stored in the database, so it is cheap to repeat. After that, announce and run `make motor` (model download only if `modelos/` is missing, then classification and event grouping; idempotent, about a minute when nothing changed). Report the manifest hash printed in `data/reporte_calidad.md`; the same hash on both machines means the same data.
- **Data snapshot ownership.** `data/processed/`, `data/manifest.json`, `data/diccionario.md` and `data/reporte_calidad.md` are committed (frozen dev snapshot). `data/raw/` and `data/*.duckdb` are never committed. Only one person regenerates the snapshot (`make datos`, then `make db`) and commits it; the other one never runs `make datos`, just pulls.

## Relevant skills

- `gentle-ai-work-unit-commits` for commits, `test-driven-development` for behavior changes.
