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

- Install and run commands: `make instalar`, `make datos`.
- Test, lint, typecheck, and build commands: `make test` or `.venv/bin/python -m pytest tests -q`; `python notion_sync.py --dry-run` validates the log files.
- Manual checks required for this project: Pending.

## Reference documents

- Architecture and requirements: `documentacion/traspaso-hackiathon-tvn.md`, `documentacion/reto-tvn-media.md`.
- UI or design system: Pending.
- Data and security: Never commit `.env` or any `.env.*` with real tokens; no secrets in git. Scrape metadata only, do not redistribute article text.

## Project-specific rules

- **Sync reminder (mandatory).** Every time a task changes state, or the user says they are stopping, leaving, or ending the session, remind them of this checklist, in order, before closing:
  1. Record the progress: `python bitacora.py estado TAR-xxx "Hecho"` (or edit `bitacora/*.yaml`).
  2. Commit the work (Conventional Commit).
  3. `git pull --rebase` and then `git push` so the teammate sees it.
  4. Sync Notion: `python notion_sync.py`. Only one person syncs at a time (currently Guille), because the sync state is local and a second sync duplicates pages.
- **Session start.** Remind the user to run `git pull` before starting work, so they do not overwrite the teammate's changes.
- Keep these reminders short, one message, and never push or run the sync without the user's go-ahead.

## Relevant skills

- `gentle-ai-work-unit-commits` for commits, `test-driven-development` for behavior changes.
