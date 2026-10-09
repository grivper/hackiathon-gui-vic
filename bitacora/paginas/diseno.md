# Diseño de solución
## Flujo
1. Cargar: validación del snapshot y reporte de calidad
2. Organizar: clasificación temática y agrupación de eventos (IA)
3. Contextualizar: vínculo con indicadores y eventos oficiales
4. Priorizar: P = 30R + 25I + 20U + 15N + 10E, reglas versionadas
5. Explicar: ficha de evidencia
6. Producir: borrador con citas por afirmación (IA)
7. Revisar: aprobación humana y registro en Notion
## Almacenamiento
DuckDB local. Ver DEC-003.
## Modelos y versiones
- Embeddings: paraphrase-multilingual-MiniLM-L12-v2 (sentence-transformers, CPU, funciona sin internet con la caché local). Ver DEC-006.
- Baseline de clasificación: TF-IDF con scikit-learn. Macro-F1 0,339 con embeddings frente a 0,145 con TF-IDF.
- LLM local: gemma3:4b con Ollama 0.40.1 (solo CPU, sin API externa). Opciones medidas: num_ctx=4096, num_predict=768, temperature=0, seed=7. Ver DEC-008.
- Rendimiento medido (n=10): mediana 18,87 s, p95 41,04 s; por eso las fichas finales se pregeneran antes de la demo.
- Reglas de puntaje: v0.3
## Límites del sistema
- Las noticias solo incluyen titular y metadatos
- No etiqueta noticias como verdaderas o falsas
