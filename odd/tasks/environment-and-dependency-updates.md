# Environment and dependency updates

## Scope
Update verified stale development tooling and Python dependencies without changing the bundled Pi runtime managed by Gentle Shell maintainers.

## Tasks

- [x] T1 Upgrade the Engram CLI from 3.0.0 to 3.1.0. Evidence: `gentle-ai upgrade` succeeded; backup `upgrade-20261006T201757Z`.
- [x] T2 Update the isolated-home `pi-web-access` package from 0.35.0 to 0.37.0. Evidence: `gentle-shell update npm:pi-web-access` completed.
- [x] T3 Refresh `requirements.txt` in an isolated Python virtual environment and validate compatibility. Evidence: direct pins installed successfully and `make test` passed (5 tests).
- [x] T4 Re-run focused diagnostics and project tests. Evidence: `gentle-ai update` reports all tools current; `gentle-ai doctor` is healthy (8 passed); post-refresh `make test` passed (5 tests).

## Constraints

- Do not alter Gentle Shell's bundled Pi 1.0.1.
- Do not edit the parent Git repository configuration.
- Do not commit: this project is not a standalone Git repository.

## Evidence

- T1: `gentle-ai upgrade` upgraded Engram successfully and preserved a configuration backup.
- T2: `gentle-shell update npm:pi-web-access` completed. npm reported two high-severity dependency audit findings; no audit fix was applied.
- T3: Baseline and refreshed environments both passed `make test` (5 passed). Installed direct pins: requests 2.34.2, PyYAML 6.0.3, python-dotenv 1.2.4, feedparser 6.0.14, pytest 9.1.1.
- T4: `gentle-ai update` reports all managed tools current. `gentle-ai doctor` is healthy (8 passed, 0 failed, 0 warnings). The isolated `pi-web-access` package is version 0.37.0. Native review preflight was blocked because the parent Git root includes the nested `Design` repository; no review transaction was created.
