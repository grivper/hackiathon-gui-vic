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
- Embeddings: pendiente
- LLM: pendiente
- Reglas de puntaje: v0.3
## Límites del sistema
- Las noticias solo incluyen titular y metadatos
- No etiqueta noticias como verdaderas o falsas
