# Anexo · Bitácora de trabajo del equipo
> El trabajo del equipo queda registrado en el repositorio (carpeta bitacora) y se refleja en este Notion. Este anexo resume esa bitácora.

## Cómo trabajamos
- Guille: motor, datos e IA (ingesta, clasificación, agrupación, puntaje, generación con citas, benchmark y pruebas de aceptación).
- Víctor: producto, interfaz, revisión humana, páginas de Notion y pitch.
- El repositorio es la fuente de verdad. Notion es un espejo: lo que se registra en la bitácora se sincroniza, y nada se edita a mano en Notion.
- Cada cambio entra con commits convencionales y tests; el estado de las tareas se actualiza al cerrarlas.

## Resumen en cifras
- Tareas registradas: 40 en 5 épicas. Hechas: 39. Pendientes: 1.
- Guille: 18 tareas, 18 hechas.
- Víctor: 22 tareas, 21 hechas.
- Decisiones registradas: 8 (ver más abajo).
- Pruebas de aceptación: 10 (T01 a T10), todas ejecutadas; T03, T04 y T05 fallaron primero y se corrigieron.

## Épicas
- Gestión con la organización (Guille): 4 de 4 tareas hechas.
- Datos (Guille): 5 de 5 tareas hechas.
- Motor de IA (Guille): 6 de 6 tareas hechas.
- Producto e interfaz (Víctor): 7 de 8 tareas hechas.
- Pruebas y entrega (Guille): 17 de 17 tareas hechas.

## Tareas de Guille
- TAR-001 · Pedir a la organización el teamspace, cupos y acceso del jurado (Hecho)
- TAR-002 · Confirmar si la organización entrega el snapshot común y en qué fecha (Hecho)
- TAR-003 · Consultar la inconsistencia del intervalo de fechas (sección 6 vs. sección 7) (Hecho)
- TAR-004 · Confirmar si CU-05 (banca) es obligatorio en la modalidad editorial (Hecho)
- TAR-005 · Script de descarga de fuentes y generación de manifest.json (Hecho)
- TAR-006 · Validación de carga y reporte de calidad (T01) (Hecho)
- TAR-007 · Clasificación temática y agrupación de eventos, con baseline TF-IDF (Hecho)
- TAR-008 · Motor de puntaje con reglas versionadas y estado de evidencia (Hecho)
- TAR-009 · Generación con citas y validador de citas (Hecho)
- TAR-011 · Ejecutar T01–T10 y benchmark de desarrollo (Hecho)
- TAR-013 · Recapturar el RSS de TVN cada día hasta el jueves (mínimo 3 capturas más) (Hecho)
- TAR-014 · Reintentar GDELT desde otra red o más tarde (opcional) (Hecho)
- TAR-029 · Ensayar la carga de un paquete de datos simulado: copiar a data/processed y data/manifest.json, correr make db (Hecho)
- TAR-031 · Subir el recall de la clasificación: ajustar umbral_score y umbral_margen y re-evaluar con make evaluar (Hecho)
- TAR-032 · Corregir métricas finales: latencia oficial, numeradores, denominadores, casos y errores (Hecho)
- TAR-033 · Completar evidencia técnica de T01 y T02 con conteos, IDs y errores conservados (Hecho)
- TAR-034 · Registrar a Guille como revisor de las cinco fichas finales y preparar lotes de validación para Víctor (Hecho)
- TAR-040 · Enviar correo final con enlace del repositorio y los tres enlaces de Notion (Hecho)

