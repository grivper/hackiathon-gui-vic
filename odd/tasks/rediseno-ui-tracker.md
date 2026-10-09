# Editorial UI redesign: PR chain

Tracker for a chain of five PRs (feature-branch chain). This PR stays draft and is not merged until every child is reviewed and integrated.

| # | Branch | Scope |
|---|--------|-------|
| 1 | `feat/rediseno-ui-01-fichas-docs` | Initial UI styles, regenerated fichas and Ollama setup docs |
| 2 | `feat/rediseno-ui-02-bandeja-ficha` | Inbox and ficha split as two pages, design references |
| 3 | `feat/rediseno-ui-03-chat` | Chat: input below messages, fixed-height history, example questions |
| 4 | `feat/rediseno-ui-04-pulido-resumen` | Button states, larger text, rank, readable topic filter, R/I/U/N/E rows |
| 5 | `feat/rediseno-ui-05-generar-borrador` | On-demand draft generation and the package expander |

Child 1 targets this branch; each later child targets the previous one.
