# Repo bootstrap and sharing

## Scope
Make `hackiathon-gui-vic` an independent Git repository, publish it as a private GitHub repo named after the folder, share it with collaborator `vicmat04`, enable the Notion hook, and share project memories via Engram chunks.

## Decisions (user)
- Repo is private for now; may become public after the event.
- Repo name equals the folder name: `hackiathon-gui-vic`.
- Collaborator: `vicmat04`.
- Roles stay "Propuesto" in the bitacora unless both agree.

## Tasks
- [~] T1 Add `.gitignore` (done) and `.env.example` (BLOCKED: Gentle AI safety policy denies writing that path; needs a user-approved plan).
- [x] T2 `git init -b main`, secrets scan clean, first commit `74a9775`.
- [ ] T3 Create private GitHub repo and push; invite `vicmat04`. BLOCKED: `gh` PAT lacks createRepository permission; user creates the empty private repo in the web UI.
- [ ] T4 Enable `core.hooksPath hooks`; validate `notion_sync.py --dry-run`.
- [ ] T5 Export project memories with `engram sync` for the collaborator.

## Constraints
- Do not touch the parent repo `/home/river/Proyectos`.
- No secrets in git. Notion token is entered by the user only.
- Push/repo creation authorized by the user in this session; no PRs or merges.

## Evidence
Pending.
