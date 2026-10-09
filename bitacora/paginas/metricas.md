# Métricas de la ejecución
> Reportar numerador, denominador y fallos; no esconder errores tras un promedio.

Datos: snapshot con manifest `81640bd328e6`. Modelo local `gemma3:4b` (Ollama 0.40.1, solo CPU). Costo de API: USD 0 (sin servicio externo). Los tokens se reportan solo donde fueron medidos.

## Resumen

| Métrica | Resultado | Numerador / denominador | Estado |
|---|---|---|---|
| Cobertura de citas | 100 % | 12 / 12 afirmaciones con citas estructurales | Medida |
| Validez del sustento | 66,7 % | 8 / 12 afirmaciones válidas (1 ambigua, 3 no respaldadas) | Medida (meta ≥90 % no cumplida) |
| Abstención correcta | 100 % | 10 / 10 (6 sin evidencia + 4 adversarias) | Medida, casos sintéticos |
| Abstenciones incorrectas | 29,2 % | 7 / 24 consultas respondibles | Medida |
| Macro-F1 (embeddings) | 0,339 | 93 etiquetas humanas | Medida |
| Macro-F1 (baseline TF-IDF) | 0,145 | 93 etiquetas humanas | Medida |
| Precision@5 | 80 % | 4 / 5 registros relevantes en el top-5 | Medida |
| Tiempo mediano / p95 | 18,87 s / 41,04 s | n = 10 | Medida |

## Detalle y errores conservados

- **Cobertura de citas:** estructural; el código valida que cada afirmación apunte a una evidencia existente. No equivale a validez del sustento.
- **Validez del sustento:** el reto exige al menos 30 afirmaciones revisadas por una persona, con meta de 90 %. Las 5 fichas tienen solo 12 afirmaciones, por eso el denominador es 12. La meta no se declara cumplida (66,7 %). Evaluación detallada en `documentacion/evaluacion-humana-final.md` (TAR-035).
- **Abstención correcta:** los 10 casos son sintéticos (benchmark TAR-011). Miden el mecanismo, no la calidad sobre datos reales.
- **Abstenciones incorrectas (7):** TAR023-007, 008, 009, 011, 016, 017 y 018. Eran consultas con evidencia disponible y el sistema se abstuvo (recall de evidencia 0 %). Acierto de respuesta: 17 / 24 (70,8 %).
- **Benchmark global:** 40 consultas, acierto de tipo 82,5 %; contradicciones 6 / 6, evaluadas contra fichas sintéticas. Recall promedio de evidencia en consultas de respuesta: 27,1 %. Detalle: `documentacion/evidencia-benchmark.md`.
- **Macro-F1:** muestra pequeña con soportes por clase bajos (turismo n = 2, regulación n = 3). Se probaron 8 variantes de ajuste; se descartaron porque mejoraban la muestra de 93 pero empeoraban el control independiente de 24 titulares. Detalle: `data/evaluacion_clasificacion.md`.
- **Precision@5:** 4/5 = 80%, juicio humano independiente de Víctor sobre los cinco grupos actuales de DuckDB. Detalle en `documentacion/evaluacion-humana-final.md` (TAR-036).
- **Segunda opinión humana:** otra persona del equipo revisó 23 afirmaciones reales y obtuvo 19 / 23 = 82,6 % de validez del sustento (90,5 % sin contar las ambiguas) y 2 / 5 = 40 % de Precision@5 sobre los mismos cinco grupos. Las dos revisiones pertenecen al equipo y no son ciegas ni externas; la diferencia se debe a criterios de relevancia distintos y a una muestra de solo cinco registros. Detalle: `documentacion/segunda-opinion-humana.md`.
- **Rendimiento:** la meta de mediana de 15 s no se cumplió (18,87 s). Mediana de 9,86 tokens/s; JSON válido 10 / 10; al menos una cita válida 9 / 10. Por eso las fichas finales se pre-generan antes de la demo. Detalle: `documentacion/evidencia-modelo-real.md`.
- **Ahorro de tiempo:** tarea manual estimada en 20 min frente a 1,25 min asistida (una sola tarea medida; dato orientativo).