## Tareas de Víctor
- TAR-010 · Interfaz con bandeja, ficha, borrador y revisión (Hecho)
- TAR-012 · Preparar y ensayar el pitch desde Notion con demo offline (Hecho)
- TAR-015 · Definir y ajustar los 6 temas en motor/temas.yaml (descripción y semillas) (Hecho)
- TAR-016 · Etiquetar a ciegas los 104 titulares de data/etiquetas/muestra_etiquetado.csv y correr make evaluar (Hecho)
- TAR-017 · Interfaz: bandeja de temas y grupos priorizados con filtros por tema y fecha (CU-01) (Hecho)
- TAR-018 · Interfaz: ficha de evidencia del grupo con procedencias, corroboración y fecha original (Hecho)
- TAR-019 · Interfaz: panel de contexto oficial con indicadores del Banco Mundial y sismos USGS (Hecho)
- TAR-020 · Interfaz: caja de consulta con respuesta citada o abstención (CU-04) (Hecho)
- TAR-021 · Interfaz: borrador con citas y revisión humana con los 5 estados (Hecho)
- TAR-022 · Instalar Ollama en la máquina de la demo y medir la latencia de gemma3:4b (modelo vigente; meta mediana 15 s) (Hecho)
- TAR-023 · Escribir las 40 consultas de desarrollo del benchmark (Hecho)
- TAR-024 · Preparar las 5 fichas finales, una con evidencia insuficiente (Hecho)
- TAR-025 · Medir tiempo manual frente a asistido en una tarea equivalente (Hecho)
- TAR-026 · Redactar las páginas de Notion Inicio, Riesgos y Presentación (bitacora/paginas) (Hecho)
- TAR-027 · Crear datos sintéticos para las pruebas T03, T05 y T07 y registrar los resultados con bitacora.py prueba (Hecho)
- TAR-028 · Interfaz: conectar la interfaz a las tablas de data/motor.duckdb (contrato en documentacion/interfaz-brief.md) (Hecho)
- TAR-030 · Opcional, solo si sobra tiempo: pantalla 'Cargar paquete' en la interfaz que dispare make db y make motor (Pendiente)
- TAR-035 · Revisar 30 afirmaciones y calcular validez del sustento con razones por caso (Hecho)
- TAR-036 · Evaluar independientemente Precision@5 de los cinco temas mejor posicionados (Hecho)
- TAR-037 · Auditar T03-T10 e informar campos faltantes sin editar pruebas.yaml (Hecho)
- TAR-038 · Preparar en el Notion del evento la página con enlaces técnico, funcional y Pitch Day (Hecho)
- TAR-039 · Sincronizar una sola vez el Notion del evento y verificar los tres enlaces públicos (Hecho)

## Decisiones registradas
- DEC-001 · Documentación como código, sincronizada con Notion por API (Vigente)
- DEC-002 · Modalidad editorial (TVN · principal) (Vigente)
- DEC-003 · Base de datos local (DuckDB); Notion solo como bitácora y presentación (Vigente)
- DEC-004 · Período de datos: entrenar y probar con cualquier fecha y fuente; demo con datos recientes (desde 2025-10-02, fin 2026-09-30 por confirmar) (Vigente)
- DEC-005 · Snapshot de datos en git y base DuckDB derivada (make db), idempotente por hash del manifest (Vigente)
- DEC-006 · Clasificación por embeddings multilingües con prototipos por tema, grupos de contraste y abstención; TF-IDF como baseline; agrupación por similitud con ventana y tope de 3 días (Vigente)
- DEC-007 · Roles: Guille en datos, motor e IA; Víctor en interfaz, Notion, pruebas de producto y pitch (Vigente)
- DEC-008 · LLM local con Ollama: gemma3:4b para la generación de las fichas, corriendo uno por vez con contexto acotado (Vigente)

## Correcciones y fallos conservados
- T03 · Noticia antigua recirculada: falló y se corrigió. generar._contexto_noticia escribe por código la fecha de publicación original, o 'detectada ... fecha de publicación no disponible', y marca 'vuelve a circular, no es un evento nue
- T04 · Cifra anual del Banco Mundial: falló y se corrigió. evidencia incluye pais_iso3 y generar._borrador agrega por código 'Panamá · año · unidad; dato anual, no una medición de hoy'. Una cifra no sustentada sigue descartada por el valid
- T05 · Dos afirmaciones incompatibles: falló y se corrigió. Prompt con regla 5 más clara y un ejemplo corto de contradicción; generar.py trata 2 o más 'versiones' como contradicción aunque el modelo diga 'respuesta'. Un primer intento con u

## Dónde ver el detalle
- Bases Tareas y Decisiones: página 2 · Plan y decisiones.
- Matriz de pruebas: página 6 · Pruebas y métricas.
- Código, tests y commits: repositorio público en GitHub (https://github.com/grivper/hackiathon-gui-vic).
