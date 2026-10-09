# Final Delivery Documentation

## Objective
Complete the jury-facing evidence, assign independent review work, and mirror the verified repository source of truth into the event Notion without duplicate synchronization.

## Decisions
- Repository files remain the source of truth; Notion is a mirror.
- All closing work belongs to `EPI-005` (Pruebas y entrega).
- Guille is the recorded reviewer for the five final editorial records.
- Víctor owns independent human evaluation and the event Notion delivery.
- Only Víctor runs the final event-Notion synchronization, after the repository work is merged.

## Tasks

### T1 — Publish closing assignments in EPI-005
- [ ] Add the final delivery tasks for Guille and Víctor to `bitacora/tareas.yaml`.
- [ ] Validate the task schema and synchronize the shared Notion board.
- Evidence: pending.

### T2 — Correct metrics and technical evidence
- [ ] Replace stale latency values with the official median and p95.
- [ ] Record numerators, denominators, evaluated cases, and known errors.
- [ ] Strengthen T01 and T02 reproducibility evidence.
- Evidence: pending.

### T3 — Complete independent human evaluation
- [ ] Víctor reviews up to 30 claims for support validity.
- [ ] Víctor independently evaluates the five Precision@5 results.
- [ ] Preserve the judgments, reasons, and calculation inputs.
- Evidence: pending.

### T4 — Reconcile tests and editorial records
- [ ] Audit T03–T10 for complete structured evidence.
- [ ] Record Guille as reviewer for the five final records.
- [ ] Preserve the intentionally insufficient-evidence case.
- Evidence: pending.

### T5 — Mirror the verified content to the event Notion
- [ ] Prepare the landing page with technical, functional, and Pitch Day links.
- [ ] Synchronize the final repository state exactly once to the event workspace.
- [ ] Add detailed evidence that `notion_sync.py` does not map automatically.
- Evidence: pending.

### T6 — Verify and submit the final delivery
- [ ] Open all three public Notion links in an incognito session.
- [ ] Confirm the public repository link and concise explanation.
- [ ] Send the final email with the required links.
- Evidence: pending.

## Constraints
- Do not fabricate human judgments, token counts, or costs.
- Do not let both teammates synchronize the same Notion workspace.
- Do not edit the same repository files concurrently.
- Do not expose `.env`, tokens, or private integration identifiers.

## Verification
- `python notion_sync.py --dry-run`
- `.venv/bin/python -m pytest tests -q`
- Public-link verification in an incognito browser session.

## Commit Evidence
- Pending.
