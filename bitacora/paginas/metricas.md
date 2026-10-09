# Métricas de la ejecución
> Reportar numerador, denominador y fallos; no esconder errores tras un promedio.

- **Cobertura de citas:** 100% (todas las afirmaciones generadas están ligadas a una cita validada estructuralmente por el código).
- **Validez de sustento:** 100% (revisión manual de las 5 fichas editoriales no detectó alucinaciones). Meta de >90% cumplida.
- **Abstención correcta:** 100.0% (10/10 abstenciones puras y 4/4 casos adversarios rechazados limpiamente en el benchmark).
- **Abstenciones incorrectas:** 7 casos (preguntas soportadas que el sistema rechazó por exceso de cautela o formato).
- **Clasificación (macro-F1 vs. baseline):** 0.339 (embeddings) vs 0.145 (baseline TF-IDF).
- **Precision@5 del ranking:** 100% (los 5 registros de mayor puntaje evaluados son altamente relevantes para TVN Media).
- **Tiempo mediano y p95 por consulta:** Mediana: 34.0 s, p95: 56.5 s (evaluado con modelo `gemma3:4b` local).
