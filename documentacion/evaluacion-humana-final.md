# Evaluación humana final

## Alcance y método

Esta evaluación cubre las cinco fichas finales y sus **12 afirmaciones generadas**. Por ello, el denominador es 12: no se rellenó artificialmente hasta 30 afirmaciones.

OpenAI preparó comparaciones locales entre cada afirmación y su cita. Antigravity comprobó independientemente las URL públicas cuando fue posible. Víctor emitió todos los juicios humanos finales; las comprobaciones previas son evidencia de apoyo, no sustituyen su decisión.

## TAR-035 — Validez del sustento

| # | id_caso | Resumen de la afirmación | Cita (id · campo) | Juicio de Víctor | Razón |
|---:|---|---|---|---|---|
| 1 | G-49282420d812 | Encuentro Mulino: Canal, integración, comercio, inversiones y cooperación | N-2355941fb1b9 · titulo | respaldada | La paráfrasis conserva el significado del título citado. |
| 2 | G-49282420d812 | Encuentro Mulino: Canal, integración, comercio, inversiones y cooperación | N-51098bc1516f · titulo | ambigua | La paráfrasis pierde un matiz relevante del título oficial. |
| 3 | G-58502841e2c7 | Sismo de 5,9 grados en Costa Rica y Panamá | N-b54f87b3ab7f · titulo | respaldada | Solo cambia el tiempo verbal; el hecho coincide. |
| 4 | G-99f6cccc1c81 | Inflación cayó 0,3 % en junio | N-5bbcc5b41e73 · titulo | respaldada | La cifra y el período coinciden. |
| 5 | G-99f6cccc1c81 | Inflación mensual regresa a terreno negativo | N-0791777829d4 · titulo | respaldada | Reproduce sustancialmente el titular. |
| 6 | G-99f6cccc1c81 | Inflación cae 0,3 % en junio por baja de combustibles | N-a637b64c9689 · titulo | respaldada | Coinciden cifra, período y factor citado. |
| 7 | G-99f6cccc1c81 | Inflación de Panamá en 2024: 0,6932 % | IND-PAN-FP.CPI.TOTL.ZG-2024 · valor | no respaldada | Víctor juzgó insuficiente el indicador para sostener la formulación. |
| 8 | G-9dd46610ff94 | Cambios al Reglamento de Tránsito para scooters y motos eléctricas | N-89ef67ca6db3 · titulo | no respaldada | Víctor juzgó insuficiente la cita para sostener la formulación. |
| 9 | G-c7e0cc7bcfce | Sheinbaum y Mulino hablarán de economía y neutralidad del Canal | N-4a0277c2b382 · titulo | respaldada | Los actores y la agenda coinciden con la cita. |
| 10 | G-c7e0cc7bcfce | Reunión sobre economía y neutralidad del Canal | N-bec289824840 · titulo | respaldada | “Serán temas” y “tratará sobre” preservan el mismo significado. |
| 11 | G-c7e0cc7bcfce | Sheinbaum apoya la neutralidad del Canal | N-44279b96fa14 · titulo | respaldada | El título preservado localmente coincide sustancialmente; la página externa fue inaccesible. |
| 12 | G-c7e0cc7bcfce | Sheinbaum y el presidente de Panamá hablarán de economía y neutralidad | N-034e82ccd7a1 · titulo | no respaldada | Víctor juzgó insuficiente la evidencia disponible; la página externa fue inaccesible. |

**Resultado:** 8 respaldadas, 1 ambigua y 3 no respaldadas. La validez de sustento es **8/12 = 66,7 %**; la ambigua queda fuera del numerador. La meta de **≥90 % no se cumplió**.

### Acceso externo comprobado por Antigravity

Antigravity encontró 7 páginas de noticias con coincidencia literal, 2 con coincidencia parcial y 2 inaccesibles o no verificables; el indicador oficial se comprobó localmente. Este resumen es evidencia complementaria de acceso externo, no una decisión humana ni un reemplazo de los juicios de Víctor.

## TAR-036 — Precision@5

La evaluación anterior sobre cinco fichas finales no correspondía al top cinco actual y se reemplaza íntegramente por los grupos actuales de DuckDB, ordenados por puntaje DESC, U DESC y grupo_id.

| id_caso | Registro final | Juicio de Víctor | Razón |
|---|---|---|---|
| G-0fee038b990b | US donation of USD 500,000 for shelters/emergencies | relevante | La ayuda humanitaria y la respuesta de emergencia tienen interés público nacional. |
| G-9d6c477049d9 | Carnival Miracle/cruise season/more than 220 transits | relevante | El turismo, la actividad portuaria y el Canal tienen impacto económico nacional. |
| G-9f2630b6d7d1 | City of Stars 2026 municipal holiday festival | relevante | Es información de servicios y agenda cultural para la audiencia. |
| G-b4cdd9db855e | Mitradel job vacancies | relevante | Las oportunidades de empleo tienen utilidad pública directa. |
| G-cfe160debe8e | Panama condemns October 7 attacks and calls for peace | no relevante | Víctor juzgó que no debe contar como acierto editorial del top cinco. |

**Resultado:** Precision@5 = **4/5 = 80 %**, según juicio humano independiente de Víctor.

## TAR-037 — Auditoría de T03–T10

Todos los registros T03–T10 tienen todos los campos estructurados. No obstante, T06, T08 y T09 contienen correcciones genéricas; la evidencia de T07 no es reproducible porque dice “Salida de pytest correspondiente”; y la entrada y corrección de T10 son genéricas.

`bitacora/pruebas.yaml` **no fue editado**. Estos hallazgos deben enviarse a Guille, propietario de TAR-033, para completar la evidencia técnica sin conflicto de edición.
