# Notion epics and tasks board (repo is source of truth)

## Scope
Add epics and loose tasks to `bitacora/tareas.yaml`, with epic progress visible in Notion. The repo stays the single source of truth; `notion_sync.py` renders it.

## Decisions (user)
- Option B: unify, the repo drives. No manual task board in Notion.
- The Tareas base moves to the user's page `HackIAthon · Tareas` (id `3f2265e2-1333-80dc-a256-dbf38dced376`, simulation workspace), configured via env `NOTION_TAREAS_PAGE_ID`.

## Design
- tareas.yaml fields added: `tipo` (Épica | Tarea, default Tarea), `epica` (epic ID on a task, e.g. EPI-002).
- Epic IDs use prefix `EPI-`; tasks keep `TAR-`.
- Epic `Progreso` (text bar, e.g. `██████░░░░ 60% (3/5)`) and `Estado` are derived on sync from child tasks; never edited by hand.
- CLI: `bitacora.py epica "title"`, `bitacora.py tarea "title" --epica EPI-002`.
- Initial epics: EPI-001 Gestión con la organización (TAR-001..004), EPI-002 Datos (TAR-005,006), EPI-003 Motor de IA (TAR-007..009), EPI-004 Producto e interfaz (TAR-010), EPI-005 Pruebas y entrega (TAR-011,012).

## Tasks
- [ ] T1 Schema + CLI: `tipo`/`epica` in bitacora.py and tareas.yaml (5 epics, 12 tasks assigned)
- [ ] T2 notion_sync.py: new properties, derived epic progress/state, Tareas base under NOTION_TAREAS_PAGE_ID, migrate old base
- [ ] T3 Tests for progress/state derivation and validation (epic refs exist)
- [ ] T4 Real sync against simulation workspace and visual check
- [ ] T5 Docs (README) and work-unit commit(s)
