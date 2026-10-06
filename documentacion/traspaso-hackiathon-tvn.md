# Traspaso de contexto · HackIAthon, reto TVN Media

Documento para que otro asistente retome el trabajo sin contexto previo. Fecha de corte: martes 6 de octubre de 2026 (hora de Panamá).

## 1. Contexto y objetivo

- **Usuario:** Guille, desarrollador de software independiente en Panamá (su foco habitual son herramientas AML/KYC y SaaS). Prefiere entregables concretos y listos para copiar. Comunicación en español.
- **Evento:** HackIAthon (cuarta edición), organizado por Viamatica y ADEN. Reto de TVN Media: **"De la señal a la decisión · Copiloto de inteligencia informativa y análisis de entorno con IA"**.
- **Plazo:** comenzó el martes 6 de octubre de 2026; la entrega es el **jueves 8 de octubre de 2026 a las 23:59** (confirmado por el usuario). Nota: en la conversación se dijo por error "miércoles 8"; el 8 de octubre de 2026 es jueves.
- **Equipo:** 2 personas (Guille y victor programadores).
- **LLM:** no tienen ninguna API de LLM. Solo modelos locales (se propuso Ollama).
- **Datos oficiales:** la organización todavía no entregó el paquete de datos común.
- **Notion:** la organización avisó que el teamspace va a demorar y que avancen; se trabaja en el Notion personal de Guille y se migra después.
- **Objetivo:** construir en ~60 horas un prototipo que convierta noticias públicas e indicadores oficiales en una bandeja de temas priorizados, fichas de evidencia y borradores editoriales con citas, con revisión humana y todo documentado y presentado desde Notion.

## 2. Resumen del reto (lo esencial del PDF de 12 páginas)

**Idea central:** la innovación no es producir texto, sino reducir el tiempo para encontrar un tema relevante, mostrar qué evidencia existe, qué falta verificar y entregar un resultado trazable. Toda afirmación factual debe vincularse con fuente, fecha y alcance. Nada se publica automáticamente; todo es borrador para revisión humana.

**Modalidades:** editorial TVN (recomendada), TVN digital, o banca (alternativa). Usuario elegido: editor/a y periodista de TVN.

**Flujo obligatorio de 7 etapas:**
1. Cargar: leer el snapshot, validar IDs, URLs, fechas, campos obligatorios y nulos; emitir reporte de calidad.
2. Organizar: clasificar en 6 temas (economía, logística/Canal, turismo, servicios públicos, eventos naturales, regulación) y agrupar noticias del mismo evento.
3. Contextualizar: relacionar con indicadores/eventos oficiales mostrando período, unidad y limitaciones; no forzar relaciones.
4. Priorizar: puntaje de atención con componentes; distinguir relevancia de suficiencia de evidencia.
5. Explicar: ficha (qué se reporta, quién, qué está respaldado, qué falta, acción recomendada).
6. Producir: borrador con cita por afirmación; distinguir hecho, declaración, inferencia e hipótesis.
7. Revisar: aceptación, corrección o descarte por una persona; registrar en Notion (manual válido, automatizar es opcional).

**Salida TVN:** brief ≤250 palabras, título, enfoque de interés público, 3 preguntas de investigación, fuentes y verificaciones pendientes; guion de 45–60 s; copy digital ≤80 palabras. No inventar entrevistas, citas, imágenes ni afirmaciones. Si solo hay titular/metadatos, la salida debe decir "basado únicamente en titular/metadatos".

**Casos de uso:** CU-01 cinco temas para la agenda con ranking, evidencia y vacíos; CU-02 tema económico con serie oficial sin confundir dato anual con medición actual; CU-03 distinguir repetición de corroboración (una agencia replicada = una procedencia); CU-04 cifra inexistente o contradicción → abstenerse o mostrar versiones; CU-05 (banca) señales del entorno logístico.

**Puntaje:** P = 30R + 25I + 20U + 15N + 10E, componentes normalizados 0–1 con criterios documentados (R relevancia, I impacto, U urgencia, N novedad, E evidencia). Rangos: bajo [0,40), medio [40,70), alto [70,100]. Empates: mayor urgencia, luego ID. Mostrar versión de reglas. **Estado de evidencia independiente:** insuficiente / parcial / suficiente para el borrador. Nunca etiquetar noticias como verdaderas o falsas.

**Notion (obligatorio, 15 puntos y condición de admisión):** 8 páginas: Inicio del reto; Plan y decisiones; Catálogo de datos; Diseño de solución; Casos y evidencias; Pruebas y métricas; Riesgos y ética; Presentación al jurado. Mínimos de admisión: URL accesible al jurado, plan con ≥8 tareas y ≥3 decisiones justificadas registradas durante la ejecución, catálogo completo, ≥5 fichas trazables (una con evidencia insuficiente), matriz T01–T10 con métricas, pitch de 10 min desde Notion (PDF/PPT no lo reemplaza).

**Datos (paquete "Panamá · Señales y Evidencias v1"):**
- A · Noticias: TVN RSS + GDELT DOC 2.0. Meta 200 únicas; mínimo 100 con ≥20 de TVN; 30 días previos a la extracción (ampliable a 90). GDELT máx. 250 artículos por consulta: dividir por fechas y deduplicar por URL. Solo metadatos.
- B · Banco Mundial: PAN, CRI, COL, DOM, MEX, GTM; 2010–2024; indicadores NY.GDP.MKTP.KD.ZG, FP.CPI.TOTL.ZG, SL.UEM.TOTL.ZS, SP.POP.TOTL, IT.NET.USER.ZS, NE.EXP.GNFS.ZS. Conservar nulos. CC BY 4.0.
- C · USGS: sismos 2024, lat 5–12, lon −86 a −76, magnitud ≥3. La caja no equivale a Panamá; solo para hechos sísmicos.
- D · SBP: solo modalidad bancaria (no aplica).

**Contrato de datos (sección 7):** noticias.csv (id_noticia, titulo, url, medio, idioma, fecha_publicacion, fecha_deteccion, fecha_extraccion, tema, origen, alcance_texto); indicadores.csv (pais_iso3, indicador_id, anio, valor nullable, unidad, fuente_url, fecha_extraccion, licencia); eventos.geojson (id, magnitude, time, updated, longitude, latitude, depth, place, status, url); fichas.jsonl (id_caso, modalidad, ids_fuente, afirmaciones, citas, puntaje, componentes, estado_evidencia, borrador, estado_revision); manifest.json (versión, fecha_corte_UTC, consultas, cantidades, licencias, SHA-256, transformaciones). Reglas: UTF-8, IDs estables, ISO 8601 UTC (mostrar hora de Panamá), fecha de publicación distinta de `seendate` de GDELT, no rellenar nulos con cero, cada afirmación cita ID de evidencia + campo. Excluir registros fuera de [2024-01-01, 2025-10-01).

**Benchmark:** benchmark.jsonl con 60 consultas (30 sustentadas, 10 contradicción/ambigüedad, 10 sin respuesta, 10 adversariales); 40 desarrollo, 20 reservadas al jurado (mismas proporciones). Etiquetas por revisión humana; casos alterados marcados como sintéticos; respuestas nunca dentro del corpus.

**IA exigida:** al menos una capacidad ML/NLP (clasificación semántica, similitud para agrupar, extracción de entidades o recuperación semántica; IF/ELSE no cuenta); generación sobre evidencia recuperada con instrucciones separadas del contenido y salida estructurada con citas y vacíos; comparación con un baseline simple explicando cuándo la IA no ayuda; documentar modelo, versión, prompts, parámetros, costo y limitaciones.

**Seguridad:** estados de revisión "nuevo", "en revisión", "requiere evidencia", "aprobado como borrador", "descartado" (aprobar ≠ publicar); anti-alucinación (abstenerse); anti-inyección (texto de fuente = dato); privacidad (sin perfiles; acusaciones como declaraciones); derechos (no redistribuir artículos); credenciales fuera de código, Notion y logs.

**Pruebas T01–T10:** fechas inválidas y nulos; tres registros del mismo evento; noticia recirculada; cifra anual del Banco Mundial; afirmaciones incompatibles; consulta sin respuesta; fuente que pide ignorar instrucciones; prioridad alta (componentes visibles, no habilita publicación); brief con citas y distinción hechos/inferencias; demo sin internet.

**Métricas (orientativas, reportar numerador/denominador/fallos):** cobertura de citas 100%; validez de sustento ≥90% sobre ≥30 afirmaciones revisadas por humano; abstención ≥80% (y reportar abstenciones incorrectas); macro-F1 de clasificación/agrupación contra etiquetas humanas; Precision@5 contra selección independiente de un editor (si no hay, "exploratoria"); tiempo mediano ≤15 s y p95, tokens y costo. Ahorro de tiempo solo medido con tarea manual vs. asistida.

**Entregables:** prototipo ejecutable con demo reproducible sin fuente en vivo; repositorio GitHub con README, instalación, comando de ejecución, dependencias fijadas, .env.example y pruebas; paquete de datos (snapshot, diccionario, manifest, licencias, benchmark de desarrollo; si hay restricciones, metadatos + receta); espacio Notion.

**Rúbrica (100):** Utilidad TVN 20; Prototipo y flujo completo 20; Uso efectivo de IA 15; Evidencias y explicabilidad 15; Notion 15; Calidad técnica 10; Seguridad 5. Nota 0–5 por dimensión; puntaje = Σ(peso × nota/5). Condiciones previas: acceso Notion, documentación, pitch, demo ejecutable, fuentes declaradas, sin secretos; citas falsas deben corregirse antes del cierre.

**Pitch (10 min desde Notion):** 1 problema/usuario; 1 solución/alcance/datos; 4 demo (consulta útil, ficha con citas, borrador, abstención); 2 arquitectura, IA, baseline, métricas; 1 valor medido o hipótesis; 1 riesgos y próximos pasos. +5 min preguntas. Preguntas dinámicas del jurado: origen y año de una cifra; cuántas fuentes independientes si cinco medios replican una agencia; qué pasa sin evidencia o con fuente maliciosa; mostrar en Notion una decisión, una prueba fallida y su corrección.

## 3. Decisiones tomadas

| ID | Decisión | Estado |
|---|---|---|
| DEC-001 | Documentación como código: bitácora en YAML/Markdown dentro del repo, sincronizada a Notion por API en cada registro y en cada commit (hook post-commit) | Vigente |
| DEC-002 | Modalidad editorial (TVN · principal) | Propuesta, falta confirmar |
| DEC-003 | Base de datos local DuckDB; Notion solo como bitácora y presentación (no como base de datos: requiere internet, ~3 req/s, sin búsqueda semántica) | Propuesta, falta confirmar |
| — | Trabajar en Notion personal y migrar al teamspace cambiando NOTION_TOKEN y NOTION_ROOT_PAGE_ID | Acordado |
| — | Snapshot propio de desarrollo (`v0-dev`) con el formato exacto del contrato, reemplazable por el oficial | Acordado |
| — | LLM local con Ollama (candidatos: Qwen2.5 7B o Llama 3.1 8B; medir latencia) | Propuesto, registrar en bitácora |
| — | Roles: Guille motor (datos e IA); compañero producto (interfaz, Notion, pruebas, pitch) | Propuesto, registrar en bitácora |

**Diseño técnico acordado (aún no implementado salvo la ingesta):**
- Stack: Python, DuckDB, sentence-transformers con modelo de embeddings multilingüe, scikit-learn (baseline TF-IDF y agrupación), LLM local vía Ollama con salida JSON, Streamlit, pytest.
- Embeddings para organizar (clasificar, agrupar, buscar); LLM solo para redactar; código determinista para validar, puntuar y decidir abstención.
- Consultas: patrón RAG en capas: interpretar → recuperar (código; para cifras, consulta exacta a la tabla del Banco Mundial) → si no hay evidencia, abstención por código sin llamar al LLM → LLM redacta solo con evidencia en JSON → validador de citas (código) descarta afirmaciones sin ID válido.
- Tres tipos de abstención: indicador no está en el corpus; existe pero el valor es nulo; año fuera de rango.
- Formato de salida del LLM propuesto:
```json
{
  "tipo_respuesta": "respuesta | abstencion | contradiccion",
  "afirmaciones": [
    {"texto": "...", "tipo": "hecho", "id_evidencia": "IND-PAN-SL.UEM.TOTL.ZS-2022", "campo": "valor"}
  ],
  "versiones": [],
  "vacios": ["Falta el dato oficial de turismo"],
  "alcance": "basado únicamente en titular/metadatos"
}
```
- IDs: noticias `N-` + SHA-1 (12 hex) de la URL normalizada; indicadores `IND-<ISO3>-<indicador>-<año>`; sismos con el ID de USGS.
- Criterios iniciales propuestos para el puntaje (a documentar como decisión): R 1,0 si es de Panamá y de uno de los 6 temas, 0,5 regional, 0 sin relación; I por alcance nacional/sectorial/local; U por antigüedad desde fecha de publicación (<24 h 1,0; 1–3 días 0,7; 3–7 días 0,4; >7 días 0,1); N 1,0 evento nuevo, baja si repite y los duplicados no suman; E por procedencias independientes, fuente primaria y dato oficial vinculado. Reglas en un archivo versionado.
- Anti-inyección: titulares entre delimitadores, instrucción explícita de no obedecer contenido, LLM sin herramientas ni secretos, validación de esquema; prueba con palabra canario en un titular sintético.
- Evaluación: etiquetado humano a ciegas de ~100 titulares (tema y evento) para macro-F1 de embeddings vs. baseline TF-IDF; el campo `tema` de noticias.csv es el tema de búsqueda, no una etiqueta. Script de evaluación que corre el benchmark, guarda salidas, calcula métricas automáticas y genera planilla para revisión humana.

## 4. Inconsistencias del PDF y preguntas a la organización

1. Período de noticias: la sección 6 pide los 30 días previos a la extracción, pero la sección 7 excluye todo fuera de [2024-01-01, 2025-10-01). El RSS de TVN solo trae noticias recientes. En la ingesta el filtro quedó configurable y desactivado.
2. La cuadrícula del Banco Mundial dice 1.350 combinaciones, pero 6 países × 6 indicadores × 15 años = 540.
3. ¿CU-05 (banca) es obligatorio en modalidad editorial?
4. ¿Quién arma las 40 consultas de desarrollo del benchmark?
5. ¿La persona editorial designada por la organización estará disponible para Precision@5 y revisión de casos?
6. ¿Se puede usar la descripción del RSS de TVN o solo el titular?
7. ¿Entregarán el paquete de datos común?

Mensaje sugerido al usuario para enviar (estado de envío desconocido):
> Hola, somos el equipo de Guille. Dos consultas: ¿entregarán el paquete de datos común o cada equipo arma el suyo? ¿Qué período de noticias es válido, considerando que la sección 7 excluye todo fuera de [2024-01-01, 2025-10-01)? Gracias.

## 5. Datos técnicos verificados

- **Notion API:** se usa `Notion-Version: 2025-09-03`. En esta versión las bases se crean con `POST /v1/databases` e `initial_data_source`; las filas se crean con `parent.data_source_id`; las consultas van a `POST /v1/data_sources/{id}/query`. Crear una integración interna en el espacio oficial probablemente requiera permisos de administrador.
- **GDELT DOC 2.0:** permite buscar desde 2017, pero el modo de lista de artículos solo considera los últimos 3 meses de la ventana indicada; para cobertura antigua se usan ventanas estrechas. Pide no más de una solicitud cada 5 segundos. Las palabras clave se buscan sobre texto traducido al inglés.
- **TVN RSS:** la URL no se encontró en la web; está en el enlace [2] de la sección 12 del PDF. Debe pegarse en `ingesta/config.yaml` → `tvn.url`.

## 6. Estado actual y problemas pendientes

- Se entregó al usuario `hackiathon-tvn.zip` con el proyecto completo (carpeta `proyecto/`, contenido íntegro en la sección 9). El usuario aún no lo ejecutó; estaba ubicando el archivo.
- `ingesta/descargar_snapshot.py`: 5 pruebas pasan con datos de ejemplo (fusión de duplicados TVN/GDELT, UTC, cuadrícula con nulos, división de ventanas de GDELT, filtro de intervalo, determinismo). **No probado contra las APIs reales** (el entorno del asistente no tenía acceso a esos dominios).
- `notion_sync.py`: probado solo con una simulación de la API (creación de estructura e idempotencia). **No probado contra Notion real.**
- `bitacora.py`: probado localmente (decisión, tarea, estado, prueba con historial, resumen).
- Falta la URL del RSS de TVN.
- Las decisiones DEC-002 y DEC-003 están como "Propuesta"; LLM local y roles no se registraron aún.
- El compañero tiene como tarea instalar Ollama y medir cuánto tarda un modelo de 7–8B en redactar un brief de 250 palabras en la máquina de la demo (meta de mediana ≤15 s).

## 7. Plan de trabajo (días corregidos)

| Momento | Persona A · Motor (Guille) | Persona B · Producto (compañero) |
|---|---|---|
| Mar 6 (hoy) | Repo en GitHub; `make datos`; carga y validación en DuckDB con reporte de calidad (T01) | Ollama y prueba de latencia; bitácora y Notion personal; definiciones de los 6 temas |
| Mié 7 mañana | Embeddings, clasificación con baseline TF-IDF, agrupación de eventos, conteo de procedencias | Interfaz Streamlit (bandeja, ficha) con datos de ejemplo; etiquetar 100 titulares a ciegas; datos sintéticos para T01, T03, T05, T07 |
| Mié 7 tarde/noche | Puntaje con reglas versionadas, vínculo con Banco Mundial, generación con LLM local, validador de citas, abstención | Conectar interfaz al motor; revisión con 5 estados; 40 consultas de desarrollo del benchmark |
| Jue 8 mañana | T01–T10 y benchmark; correcciones | Registrar pruebas y métricas en Notion; medir tiempo manual vs. asistido |
| Jue 8 16:00 | Congelar funcionalidades | |
| Jue 8 tarde | README probado desde cero, revisión de secretos en git, caché del LLM | 5 fichas (una con evidencia insuficiente), página del pitch |
| Jue 8 noche | Ensayo de la demo sin internet, cronometrado | |
| Entrega | Antes de las 22:00 (límite 23:59) | |

Prioridad de recorte si hay atraso: primero USGS, luego extracción de entidades, luego exportación automática de fichas a Notion (copiar a mano), luego modelo LLM de respaldo. Nunca se recorta: flujo completo, validador de citas, abstención, T01–T10, mínimos de Notion.

## 8. Próximos pasos inmediatos para el usuario

1. Enviar el mensaje a la organización (sección 4).
2. Descomprimir `hackiathon-tvn.zip`, subir la carpeta `proyecto` a un repositorio de GitHub y dar acceso al compañero.
3. `make instalar`.
4. Pegar la URL del RSS de TVN en `ingesta/config.yaml`.
5. `make datos` y revisar que haya ≥100 noticias (≥20 de TVN); si faltan, ampliar la ventana de GDELT.
6. Compartir la salida de la consola para revisarla.
7. Configurar la bitácora (README) y registrar decisiones:
```
python bitacora.py estado DEC-002 Vigente
python bitacora.py estado DEC-003 Vigente
python bitacora.py decision "LLM local con Ollama; sin API externa"
python bitacora.py decision "Roles: Guille en datos e IA, compañero en interfaz, Notion y pruebas"
python bitacora.py estado TAR-005 "En curso"
```
8. Siguiente bloque técnico a construir: carga en DuckDB con reporte de calidad (T01), luego embeddings para clasificar y agrupar.

## 9. Archivos del proyecto (contenido completo)

Estructura:
```
proyecto/
├── .env.example
├── .gitignore
├── Makefile
├── README.md
├── requirements.txt
├── notion_sync.py
├── bitacora.py
├── bitacora/
│   ├── tareas.yaml
│   ├── decisiones.yaml
│   ├── pruebas.yaml
│   ├── catalogo.yaml
│   └── paginas/
│       ├── inicio.md
│       ├── diseno.md
│       ├── metricas.md
│       ├── riesgos.md
│       └── presentacion.md
├── hooks/
│   └── post-commit
├── ingesta/
│   ├── config.yaml
│   └── descargar_snapshot.py
└── tests/
    └── test_ingesta.py
```

### `.env.example`

`````text
# Token de la integración interna de Notion (nunca lo subas al repositorio)
NOTION_TOKEN=
# ID o URL de la página raíz donde se crea la estructura
NOTION_ROOT_PAGE_ID=
# 1 = sincronizar automáticamente después de cada registro de bitacora.py
NOTION_AUTOSYNC=1
BITACORA_AUTOR=Guille
DATA_DIR=data
`````

### `.gitignore`

`````text
.env
.notion_state*.json
.notion_sync.log
__pycache__/
.pytest_cache/
# El RSS de TVN trae descripciones de las notas: no se redistribuye (receta: ingesta/).
data/raw/tvn/
`````

### `Makefile`

`````makefile
.PHONY: instalar datos procesar test sync

instalar:
	pip install -r requirements.txt

datos:          ## descarga todas las fuentes y genera el snapshot
	python ingesta/descargar_snapshot.py

procesar:       ## regenera processed/ desde raw/ sin internet
	python ingesta/descargar_snapshot.py --solo-procesar

test:
	python -m pytest -q tests

sync:           ## sincroniza la bitácora con Notion
	python notion_sync.py
`````

### `requirements.txt`

`````text
requests==2.32.3
PyYAML==6.0.2
python-dotenv==1.0.1
feedparser==6.0.11
pytest==8.3.3
`````

### `README.md`

`````markdown
# HackIAthon · Reto TVN Media

## Datos: snapshot propio de desarrollo

Mientras no llegue el paquete oficial, `ingesta/descargar_snapshot.py` descarga las cuatro
fuentes y genera los archivos del contrato de la sección 7 en `data/`.

1. Copia la URL del RSS de TVN (enlace [2] del PDF del reto) en `ingesta/config.yaml` → `tvn.url`.
2. `make datos` (GDELT pide una consulta cada 5 segundos: la descarga completa tarda varios minutos).
3. `make test` para verificar el procesamiento.

El RSS solo trae noticias recientes: conviene ejecutar `python ingesta/descargar_snapshot.py --solo tvn`
varias veces durante el reto; las capturas se acumulan y se deduplican.
Para otro período de GDELT: `--solo gdelt --desde 2025-07-01 --hasta 2025-09-30`.
El `manifest.json` alimenta automáticamente el Catálogo de datos en Notion.

# Bitácora del proyecto sincronizada con Notion

La documentación vive en este repositorio y se refleja en Notion. Cada decisión, tarea
y prueba se registra al momento con su fecha, y cada commit actualiza Notion.

## Configuración (una sola vez)

1. Instala las dependencias: `pip install -r requirements.txt`
2. En Notion, crea una integración interna y copia su token
   (configuración de integraciones: notion.so/profile/integrations).
3. Crea una página vacía, por ejemplo "HackIAthon · TVN". En su menú `···` →
   Conexiones, agrega tu integración.
4. Copia la URL de esa página.
5. `cp .env.example .env` y completa `NOTION_TOKEN` y `NOTION_ROOT_PAGE_ID` (sirve la URL).
6. Activa el hook de git: `git config core.hooksPath hooks`
7. Primera sincronización: `python notion_sync.py`

Se crean las 8 páginas que exige el reto, con bases de datos de Tareas, Decisiones,
Fuentes, Fichas y Matriz de pruebas.

## Uso diario

```
python bitacora.py decision "Usar embeddings multilingües para agrupar"
python bitacora.py tarea "Implementar validador de citas"
python bitacora.py estado TAR-009 "En curso"
python bitacora.py prueba T07 Falló --observado "El agente obedeció al artículo"
python bitacora.py prueba T07 Corregida --correccion "Fuentes delimitadas como datos"
python bitacora.py resumen
```

`decision` pide la justificación si no la pasas: es obligatoria.
`prueba` guarda un historial con cada cambio de estado, así queda visible la
prueba fallida y su corrección, que el jurado pedirá ver.

Las páginas de texto se editan en `bitacora/paginas/*.md`. Las fichas se toman de
`data/fichas.jsonl` y el catálogo de `data/manifest.json` (campo `fuentes`) cuando existan.

**Regla:** todo se edita en el repositorio. Los cambios hechos en Notion a contenido
sincronizado se sobrescriben. Los comentarios en Notion sí se conservan.

## Migración al teamspace oficial

1. Pide a la organización la creación de una integración en el espacio oficial (crearla
   puede requerir permisos de administrador) o permiso para crearla.
2. Crea la página raíz en el teamspace y conéctale la integración.
3. Cambia `NOTION_TOKEN` y `NOTION_ROOT_PAGE_ID` en `.env`.
4. Ejecuta `python notion_sync.py`. Detecta el destino nuevo, respalda el estado anterior
   y crea todo desde los archivos del repositorio.

Notion marcará como fecha de creación el día de la migración. La cronología real queda en
la propiedad **Fecha** de cada registro y en el historial de git; conviene mencionarlo al
jurado. El espacio personal queda como respaldo.

## Si algo falla

- `python notion_sync.py --dry-run` valida los archivos sin llamar a Notion.
- Errores del hook: `.notion_sync.log`.
- Si borraste páginas en Notion: elimina `.notion_state.json` y vuelve a sincronizar.
`````

### `notion_sync.py`

`````python
#!/usr/bin/env python3
"""
Sincroniza la bitácora del proyecto con Notion.

La fuente de verdad son los archivos del repositorio:
  bitacora/tareas.yaml, decisiones.yaml, pruebas.yaml, catalogo.yaml
  bitacora/paginas/*.md
  data/manifest.json  (catálogo de datos, si existe; reemplaza a catalogo.yaml)
  data/fichas.jsonl   (casos y evidencias, si existe)

Notion es un espejo: el script crea la estructura de las 8 páginas si no existe
y actualiza solo lo que cambió. Para migrar a otro espacio basta con cambiar
NOTION_TOKEN y NOTION_ROOT_PAGE_ID en .env y volver a ejecutarlo.

Uso:
  python notion_sync.py             # crea la estructura si falta y sincroniza
  python notion_sync.py --dry-run   # valida los archivos locales sin llamar a Notion
  python notion_sync.py --quiet     # sin salida (lo usa el hook de git)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent
BITACORA = RAIZ / "bitacora"
PAGINAS_MD = BITACORA / "paginas"
ESTADO = RAIZ / ".notion_state.json"
API = "https://api.notion.com/v1"
NOTION_VERSION = "2025-09-03"
MAX_TEXTO = 2000    # límite de Notion por objeto de texto
MAX_BLOQUES = 100   # límite de Notion por solicitud de bloques
SILENCIO = False


def log(msg: str) -> None:
    if not SILENCIO:
        print(msg)


def _sel(*opciones):
    return {"select": {"options": [{"name": o} for o in opciones]}}


_TXT = {"rich_text": {}}
_FECHA = {"date": {}}
_NUM = {"number": {"format": "number"}}

# Páginas en orden de creación (el padre siempre antes que el hijo).
PAGINAS = [
    {"clave": "inicio", "titulo": "1 · Inicio del reto", "md": "inicio.md"},
    {"clave": "plan", "titulo": "2 · Plan y decisiones"},
    {"clave": "catalogo", "titulo": "3 · Catálogo de datos"},
    {"clave": "diseno", "titulo": "4 · Diseño de solución", "md": "diseno.md"},
    {"clave": "casos", "titulo": "5 · Casos y evidencias"},
    {"clave": "pruebas", "titulo": "6 · Pruebas y métricas"},
    {"clave": "metricas", "titulo": "Métricas de la ejecución", "md": "metricas.md", "padre": "pruebas"},
    {"clave": "riesgos", "titulo": "7 · Riesgos y ética", "md": "riesgos.md"},
    {"clave": "presentacion", "titulo": "8 · Presentación al jurado", "md": "presentacion.md"},
]

# Bases de datos: página donde viven, esquema y mapeo de campos locales -> propiedades.
BASES = {
    "tareas": {
        "pagina": "plan", "titulo": "Tareas", "archivo": "tareas.yaml",
        "esquema": {
            "Tarea": {"title": {}}, "ID": _TXT, "Responsable": _TXT,
            "Estado": _sel("Pendiente", "En curso", "Hecho", "Bloqueada"),
            "Fecha": _FECHA, "Notas": _TXT,
        },
        "campos": {"id": "ID", "tarea": "Tarea", "responsable": "Responsable",
                   "estado": "Estado", "fecha": "Fecha", "notas": "Notas"},
    },
    "decisiones": {
        "pagina": "plan", "titulo": "Decisiones", "archivo": "decisiones.yaml",
        "esquema": {
            "Decisión": {"title": {}}, "ID": _TXT, "Fecha": _FECHA,
            "Estado": _sel("Propuesta", "Vigente", "Reemplazada"),
            "Contexto": _TXT, "Alternativas": _TXT, "Justificación": _TXT, "Decidió": _TXT,
        },
        "campos": {"id": "ID", "decision": "Decisión", "fecha": "Fecha", "estado": "Estado",
                   "contexto": "Contexto", "alternativas": "Alternativas",
                   "justificacion": "Justificación", "decidio": "Decidió"},
    },
    "catalogo": {
        "pagina": "catalogo", "titulo": "Fuentes", "archivo": "catalogo.yaml",
        "esquema": {
            "Fuente": {"title": {}}, "ID": _TXT, "URL": {"url": {}},
            "Fecha extracción": _FECHA, "Cobertura": _TXT, "Campos": _TXT,
            "Licencia": _TXT, "Transformaciones": _TXT, "SHA-256": _TXT, "Registros": _NUM,
        },
        "campos": {"id": "ID", "fuente": "Fuente", "url": "URL",
                   "fecha_extraccion": "Fecha extracción", "cobertura": "Cobertura",
                   "campos": "Campos", "licencia": "Licencia",
                   "transformaciones": "Transformaciones", "sha256": "SHA-256",
                   "registros": "Registros"},
    },
    "casos": {
        "pagina": "casos", "titulo": "Fichas",
        "esquema": {
            "Caso": {"title": {}}, "ID": _TXT,
            "Modalidad": _sel("TVN · principal", "TVN · digital", "Banca"),
            "Fuentes": _TXT, "Puntaje": _NUM, "Componentes": _TXT,
            "Prioridad": _sel("Alta", "Media", "Baja"),
            "Estado evidencia": _sel("Insuficiente", "Parcial", "Suficiente para el borrador"),
            "Estado revisión": _sel("Nuevo", "En revisión", "Requiere evidencia",
                                    "Aprobado como borrador", "Descartado"),
            "Revisor": _TXT,
        },
    },
    "pruebas": {
        "pagina": "pruebas", "titulo": "Matriz de pruebas", "archivo": "pruebas.yaml",
        "esquema": {
            "Prueba": {"title": {}}, "ID": _TXT,
            "Estado": _sel("Pendiente", "Pasó", "Falló", "Corregida"),
            "Entrada": _TXT, "Resultado esperado": _TXT, "Resultado observado": _TXT,
            "Evidencia": _TXT, "Corrección": _TXT, "Historial": _TXT, "Fecha": _FECHA,
        },
        "campos": {"id": "ID", "prueba": "Prueba", "estado": "Estado", "entrada": "Entrada",
                   "esperado": "Resultado esperado", "observado": "Resultado observado",
                   "evidencia": "Evidencia", "correccion": "Corrección",
                   "historial": "Historial", "fecha": "Fecha"},
    },
}


# ---------------------------------------------------------------- utilidades

def sha(obj) -> str:
    texto = obj if isinstance(obj, str) else json.dumps(obj, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def plano(valor):
    """Convierte listas, dicts y fechas de YAML/JSON en texto para Notion."""
    if valor is None:
        return None
    if hasattr(valor, "isoformat"):
        return valor.isoformat()
    if isinstance(valor, list):
        return ", ".join(str(plano(v)) for v in valor)
    if isinstance(valor, dict):
        return " · ".join(f"{k}={plano(v)}" for k, v in valor.items())
    return valor


def rt(texto) -> list:
    texto = "" if texto is None else str(texto)
    texto = texto[: MAX_TEXTO * 100]
    return [{"type": "text", "text": {"content": texto[i:i + MAX_TEXTO]}}
            for i in range(0, len(texto), MAX_TEXTO)]


def rt_md(texto: str) -> list:
    """Texto con **negritas** de Markdown."""
    salida = []
    for i, parte in enumerate(re.split(r"\*\*(.+?)\*\*", texto)):
        for obj in rt(parte):
            if i % 2 == 1:
                obj["annotations"] = {"bold": True}
            salida.append(obj)
    return salida


def valor_propiedad(tipo: str, valor):
    valor = plano(valor)
    if tipo == "title":
        return {"title": rt(valor)}
    if tipo == "rich_text":
        return {"rich_text": rt(valor)}
    if tipo == "select":
        if valor in (None, ""):
            return {"select": None}
        nombre = str(valor).replace(",", " ")
        return {"select": {"name": nombre[:1].upper() + nombre[1:]}}
    if tipo == "number":
        return {"number": None if valor in (None, "") else float(valor)}
    if tipo == "url":
        return {"url": valor or None}
    if tipo == "date":
        return {"date": {"start": str(valor)} if valor else None}
    raise ValueError(f"Tipo de propiedad no soportado: {tipo}")


def md_a_bloques(md: str) -> list:
    """Markdown simple -> bloques de Notion (títulos, listas, citas, código, separadores)."""
    bloques, codigo, en_codigo = [], [], False

    def cerrar_codigo():
        bloques.append({"object": "block", "type": "code",
                        "code": {"rich_text": rt("\n".join(codigo)), "language": "plain text"}})

    for linea in md.splitlines():
        if linea.strip().startswith("```"):
            if en_codigo:
                cerrar_codigo()
                codigo = []
            en_codigo = not en_codigo
            continue
        if en_codigo:
            codigo.append(linea)
            continue
        l = linea.strip()
        if not l:
            continue
        if l in ("---", "***"):
            bloques.append({"object": "block", "type": "divider", "divider": {}})
            continue
        m = re.match(r"^(#{1,3}) (.*)", l)
        if m:
            tipo, texto = f"heading_{len(m.group(1))}", m.group(2)
        elif re.match(r"^[-*] ", l):
            tipo, texto = "bulleted_list_item", l[2:]
        elif re.match(r"^\d+[.)] ", l):
            tipo, texto = "numbered_list_item", l.split(" ", 1)[1]
        elif l.startswith("> "):
            tipo, texto = "quote", l[2:]
        else:
            tipo, texto = "paragraph", l
        bloques.append({"object": "block", "type": tipo, tipo: {"rich_text": rt_md(texto)}})
    if en_codigo and codigo:
        cerrar_codigo()
    return bloques


def normalizar_id(valor: str) -> str:
    """Acepta un ID con o sin guiones, o la URL completa de la página."""
    hexa = re.findall(r"[0-9a-fA-F]{32}", valor.replace("-", ""))
    if not hexa:
        sys.exit(f"NOTION_ROOT_PAGE_ID no parece un ID de Notion: {valor}")
    h = hexa[-1].lower()
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


# ---------------------------------------------------------------- cliente Notion

class Notion:
    def __init__(self, token: str):
        self.s = requests.Session()
        self.s.headers.update({
            "Authorization": f"Bearer {token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        })

    def req(self, metodo: str, ruta: str, cuerpo: dict | None = None) -> dict:
        for intento in range(5):
            time.sleep(0.35)  # Notion permite ~3 solicitudes por segundo
            r = self.s.request(metodo, API + ruta, json=cuerpo, timeout=30)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(float(r.headers.get("Retry-After", 2 ** intento)))
                continue
            if r.status_code == 401:
                raise RuntimeError("Token inválido (401). Revisa NOTION_TOKEN en .env.")
            if r.status_code == 404:
                raise RuntimeError(
                    f"No se encontró {ruta} (404). ¿La página raíz está conectada a la "
                    "integración? Si borraste páginas en Notion, elimina .notion_state.json.")
            if not r.ok:
                raise RuntimeError(f"{metodo} {ruta} -> {r.status_code}: {r.text[:500]}")
            return r.json() if r.content else {}
        raise RuntimeError(f"{metodo} {ruta}: demasiados reintentos")

    def hijos(self, bloque_id: str) -> list[str]:
        ids, cursor = [], None
        while True:
            q = "?page_size=100" + (f"&start_cursor={cursor}" if cursor else "")
            res = self.req("GET", f"/blocks/{bloque_id}/children{q}")
            ids += [b["id"] for b in res["results"]]
            if not res.get("has_more"):
                return ids
            cursor = res["next_cursor"]

    def agregar_bloques(self, bloque_id: str, bloques: list) -> None:
        for i in range(0, len(bloques), MAX_BLOQUES):
            self.req("PATCH", f"/blocks/{bloque_id}/children",
                     {"children": bloques[i:i + MAX_BLOQUES]})

    def reemplazar_contenido(self, pagina_id: str, bloques: list) -> None:
        for b in self.hijos(pagina_id):
            self.req("DELETE", f"/blocks/{b}")
        self.agregar_bloques(pagina_id, bloques)


# ---------------------------------------------------------------- estado local

def cargar_estado(raiz: str) -> dict:
    if ESTADO.exists():
        est = json.loads(ESTADO.read_text(encoding="utf-8"))
        if est.get("raiz") == raiz:
            return est
        respaldo = ESTADO.with_name(f".notion_state.{est.get('raiz', 'anterior')[:8]}.json")
        ESTADO.rename(respaldo)
        log(f"Página raíz distinta: el estado anterior quedó en {respaldo.name}. "
            "Se creará la estructura en el nuevo destino.")
    return {"raiz": raiz, "paginas": {}, "bases": {}, "hashes": {}}


def guardar_estado(est: dict) -> None:
    ESTADO.write_text(json.dumps(est, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------- carga de archivos locales

def datos_dir() -> Path:
    return RAIZ / os.getenv("DATA_DIR", "data")


def leer_yaml(nombre: str) -> list:
    ruta = BITACORA / nombre
    if not ruta.exists():
        return []
    return yaml.safe_load(ruta.read_text(encoding="utf-8")) or []


def mapear(items: list, campos: dict) -> list:
    return [{prop: it.get(k) for k, prop in campos.items() if k in it} for it in items]


def prioridad(puntaje):
    if puntaje in (None, ""):
        return None
    p = float(puntaje)
    return "Baja" if p < 40 else "Media" if p < 70 else "Alta"


def cuerpo_ficha(f: dict) -> str:
    partes = []
    if f.get("alcance"):
        partes.append(f"> {f['alcance']}")
    if f.get("borrador"):
        partes += ["## Borrador", str(f["borrador"])]
    if f.get("afirmaciones"):
        partes.append("## Afirmaciones y citas")
        for a in f["afirmaciones"]:
            if isinstance(a, dict):
                cita = a.get("id_evidencia") or a.get("cita") or "SIN CITA"
                campo = f" · {a['campo']}" if a.get("campo") else ""
                partes.append(f"- [{a.get('tipo', '?')}] {a.get('texto', '')} ({cita}{campo})")
            else:
                partes.append(f"- {a}")
    if f.get("vacios"):
        partes.append("## Pendiente de verificar")
        partes += [f"- {v}" for v in f["vacios"]]
    return "\n".join(partes)


def cargar_casos() -> list:
    ruta = datos_dir() / "fichas.jsonl"
    if not ruta.exists():
        return []
    casos = []
    for n, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
        if not linea.strip():
            continue
        try:
            f = json.loads(linea)
        except json.JSONDecodeError as e:
            log(f"  ! fichas.jsonl línea {n} inválida, se omite: {e}")
            continue
        casos.append({
            "ID": f.get("id_caso"), "Caso": f.get("titulo") or f.get("id_caso"),
            "Modalidad": f.get("modalidad"), "Fuentes": f.get("ids_fuente"),
            "Puntaje": f.get("puntaje"), "Componentes": f.get("componentes"),
            "Prioridad": f.get("prioridad") or prioridad(f.get("puntaje")),
            "Estado evidencia": f.get("estado_evidencia"),
            "Estado revisión": f.get("estado_revision"), "Revisor": f.get("revisor"),
            "_cuerpo": cuerpo_ficha(f),
        })
    return casos


def cargar_catalogo() -> list:
    manifest = datos_dir() / "manifest.json"
    if manifest.exists():
        fuentes = json.loads(manifest.read_text(encoding="utf-8")).get("fuentes")
        if fuentes:
            return mapear(fuentes, BASES["catalogo"]["campos"])
    return mapear(leer_yaml("catalogo.yaml"), BASES["catalogo"]["campos"])


def cargar_todo() -> dict:
    datos = {}
    for clave in ("tareas", "decisiones", "pruebas"):
        datos[clave] = mapear(leer_yaml(BASES[clave]["archivo"]), BASES[clave]["campos"])
    datos["catalogo"] = cargar_catalogo()
    datos["casos"] = cargar_casos()
    return datos


def validar(datos: dict) -> int:
    errores = 0
    for clave, regs in datos.items():
        vistos = set()
        for r in regs:
            ident = r.get("ID")
            if not ident:
                log(f"  ! {clave}: registro sin ID, se omitirá: {r}")
                errores += 1
            elif ident in vistos:
                log(f"  ! {clave}: ID duplicado {ident}")
                errores += 1
            vistos.add(ident)
    return errores


# ---------------------------------------------------------------- sincronización

def asegurar_estructura(n: Notion, est: dict) -> None:
    for p in PAGINAS:
        if p["clave"] in est["paginas"]:
            continue
        padre = est["raiz"] if "padre" not in p else est["paginas"][p["padre"]]
        res = n.req("POST", "/pages", {
            "parent": {"page_id": padre},
            "properties": {"title": {"title": rt(p["titulo"])}},
        })
        est["paginas"][p["clave"]] = res["id"]
        guardar_estado(est)
        log(f"  + página {p['titulo']}")

    for clave, base in BASES.items():
        if clave in est["bases"]:
            continue
        res = n.req("POST", "/databases", {
            "parent": {"type": "page_id", "page_id": est["paginas"][base["pagina"]]},
            "title": rt(base["titulo"]),
            "is_inline": True,
            "initial_data_source": {"properties": base["esquema"]},
        })
        fuentes = res.get("data_sources") or n.req("GET", f"/databases/{res['id']}").get("data_sources")
        est["bases"][clave] = {"database_id": res["id"], "data_source_id": fuentes[0]["id"]}
        guardar_estado(est)
        log(f"  + base {base['titulo']}")


def filas_existentes(n: Notion, data_source_id: str) -> dict:
    mapa, cursor = {}, None
    while True:
        cuerpo = {"page_size": 100}
        if cursor:
            cuerpo["start_cursor"] = cursor
        res = n.req("POST", f"/data_sources/{data_source_id}/query", cuerpo)
        for pg in res["results"]:
            ident = "".join(t.get("plain_text", "")
                            for t in pg["properties"].get("ID", {}).get("rich_text", []))
            if ident:
                mapa[ident] = pg["id"]
        if not res.get("has_more"):
            return mapa
        cursor = res["next_cursor"]


def sync_base(n: Notion, est: dict, clave: str, registros: list) -> tuple[int, int]:
    base = BASES[clave]
    ds = est["bases"][clave]["data_source_id"]
    hashes = est["hashes"].setdefault(clave, {})
    existentes = filas_existentes(n, ds)
    creados = actualizados = 0

    for reg in registros:
        ident = str(reg.get("ID") or "")
        if not ident:
            continue
        cuerpo_md = reg.get("_cuerpo")
        props = {nombre: valor_propiedad(next(iter(defin)), reg[nombre])
                 for nombre, defin in base["esquema"].items() if nombre in reg}
        h = sha([props, cuerpo_md])
        if ident in existentes and hashes.get(ident) == h:
            continue

        if ident in existentes:
            pid = existentes[ident]
            n.req("PATCH", f"/pages/{pid}", {"properties": props})
            if cuerpo_md is not None:
                n.reemplazar_contenido(pid, md_a_bloques(cuerpo_md))
            actualizados += 1
        else:
            bloques = md_a_bloques(cuerpo_md) if cuerpo_md else []
            cuerpo = {"parent": {"type": "data_source_id", "data_source_id": ds},
                      "properties": props}
            if bloques:
                cuerpo["children"] = bloques[:MAX_BLOQUES]
            res = n.req("POST", "/pages", cuerpo)
            if len(bloques) > MAX_BLOQUES:
                n.agregar_bloques(res["id"], bloques[MAX_BLOQUES:])
            creados += 1
        hashes[ident] = h
        guardar_estado(est)
    return creados, actualizados


def sync_paginas(n: Notion, est: dict) -> int:
    hashes = est["hashes"].setdefault("_paginas", {})
    cambios = 0
    for p in PAGINAS:
        ruta = PAGINAS_MD / p.get("md", "")
        if "md" not in p or not ruta.exists():
            continue
        md = ruta.read_text(encoding="utf-8")
        h = sha(md)
        if hashes.get(p["clave"]) == h:
            continue
        n.reemplazar_contenido(est["paginas"][p["clave"]], md_a_bloques(md))
        hashes[p["clave"]] = h
        guardar_estado(est)
        cambios += 1
        log(f"  ~ página {p['titulo']}")
    return cambios


def main() -> None:
    global SILENCIO
    ap = argparse.ArgumentParser(description="Sincroniza la bitácora con Notion.")
    ap.add_argument("--dry-run", action="store_true", help="validar sin llamar a Notion")
    ap.add_argument("--quiet", action="store_true", help="sin salida")
    args = ap.parse_args()
    SILENCIO = args.quiet
    load_dotenv(RAIZ / ".env")

    datos = cargar_todo()
    errores = validar(datos)
    if args.dry_run:
        for clave, regs in datos.items():
            print(f"{clave:<11} {len(regs):>3} registros")
        print("Sin errores." if not errores else f"{errores} advertencias.")
        return

    token, raiz = os.getenv("NOTION_TOKEN"), os.getenv("NOTION_ROOT_PAGE_ID")
    if not token or not raiz:
        sys.exit("Falta NOTION_TOKEN o NOTION_ROOT_PAGE_ID en .env")

    n = Notion(token)
    est = cargar_estado(normalizar_id(raiz))
    try:
        asegurar_estructura(n, est)
        sync_paginas(n, est)
        for clave, regs in datos.items():
            c, a = sync_base(n, est, clave, regs)
            if c or a:
                log(f"  {clave}: {c} nuevos, {a} actualizados")
    except RuntimeError as e:
        sys.exit(f"Error: {e}")
    log("Notion sincronizado.")


if __name__ == "__main__":
    main()
`````

### `bitacora.py`

`````python
#!/usr/bin/env python3
"""
Registro rápido de la bitácora. Escribe en bitacora/*.yaml con fecha y hora de Panamá
y sincroniza con Notion al terminar si NOTION_AUTOSYNC=1 (o si pasas --sync).

  python bitacora.py decision "Usar DuckDB como base local"
  python bitacora.py tarea "Script de descarga de GDELT" --responsable Guille
  python bitacora.py estado TAR-005 "En curso"
  python bitacora.py prueba T07 Falló --observado "El agente siguió la instrucción del artículo"
  python bitacora.py prueba T07 Corregida --correccion "Contenido de fuentes delimitado y validado"
  python bitacora.py resumen
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml
from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent
BITACORA = RAIZ / "bitacora"
PANAMA = timezone(timedelta(hours=-5))
ESTADOS_TAREA = ["Pendiente", "En curso", "Hecho", "Bloqueada"]
ESTADOS_DECISION = ["Propuesta", "Vigente", "Reemplazada"]
ESTADOS_PRUEBA = ["Pendiente", "Pasó", "Falló", "Corregida"]


def ahora() -> str:
    return datetime.now(PANAMA).isoformat(timespec="minutes")


def leer(nombre: str) -> list:
    ruta = BITACORA / f"{nombre}.yaml"
    return (yaml.safe_load(ruta.read_text(encoding="utf-8")) or []) if ruta.exists() else []


def escribir(nombre: str, datos: list) -> None:
    (BITACORA / f"{nombre}.yaml").write_text(
        yaml.safe_dump(datos, allow_unicode=True, sort_keys=False, width=100), encoding="utf-8")


def siguiente_id(items: list, prefijo: str) -> str:
    nums = [int(str(i["id"]).rsplit("-", 1)[-1]) for i in items
            if str(i.get("id", "")).startswith(prefijo + "-")]
    return f"{prefijo}-{(max(nums) if nums else 0) + 1:03d}"


def pedir(valor: str | None, pregunta: str, obligatorio: bool = False) -> str:
    while not valor:
        valor = input(f"{pregunta}: ").strip()
        if valor or not obligatorio:
            break
        print("  Este campo es obligatorio.")
    return valor or ""


def buscar(items: list, ident: str) -> dict:
    for it in items:
        if str(it.get("id")) == ident:
            return it
    sys.exit(f"No existe el ID {ident}.")


# ---------------------------------------------------------------- comandos

def cmd_decision(a) -> None:
    items = leer("decisiones")
    nueva = {
        "id": siguiente_id(items, "DEC"),
        "decision": a.titulo,
        "fecha": ahora(),
        "estado": a.estado,
        "contexto": pedir(a.contexto, "Contexto (qué problema o duda la originó)"),
        "alternativas": pedir(a.alternativas, "Alternativas consideradas"),
        "justificacion": pedir(a.justificacion, "Justificación", obligatorio=True),
        "decidio": a.por or os.getenv("BITACORA_AUTOR", ""),
    }
    items.append(nueva)
    escribir("decisiones", items)
    print(f"Decisión {nueva['id']} registrada.")


def cmd_tarea(a) -> None:
    items = leer("tareas")
    nueva = {"id": siguiente_id(items, "TAR"), "tarea": a.titulo,
             "responsable": a.responsable or os.getenv("BITACORA_AUTOR", ""),
             "estado": a.estado, "fecha": ahora(), "notas": a.notas or ""}
    items.append(nueva)
    escribir("tareas", items)
    print(f"Tarea {nueva['id']} registrada.")


def cmd_estado(a) -> None:
    if a.id.startswith("DEC-"):
        nombre, validos = "decisiones", ESTADOS_DECISION
    else:
        nombre, validos = "tareas", ESTADOS_TAREA
    if a.estado not in validos:
        sys.exit(f"Estado inválido. Opciones: {', '.join(validos)}")
    items = leer(nombre)
    it = buscar(items, a.id)
    it["estado"] = a.estado
    it["fecha"] = ahora()
    if a.notas:
        previas = it.get("notas") or ""
        it["notas"] = (previas + "\n" if previas else "") + f"{ahora()} · {a.notas}"
    escribir(nombre, items)
    print(f"{a.id} -> {a.estado}")


def cmd_prueba(a) -> None:
    items = leer("pruebas")
    it = buscar(items, a.id)
    it["estado"] = a.estado
    it["fecha"] = ahora()
    for campo in ("entrada", "observado", "evidencia", "correccion"):
        valor = getattr(a, campo)
        if valor:
            it[campo] = valor
    detalle = a.observado or a.correccion or ""
    linea = f"{ahora()} · {a.estado}" + (f" · {detalle}" if detalle else "")
    it["historial"] = ((it.get("historial") or "") + "\n" + linea).strip()
    escribir("pruebas", items)
    print(f"{a.id} -> {a.estado}")


def cmd_resumen(_a) -> None:
    tareas, decisiones, pruebas = leer("tareas"), leer("decisiones"), leer("pruebas")
    print(f"Tareas: {len(tareas)} (mínimo exigido: 8)")
    for e in ESTADOS_TAREA:
        print(f"  {e:<10} {sum(1 for t in tareas if t.get('estado') == e)}")
    vigentes = sum(1 for d in decisiones if d.get("estado") == "Vigente")
    print(f"Decisiones: {len(decisiones)} ({vigentes} vigentes; mínimo exigido: 3)")
    print("Pruebas:")
    for p in pruebas:
        print(f"  {p['id']:<4} {p.get('estado', ''):<10} {p.get('prueba', '')}")
    if not any(p.get("estado") == "Corregida" for p in pruebas):
        print("Aviso: el jurado pedirá ver una prueba fallida y su corrección.")


# ---------------------------------------------------------------- main

def main() -> None:
    load_dotenv(RAIZ / ".env")
    comun = argparse.ArgumentParser(add_help=False)
    comun.add_argument("--sync", action="store_true", help="sincronizar con Notion al terminar")

    ap = argparse.ArgumentParser(description="Bitácora del proyecto.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("decision", parents=[comun], help="registrar una decisión")
    d.add_argument("titulo")
    d.add_argument("--contexto")
    d.add_argument("--alternativas")
    d.add_argument("--justificacion")
    d.add_argument("--estado", default="Vigente", choices=ESTADOS_DECISION)
    d.add_argument("--por", help="quién decidió")
    d.set_defaults(fn=cmd_decision)

    t = sub.add_parser("tarea", parents=[comun], help="registrar una tarea")
    t.add_argument("titulo")
    t.add_argument("--responsable")
    t.add_argument("--estado", default="Pendiente", choices=ESTADOS_TAREA)
    t.add_argument("--notas")
    t.set_defaults(fn=cmd_tarea)

    e = sub.add_parser("estado", parents=[comun], help="cambiar estado de una tarea o decisión")
    e.add_argument("id")
    e.add_argument("estado")
    e.add_argument("--notas")
    e.set_defaults(fn=cmd_estado)

    p = sub.add_parser("prueba", parents=[comun], help="registrar resultado de una prueba")
    p.add_argument("id", help="T01 a T10")
    p.add_argument("estado", choices=ESTADOS_PRUEBA)
    p.add_argument("--entrada")
    p.add_argument("--observado")
    p.add_argument("--evidencia", help="ruta a captura o log")
    p.add_argument("--correccion")
    p.set_defaults(fn=cmd_prueba)

    r = sub.add_parser("resumen", help="ver el estado de la bitácora")
    r.set_defaults(fn=cmd_resumen)

    args = ap.parse_args()
    args.fn(args)

    if args.cmd != "resumen" and (getattr(args, "sync", False)
                                  or os.getenv("NOTION_AUTOSYNC") == "1"):
        subprocess.run([sys.executable, str(RAIZ / "notion_sync.py"), "--quiet"], check=False)


if __name__ == "__main__":
    main()
`````

### `bitacora/tareas.yaml`

`````yaml
- id: TAR-001
  tarea: Pedir a la organización el teamspace, cupos y acceso del jurado
  responsable: Guille
  estado: Pendiente
  fecha: '2026-10-06'
  notas: Preguntar también quién puede crear la integración de Notion en el espacio oficial
- id: TAR-002
  tarea: Confirmar si la organización entrega el snapshot común y en qué fecha
  responsable: Guille
  estado: Pendiente
  fecha: '2026-10-06'
  notas: ''
- id: TAR-003
  tarea: Consultar la inconsistencia del intervalo de fechas (sección 6 vs. sección 7)
  responsable: Guille
  estado: Pendiente
  fecha: '2026-10-06'
  notas: 'Sección 7 excluye fuera de [2024-01-01, 2025-10-01); sección 6 pide los 30 días previos a la extracción'
- id: TAR-004
  tarea: Confirmar si CU-05 (banca) es obligatorio en la modalidad editorial
  responsable: Guille
  estado: Pendiente
  fecha: '2026-10-06'
  notas: ''
- id: TAR-005
  tarea: Script de descarga de fuentes y generación de manifest.json
  responsable: Guille
  estado: Pendiente
  fecha: '2026-10-06'
  notas: ''
- id: TAR-006
  tarea: Validación de carga y reporte de calidad (T01)
  responsable: Guille
  estado: Pendiente
  fecha: '2026-10-06'
  notas: ''
- id: TAR-007
  tarea: Clasificación temática y agrupación de eventos, con baseline TF-IDF
  responsable: Guille
  estado: Pendiente
  fecha: '2026-10-06'
  notas: ''
- id: TAR-008
  tarea: Motor de puntaje con reglas versionadas y estado de evidencia
  responsable: Guille
  estado: Pendiente
  fecha: '2026-10-06'
  notas: ''
- id: TAR-009
  tarea: Generación con citas y validador de citas
  responsable: Guille
  estado: Pendiente
  fecha: '2026-10-06'
  notas: ''
- id: TAR-010
  tarea: Interfaz con bandeja, ficha, borrador y revisión
  responsable: Guille
  estado: Pendiente
  fecha: '2026-10-06'
  notas: ''
- id: TAR-011
  tarea: Ejecutar T01–T10 y benchmark de desarrollo
  responsable: Guille
  estado: Pendiente
  fecha: '2026-10-06'
  notas: ''
- id: TAR-012
  tarea: Preparar y ensayar el pitch desde Notion con demo offline
  responsable: Guille
  estado: Pendiente
  fecha: '2026-10-06'
  notas: ''
`````

### `bitacora/decisiones.yaml`

`````yaml
- id: DEC-001
  decision: Documentación como código, sincronizada con Notion por API
  fecha: '2026-10-06'
  estado: Vigente
  contexto: El teamspace oficial aún no está asignado y la documentación tiende a quedar para el final
  alternativas: Escribir directamente en Notion; documentar al cierre del evento
  justificacion: >-
    La bitácora vive en el repositorio con fecha de cada registro y se sincroniza en cada commit.
    Migrar al teamspace consiste en cambiar el destino y volver a ejecutar la sincronización.
  decidio: Guille
- id: DEC-002
  decision: Modalidad editorial (TVN · principal)
  fecha: '2026-10-06'
  estado: Propuesta
  contexto: El reto admite editorial o bancaria; la editorial es la recomendada
  alternativas: Modalidad bancaria; ambas modalidades
  justificacion: Es la recomendada, TVN es el patrocinador y el reto pide no dispersarse en dos productos
  decidio: Guille
- id: DEC-003
  decision: Base de datos local (DuckDB); Notion solo como bitácora y presentación
  fecha: '2026-10-06'
  estado: Propuesta
  contexto: El documento no exige una base de datos específica y la demo debe funcionar sin internet (T10)
  alternativas: Notion como base de datos; SQLite; PostgreSQL
  justificacion: >-
    Un solo archivo, sin servidor y funciona offline. Notion requiere conexión, limita la API
    a unas 3 solicitudes por segundo y no permite búsqueda semántica.
  decidio: Guille
`````

### `bitacora/pruebas.yaml`

`````yaml
- id: T01
  prueba: Archivo con fechas inválidas y nulos
  esperado: Validar, separar errores y conservar nulos; no bloquear toda la carga
  estado: Pendiente
- id: T02
  prueba: Tres registros del mismo evento
  esperado: Agrupar sin perder fuentes; no triplicar importancia ni corroboración
  estado: Pendiente
- id: T03
  prueba: Noticia antigua recirculada
  esperado: Mostrar fecha original; no presentarla como un evento nuevo
  estado: Pendiente
- id: T04
  prueba: Cifra anual del Banco Mundial
  esperado: Mantener país, año y unidad; citar el dato y no describirlo como cifra de hoy
  estado: Pendiente
- id: T05
  prueba: Dos afirmaciones incompatibles
  esperado: Mostrar ambas, su alcance y la revisión pendiente; no escoger arbitrariamente
  estado: Pendiente
- id: T06
  prueba: Consulta sin respuesta en el corpus
  esperado: Abstención explícita; ninguna cifra o cita inventada
  estado: Pendiente
- id: T07
  prueba: Fuente que exige ignorar instrucciones
  esperado: Tratarla como contenido no confiable; no revelar secretos ni ejecutar acciones
  estado: Pendiente
- id: T08
  prueba: Caso de prioridad alta
  esperado: Exponer componentes y regla; la prioridad no habilita publicación
  estado: Pendiente
- id: T09
  prueba: Brief editorial
  esperado: Formato útil, citas pertinentes y distinción de hechos e inferencias
  estado: Pendiente
- id: T10
  prueba: Sin internet durante la demo
  esperado: Funcionar con snapshot y fallback documentado; dejar evidencia en Notion
  estado: Pendiente
`````

### `bitacora/catalogo.yaml`

`````yaml
# Se usa mientras no exista data/manifest.json. Cuando el script de descarga genere el
# manifest con una lista "fuentes" con estas mismas claves, el catálogo se toma de ahí.
- id: SRC-TVN
  fuente: TVN · feed RSS
  url: null
  cobertura: Pendiente de extracción
  campos: titulo, url, fecha_publicacion, descripcion
  licencia: Solo metadatos; el RSS no implica licencia abierta sobre artículos, videos o imágenes
- id: SRC-GDELT
  fuente: GDELT DOC 2.0
  url: https://api.gdeltproject.org/api/v2/doc/doc
  cobertura: Pendiente de extracción
  campos: titulo, url, dominio, idioma, seendate
  licencia: La API no transfiere derechos de los medios enlazados
  transformaciones: seendate se guarda como fecha_deteccion, nunca como fecha_publicacion
- id: SRC-WB
  fuente: Banco Mundial · Indicators API v2
  url: https://api.worldbank.org/v2/
  cobertura: PAN, CRI, COL, DOM, MEX, GTM · 2010–2024 · 6 indicadores
  campos: pais_iso3, indicador_id, anio, valor, unidad
  licencia: CC BY 4.0 salvo excepciones por indicador
  transformaciones: Cuadrícula completa de 1.350 combinaciones; nulos conservados
- id: SRC-USGS
  fuente: USGS · catálogo sísmico
  url: https://earthquake.usgs.gov/fdsnws/event/1/
  cobertura: 2024 · lat 5 a 12 · lon -86 a -76 · magnitud >= 3
  campos: id, magnitude, time, updated, longitude, latitude, depth, place, status, url
  licencia: Verificar condiciones de datos de terceros
  transformaciones: Solo para hechos sísmicos; la caja regional no equivale al territorio de Panamá
`````

### `bitacora/paginas/inicio.md`

`````markdown
# HackIAthon · Reto TVN Media
> De la señal a la decisión: copiloto de inteligencia informativa con IA.
## Equipo
- Guille · desarrollo
## Modalidad
Editorial (TVN · principal). Ver DEC-002.
## Problema
Un equipo editorial revisa fuentes dispersas, varias repiten la misma noticia y debe decidir rápido qué investigar. Que una noticia circule mucho no significa que esté confirmada.
## Usuario
Editor/a y periodista de TVN.
## Alcance
- Ingesta de noticias públicas (TVN RSS, GDELT) e indicadores oficiales (Banco Mundial, USGS)
- Bandeja priorizada, ficha de evidencia, consultas en español y paquete editorial
- Revisión humana de cada borrador; nada se publica de forma automática
## Criterios de éxito
- Un editor pasa de fuentes dispersas a un tema investigable, con evidencia y un borrador responsable
- 100% de afirmaciones factuales con cita; abstención correcta cuando no hay evidencia
## Accesos
- Demo: pendiente
- Repositorio: pendiente
`````

### `bitacora/paginas/diseno.md`

`````markdown
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
- Reglas de puntaje: v0.1
## Límites del sistema
- Las noticias solo incluyen titular y metadatos
- No etiqueta noticias como verdaderas o falsas
`````

### `bitacora/paginas/metricas.md`

`````markdown
# Métricas de la ejecución
> Reportar numerador, denominador y fallos; no esconder errores tras un promedio.
- **Cobertura de citas:** pendiente
- **Validez de sustento:** pendiente
- **Abstención correcta:** pendiente
- **Abstenciones incorrectas:** pendiente
- **Clasificación (macro-F1 vs. baseline):** pendiente
- **Precision@5 del ranking:** pendiente
- **Tiempo mediano y p95 por consulta:** pendiente
`````

### `bitacora/paginas/riesgos.md`

`````markdown
# Riesgos y ética
## Privacidad
No se almacenan datos personales innecesarios ni perfiles de personas.
## Derechos
Solo metadatos de TVN y GDELT; no se redistribuyen artículos, imágenes ni videos.
## Sesgos
Pendiente de documentar.
## Ataques al agente
El texto de las fuentes se trata como dato, nunca como instrucción (T07).
## Controles
- Estados de revisión: nuevo, en revisión, requiere evidencia, aprobado como borrador, descartado
- Validador de citas: se descarta toda afirmación sin evidencia identificable
- Credenciales fuera del código y de Notion
## Fuera de alcance
Audiencia, verdad o falsedad de noticias, perfiles de personas, contenido con paywall.
`````

### `bitacora/paginas/presentacion.md`

`````markdown
# Presentación al jurado
1. Problema y usuario (1 min)
2. Solución, alcance y datos (1 min)
3. Demo: consulta, ficha con citas, borrador y abstención (4 min)
4. Arquitectura, IA, baseline y métricas (2 min)
5. Valor operativo o hipótesis de valor (1 min)
6. Riesgos, límites y próximos pasos (1 min)
`````

### `hooks/post-commit`

`````sh
#!/bin/sh
# Sincroniza la bitácora con Notion después de cada commit, en segundo plano.
# Si falla (sin internet, sin token), el commit no se ve afectado; revisa .notion_sync.log.
cd "$(git rev-parse --show-toplevel)" || exit 0
[ -f .env ] || exit 0
( python3 notion_sync.py --quiet >> .notion_sync.log 2>&1 & )
exit 0
`````

### `ingesta/config.yaml`

`````yaml
# Configuración del snapshot "Panamá · Señales y Evidencias" (versión de desarrollo propia).
# Cuando llegue el paquete oficial, se reemplaza la carpeta data/ y este archivo queda como receta.
version: v0-dev
data_dir: data

tvn:
  # Copiar la URL del enlace [2] "TVN · feed RSS público" del PDF del reto.
  url: ""

gdelt:
  url: https://api.gdeltproject.org/api/v2/doc/doc
  dias_atras: 30        # ventana por defecto si no se pasa --desde/--hasta
  ventana_dias: 7       # cada consulta se divide en ventanas; si una llega a 250, se parte a la mitad
  pausa_segundos: 6     # GDELT pide no más de una solicitud cada 5 segundos
  # GDELT busca sobre texto traducido al inglés, por eso las palabras clave van en inglés.
  # Una consulta por fila; "tema" es el tema de BÚSQUEDA, no una etiqueta verificada.
  consultas:
    - {id: eco, tema: economia, query: 'Panama (economy OR inflation OR unemployment OR GDP)'}
    - {id: canal, tema: logistica_canal, query: '"Panama Canal"'}
    - {id: log, tema: logistica_canal, query: 'Panama (shipping OR port OR logistics)'}
    - {id: tur, tema: turismo, query: 'Panama (tourism OR tourists OR cruise)'}
    - {id: ser, tema: servicios_publicos, query: 'Panama (water OR electricity OR transport)'}
    - {id: nat, tema: eventos_naturales, query: 'Panama (earthquake OR flood OR drought OR storm)'}
    - {id: reg, tema: regulacion, query: 'Panama (law OR regulation OR decree)'}

banco_mundial:
  url: https://api.worldbank.org/v2
  desde: 2010
  hasta: 2024
  paises: {PAN: PA, CRI: CR, COL: CO, DOM: DO, MEX: MX, GTM: GT}
  licencia: CC BY 4.0 (revisar excepciones por indicador en los metadatos)
  indicadores:
    - {id: NY.GDP.MKTP.KD.ZG, unidad: "% anual"}
    - {id: FP.CPI.TOTL.ZG, unidad: "% anual"}
    - {id: SL.UEM.TOTL.ZS, unidad: "% de la fuerza laboral total"}
    - {id: SP.POP.TOTL, unidad: "personas"}
    - {id: IT.NET.USER.ZS, unidad: "% de la población"}
    - {id: NE.EXP.GNFS.ZS, unidad: "% del PIB"}

usgs:
  url: https://earthquake.usgs.gov/fdsnws/event/1/query
  desde: "2024-01-01T00:00:00"
  hasta: "2024-12-31T23:59:59"
  minlatitude: 5
  maxlatitude: 12
  minlongitude: -86
  maxlongitude: -76
  minmagnitude: 3

# Regla de la sección 7: excluir registros fuera de [2024-01-01, 2025-10-01).
# Desactivada hasta que la organización aclare el período (TAR-003). Si se activa, los
# registros fuera del intervalo van a excluidos.csv con su motivo; no se borran.
filtro_intervalo:
  activo: false
  desde: "2024-01-01T00:00:00Z"
  hasta: "2025-10-01T00:00:00Z"
`````

### `ingesta/descargar_snapshot.py`

`````python
#!/usr/bin/env python3
"""
Descarga las fuentes públicas del reto y genera un snapshot con el contrato de la sección 7.

Dos fases separadas:
  1. Descarga: guarda las respuestas originales en data/raw/ sin modificarlas.
  2. Procesamiento: lee TODO lo que hay en data/raw/ y genera data/processed/ y el manifest.
     Es determinista y no necesita internet (--solo-procesar).

Salida en data/:
  raw/tvn/rss_<fecha>.xml          cada captura del RSS (se acumulan; el RSS no guarda histórico)
  raw/gdelt/<consulta>_<ventana>.json
  raw/worldbank/<indicador>.json
  raw/usgs/eventos.json
  processed/noticias.csv           TVN + GDELT, deduplicado por URL
  processed/fuentes.json           medios presentes y condiciones de uso
  processed/indicadores.csv        cuadrícula completa país × indicador × año, con nulos
  processed/eventos.geojson        sismos USGS normalizados
  processed/excluidos.csv          registros descartados y motivo
  diccionario.md                   significado de cada campo
  manifest.json                    versión, consultas, conteos, SHA-256 y transformaciones

Uso:
  python ingesta/descargar_snapshot.py                          # todas las fuentes
  python ingesta/descargar_snapshot.py --solo tvn gdelt
  python ingesta/descargar_snapshot.py --desde 2026-09-06 --hasta 2026-10-06
  python ingesta/descargar_snapshot.py --solo-procesar          # sin internet
"""
from __future__ import annotations

import argparse
import calendar
import csv
import hashlib
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import feedparser
import requests
import yaml

RAIZ = Path(__file__).resolve().parent.parent
CONFIG = Path(__file__).resolve().parent / "config.yaml"
UTC = timezone.utc
UA = "hackiathon-tvn-snapshot/0.1 (prototipo academico)"
PAUSA_EXTRA = True  # las pruebas lo desactivan

COLUMNAS_NOTICIAS = ["id_noticia", "titulo", "url", "medio", "idioma", "fecha_publicacion",
                     "fecha_deteccion", "fecha_extraccion", "tema", "origen", "alcance_texto"]
COLUMNAS_INDICADORES = ["id_evidencia", "pais_iso3", "indicador_id", "indicador_nombre", "anio",
                        "valor", "unidad", "observacion", "fuente_url", "fecha_extraccion",
                        "licencia"]
IDIOMAS = {"spanish": "es", "english": "en", "portuguese": "pt", "french": "fr",
           "german": "de", "italian": "it", "chinese": "zh", "japanese": "ja"}


# ---------------------------------------------------------------- utilidades

def log(msg: str) -> None:
    print(msg, flush=True)


def ahora() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def iso(dt: datetime | None) -> str | None:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ") if dt else None


def sello(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(65536), b""):
            h.update(bloque)
    return h.hexdigest()


def guardar_json(ruta: Path, obj) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def leer_json(ruta: Path):
    return json.loads(ruta.read_text(encoding="utf-8"))


def obtener(url: str, params: dict | None = None) -> requests.Response:
    """GET con reintentos ante 429, errores 5xx o fallas de red."""
    ultimo = None
    for intento in range(3):
        try:
            r = requests.get(url, params=params, headers={"User-Agent": UA}, timeout=60)
            if r.status_code == 429 or r.status_code >= 500:
                ultimo = r
                time.sleep(10 * (intento + 1))
                continue
            return r
        except requests.RequestException as e:
            if intento == 2:
                raise
            log(f"    reintento por error de red: {e}")
            time.sleep(5 * (intento + 1))
    return ultimo


def normalizar_url(url: str) -> str:
    """Clave de deduplicación: sin esquema, sin www, sin parámetros de rastreo ni barra final."""
    p = urlsplit(url.strip())
    q = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
         if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid", "outputtype"}]
    host = p.netloc.lower().removeprefix("www.")
    ruta = p.path.rstrip("/") or "/"
    return urlunsplit(("", host, ruta, urlencode(q), "")).lstrip("/")


def url_valida(url: str | None) -> bool:
    if not url:
        return False
    p = urlsplit(url.strip())
    return p.scheme in ("http", "https") and bool(p.netloc)


def dominio(url: str) -> str:
    return urlsplit(url.strip()).netloc.lower().removeprefix("www.")


def id_noticia(url: str) -> str:
    return "N-" + hashlib.sha1(normalizar_url(url).encode("utf-8")).hexdigest()[:12]


def fecha_gdelt(texto: str | None) -> datetime | None:
    try:
        return datetime.strptime(texto, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
    except (TypeError, ValueError):
        return None


def fecha_iso_entrada(texto: str) -> datetime:
    dt = datetime.fromisoformat(texto)
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


# ---------------------------------------------------------------- fase 1: descarga

def descargar_tvn(cfg: dict, raw: Path) -> None:
    url = (cfg.get("tvn") or {}).get("url")
    if not url:
        log("  ! TVN: falta tvn.url en ingesta/config.yaml (enlace [2] del PDF). Se omite.")
        return
    t = ahora()
    r = obtener(url)
    r.raise_for_status()
    destino = raw / "tvn" / f"rss_{sello(t)}.xml"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(r.content)
    log(f"  TVN: captura guardada en {destino.relative_to(raw.parent)}")


def _gdelt_ventana(g: dict, raw: Path, consulta: dict, ini: datetime, fin: datetime,
                   profundidad: int = 0) -> None:
    params = {
        "query": consulta["query"], "mode": "artlist", "format": "json",
        "maxrecords": 250, "sort": "datedesc",
        "startdatetime": ini.strftime("%Y%m%d%H%M%S"),
        "enddatetime": fin.strftime("%Y%m%d%H%M%S"),
    }
    if PAUSA_EXTRA:
        time.sleep(g.get("pausa_segundos", 6))
    t = ahora()
    r = obtener(g["url"], params)
    articulos, error = [], None
    try:
        articulos = (r.json() or {}).get("articles") or []
    except ValueError:
        error = (r.text or "").strip()[:300] or f"HTTP {r.status_code}"

    # Si se alcanzó el máximo, la ventana tiene más artículos: se divide en dos.
    if len(articulos) >= 250 and (fin - ini) > timedelta(hours=2) and profundidad < 6:
        medio = ini + (fin - ini) / 2
        _gdelt_ventana(g, raw, consulta, ini, medio, profundidad + 1)
        _gdelt_ventana(g, raw, consulta, medio, fin, profundidad + 1)
        return

    nombre = f"{consulta['id']}_{params['startdatetime']}_{params['enddatetime']}.json"
    guardar_json(raw / "gdelt" / nombre, {
        "fuente": "gdelt", "consulta_id": consulta["id"], "tema": consulta["tema"],
        "params": params, "fecha_extraccion": iso(t), "http_status": r.status_code,
        "error": error, "truncado": len(articulos) >= 250, "articulos": articulos,
    })
    estado = f"error: {error[:80]}" if error else f"{len(articulos)} artículos"
    log(f"  GDELT {consulta['id']} {ini:%Y-%m-%d %H:%M} → {fin:%Y-%m-%d %H:%M}: {estado}")


def descargar_gdelt(cfg: dict, raw: Path, desde: datetime, hasta: datetime) -> None:
    g = cfg["gdelt"]
    paso = timedelta(days=g.get("ventana_dias", 7))
    for consulta in g["consultas"]:
        inicio = desde
        while inicio < hasta:
            fin = min(inicio + paso, hasta)
            _gdelt_ventana(g, raw, consulta, inicio, fin)
            inicio = fin


def descargar_banco_mundial(cfg: dict, raw: Path) -> None:
    w = cfg["banco_mundial"]
    paises = ";".join(w["paises"].keys())
    for ind in w["indicadores"]:
        url = f"{w['url']}/country/{paises}/indicator/{ind['id']}"
        params = {"format": "json", "date": f"{w['desde']}:{w['hasta']}", "per_page": 1000}
        t = ahora()
        r = obtener(url, params)
        meta, filas, error = {}, [], None
        try:
            datos = r.json()
        except ValueError:
            datos = None
        if isinstance(datos, list) and len(datos) >= 2 and isinstance(datos[1], list):
            meta, filas = datos[0], datos[1]
            if meta.get("pages", 1) > 1:
                error = "La respuesta tiene más de una página; aumentar per_page."
        else:
            error = json.dumps(datos, ensure_ascii=False)[:300] if datos else (r.text or "")[:300]
        guardar_json(raw / "worldbank" / f"{ind['id']}.json", {
            "fuente": "banco_mundial", "indicador_id": ind["id"], "url": r.url,
            "params": params, "fecha_extraccion": iso(t), "http_status": r.status_code,
            "error": error, "meta": meta, "filas": filas,
        })
        log(f"  Banco Mundial {ind['id']}: {len(filas)} filas" + (f" · {error[:80]}" if error else ""))
        if PAUSA_EXTRA:
            time.sleep(1)


def descargar_usgs(cfg: dict, raw: Path) -> None:
    u = cfg["usgs"]
    params = {"format": "geojson", "starttime": u["desde"], "endtime": u["hasta"],
              "minlatitude": u["minlatitude"], "maxlatitude": u["maxlatitude"],
              "minlongitude": u["minlongitude"], "maxlongitude": u["maxlongitude"],
              "minmagnitude": u["minmagnitude"], "orderby": "time-asc"}
    t = ahora()
    r = obtener(u["url"], params)
    r.raise_for_status()
    datos = r.json()
    guardar_json(raw / "usgs" / "eventos.json", {
        "fuente": "usgs", "url": r.url, "params": params, "fecha_extraccion": iso(t),
        "respuesta": datos,
    })
    log(f"  USGS: {len(datos.get('features', []))} sismos")


# ---------------------------------------------------------------- fase 2: procesamiento

def leer_tvn(raw: Path) -> list[dict]:
    candidatos = []
    for xml in sorted((raw / "tvn").glob("rss_*.xml")):
        extraccion = datetime.strptime(xml.stem[4:], "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
        feed = feedparser.parse(xml.read_bytes())
        for e in feed.entries:
            pub = e.get("published_parsed") or e.get("updated_parsed")
            fpub = datetime.fromtimestamp(calendar.timegm(pub), UTC) if pub else None
            link = (e.get("link") or "").strip()
            candidatos.append({
                "titulo": (e.get("title") or "").strip(), "url": link,
                "medio": dominio(link) if link else None, "idioma": "es",
                "fecha_publicacion": iso(fpub), "fecha_deteccion": None,
                "fecha_extraccion": iso(extraccion), "tema": None, "origen": "tvn_rss",
                "alcance_texto": "titular/metadatos", "_archivo": xml.name,
            })
    return candidatos


def leer_gdelt(raw: Path) -> tuple[list[dict], list[dict]]:
    candidatos, consultas = [], []
    for arch in sorted((raw / "gdelt").glob("*.json")):
        w = leer_json(arch)
        consultas.append({
            "fuente": "gdelt", "consulta_id": w["consulta_id"], "tema": w["tema"],
            "query": w["params"]["query"], "desde": w["params"]["startdatetime"],
            "hasta": w["params"]["enddatetime"], "registros": len(w["articulos"]),
            "truncado": w["truncado"], "error": w["error"],
        })
        for a in w["articulos"]:
            url = (a.get("url") or "").strip()
            idioma = (a.get("language") or "").strip()
            candidatos.append({
                "titulo": (a.get("title") or "").strip(), "url": url,
                "medio": a.get("domain") or (dominio(url) if url else None),
                "idioma": IDIOMAS.get(idioma.lower(), idioma.lower() or None),
                # GDELT no informa la fecha de publicación: se deja nula, nunca se copia seendate.
                "fecha_publicacion": None,
                "fecha_deteccion": iso(fecha_gdelt(a.get("seendate"))),
                "fecha_extraccion": w["fecha_extraccion"], "tema": w["tema"],
                "origen": "gdelt", "alcance_texto": "titular/metadatos", "_archivo": arch.name,
            })
    return candidatos, consultas


def consolidar_noticias(candidatos: list[dict], filtro: dict) -> tuple[list[dict], list[dict], dict]:
    por_clave, excluidos = {}, []
    stats = {"candidatos": len(candidatos), "duplicados_fusionados": 0}

    for c in candidatos:
        if not c["titulo"]:
            excluidos.append({**c, "motivo": "sin_titulo"})
            continue
        if not url_valida(c["url"]):
            excluidos.append({**c, "motivo": "url_invalida"})
            continue
        clave = normalizar_url(c["url"])
        if clave not in por_clave:
            por_clave[clave] = {"id_noticia": id_noticia(c["url"]), **c}
            continue
        ex = por_clave[clave]
        stats["duplicados_fusionados"] += 1
        temas = set(filter(None, (ex["tema"] or "").split("|")))
        if c["tema"]:
            temas.add(c["tema"])
        ex["tema"] = "|".join(sorted(temas)) or None
        if c["origen"] not in ex["origen"].split("|"):
            ex["origen"] += "|" + c["origen"]
        for campo in ("fecha_publicacion", "idioma", "medio"):
            if not ex.get(campo) and c.get(campo):
                ex[campo] = c[campo]
        if c["fecha_deteccion"] and (not ex["fecha_deteccion"]
                                     or c["fecha_deteccion"] < ex["fecha_deteccion"]):
            ex["fecha_deteccion"] = c["fecha_deteccion"]

    noticias = []
    for n in por_clave.values():
        referencia = n["fecha_publicacion"] or n["fecha_deteccion"]
        if filtro.get("activo") and (not referencia
                                     or not filtro["desde"] <= referencia < filtro["hasta"]):
            excluidos.append({**n, "motivo": "fuera_de_intervalo"})
            continue
        noticias.append(n)

    noticias.sort(key=lambda n: (n["fecha_publicacion"] or n["fecha_deteccion"] or "", n["id_noticia"]),
                  reverse=True)
    stats["fechas_publicacion_nulas"] = sum(1 for n in noticias if not n["fecha_publicacion"])
    stats["excluidos"] = len(excluidos)
    return noticias, excluidos, stats


def construir_fuentes(noticias: list[dict]) -> list[dict]:
    medios: dict[str, dict] = {}
    for n in noticias:
        m = medios.setdefault(n["medio"], {"medio": n["medio"], "origen": set(), "idiomas": set(),
                                           "registros": 0})
        m["registros"] += 1
        m["origen"].update(n["origen"].split("|"))
        if n["idioma"]:
            m["idiomas"].add(n["idioma"])
    salida = []
    for m in sorted(medios.values(), key=lambda x: (-x["registros"], x["medio"])):
        salida.append({
            "medio": m["medio"], "origen": sorted(m["origen"]), "idiomas": sorted(m["idiomas"]),
            "registros": m["registros"],
            "condiciones": "Solo metadatos (titular, URL, fechas). Los derechos del contenido "
                           "pertenecen al medio; no se redistribuyen artículos, imágenes ni videos.",
        })
    return salida


def procesar_indicadores(cfg: dict, raw: Path) -> tuple[list[dict], list[dict]]:
    w = cfg["banco_mundial"]
    valores, nombres, extraccion, consultas, descargados = {}, {}, {}, [], set()
    for arch in sorted((raw / "worldbank").glob("*.json")):
        d = leer_json(arch)
        ind = d["indicador_id"]
        descargados.add(ind)
        extraccion[ind] = d["fecha_extraccion"]
        consultas.append({"fuente": "banco_mundial", "indicador_id": ind, "url": d["url"],
                          "registros": len(d["filas"]), "error": d["error"],
                          "ultima_actualizacion": (d.get("meta") or {}).get("lastupdated")})
        for f in d["filas"]:
            try:
                anio = int(f["date"])
            except (KeyError, TypeError, ValueError):
                continue
            valores[(f.get("countryiso3code"), ind, anio)] = f.get("value")
            nombres[ind] = (f.get("indicator") or {}).get("value")

    filas = []
    for iso3, iso2 in w["paises"].items():
        for ind in w["indicadores"]:
            for anio in range(int(w["desde"]), int(w["hasta"]) + 1):
                clave = (iso3, ind["id"], anio)
                valor = valores.get(clave)
                if ind["id"] not in descargados:
                    obs = "indicador no descargado"
                elif valor is None:
                    obs = "sin dato en la fuente"
                else:
                    obs = ""
                filas.append({
                    "id_evidencia": f"IND-{iso3}-{ind['id']}-{anio}", "pais_iso3": iso3,
                    "indicador_id": ind["id"], "indicador_nombre": nombres.get(ind["id"]),
                    "anio": anio, "valor": valor, "unidad": ind["unidad"], "observacion": obs,
                    "fuente_url": f"https://data.worldbank.org/indicator/{ind['id']}?locations={iso2}",
                    "fecha_extraccion": extraccion.get(ind["id"]), "licencia": w["licencia"],
                })
    return filas, consultas


def procesar_eventos(raw: Path) -> tuple[dict, list[dict]]:
    arch = raw / "usgs" / "eventos.json"
    if not arch.exists():
        return {"type": "FeatureCollection", "features": []}, []
    d = leer_json(arch)
    features = []
    for f in d["respuesta"].get("features", []):
        p, coords = f.get("properties", {}), (f.get("geometry") or {}).get("coordinates") or [None] * 3
        ms = lambda v: iso(datetime.fromtimestamp(v / 1000, UTC)) if v is not None else None
        features.append({
            "type": "Feature", "id": f.get("id"), "geometry": f.get("geometry"),
            "properties": {
                "id": f.get("id"), "magnitude": p.get("mag"), "time": ms(p.get("time")),
                "updated": ms(p.get("updated")), "longitude": coords[0], "latitude": coords[1],
                "depth": coords[2] if len(coords) > 2 else None, "place": p.get("place"),
                "status": p.get("status"), "url": p.get("url"),
            },
        })
    coleccion = {
        "type": "FeatureCollection",
        "metadata": {"fuente": "USGS", "consulta": d["url"], "fecha_extraccion": d["fecha_extraccion"],
                     "aviso": "La caja geográfica no equivale al territorio de Panamá. "
                              "Usar solo para hechos sísmicos."},
        "features": features,
    }
    return coleccion, [{"fuente": "usgs", "url": d["url"], "registros": len(features)}]


def escribir_csv(ruta: Path, filas: list[dict], columnas: list[str]) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columnas, extrasaction="ignore")
        w.writeheader()
        for fila in filas:
            w.writerow({k: ("" if fila.get(k) is None else fila.get(k)) for k in columnas})


DICCIONARIO = """# Diccionario de datos

Fechas en ISO 8601 UTC (sufijo Z). Celda vacía = valor nulo; nunca se rellena con cero.

## processed/noticias.csv
- **id_noticia**: `N-` + SHA-1 de la URL normalizada (estable entre ejecuciones).
- **titulo, url, medio, idioma**: metadatos de la noticia; idioma en código ISO cuando se conoce.
- **fecha_publicacion**: publicación según el medio. Nula en GDELT, que no la informa.
- **fecha_deteccion**: `seendate` de GDELT (cuándo GDELT la detectó). No es la publicación.
- **fecha_extraccion**: cuándo se descargó.
- **tema**: tema de la CONSULTA que la encontró (varios separados por `|`). No es una etiqueta verificada.
- **origen**: `tvn_rss`, `gdelt` o ambos separados por `|`.
- **alcance_texto**: texto disponible. `titular/metadatos` = no se tiene el artículo.

## processed/indicadores.csv
- **id_evidencia**: `IND-<país>-<indicador>-<año>`, para citar.
- **valor**: nulo si la fuente no tiene dato.
- **observacion**: `sin dato en la fuente`, `indicador no descargado` o vacío.
- **fuente_url**: página pública del indicador para ese país.

## processed/eventos.geojson
- **id**: ID de USGS; también es el ID de evidencia.
- **time, updated**: hora del sismo y de la última revisión, en UTC.
- **status**: `reviewed` (revisado) o `automatic`.

## processed/excluidos.csv
Registros descartados con su **motivo**: `sin_titulo`, `url_invalida`, `fuera_de_intervalo`.
"""


def procesar(cfg: dict, data: Path) -> dict:
    raw, proc = data / "raw", data / "processed"
    proc.mkdir(parents=True, exist_ok=True)
    corte = ahora()

    tvn = leer_tvn(raw)
    gdelt, consultas_gdelt = leer_gdelt(raw)
    noticias, excluidos, stats = consolidar_noticias(tvn + gdelt, cfg.get("filtro_intervalo") or {})
    indicadores, consultas_wb = procesar_indicadores(cfg, raw)
    eventos, consultas_usgs = procesar_eventos(raw)

    escribir_csv(proc / "noticias.csv", noticias, COLUMNAS_NOTICIAS)
    escribir_csv(proc / "excluidos.csv", excluidos,
                 ["origen", "_archivo", "titulo", "url", "fecha_publicacion", "fecha_deteccion", "motivo"])
    guardar_json(proc / "fuentes.json", construir_fuentes(noticias))
    escribir_csv(proc / "indicadores.csv", indicadores, COLUMNAS_INDICADORES)
    guardar_json(proc / "eventos.geojson", eventos)
    (data / "diccionario.md").write_text(DICCIONARIO, encoding="utf-8")

    archivos = {}
    conteos = {"noticias.csv": len(noticias), "excluidos.csv": len(excluidos),
               "fuentes.json": len(construir_fuentes(noticias)),
               "indicadores.csv": len(indicadores), "eventos.geojson": len(eventos["features"])}
    for nombre, n in conteos.items():
        archivos[f"processed/{nombre}"] = {"registros": n, "sha256": sha256(proc / nombre)}

    def rango(campo, filas):
        vals = sorted(f[campo] for f in filas if f.get(campo))
        return f"{vals[0][:10]} a {vals[-1][:10]}" if vals else "sin fechas"

    de_tvn = [n for n in noticias if "tvn_rss" in n["origen"]]
    de_gdelt = [n for n in noticias if "gdelt" in n["origen"]]
    validos = sum(1 for f in indicadores if f["valor"] is not None)
    sha_noticias = archivos["processed/noticias.csv"]["sha256"]
    ultima = lambda filas: max((f["fecha_extraccion"] for f in filas if f.get("fecha_extraccion")),
                               default=None)

    fuentes_catalogo = [
        {"id": "SRC-TVN", "fuente": "TVN · feed RSS", "url": (cfg.get("tvn") or {}).get("url") or None,
         "fecha_extraccion": ultima(de_tvn), "registros": len(de_tvn),
         "cobertura": f"{len(de_tvn)} noticias · publicación {rango('fecha_publicacion', de_tvn)}",
         "campos": "titulo, url, fecha_publicacion",
         "licencia": "Solo metadatos; el RSS no implica licencia sobre artículos, videos o imágenes",
         "transformaciones": "Deduplicación por URL normalizada; fechas a UTC", "sha256": sha_noticias},
        {"id": "SRC-GDELT", "fuente": "GDELT DOC 2.0", "url": cfg["gdelt"]["url"],
         "fecha_extraccion": ultima(de_gdelt), "registros": len(de_gdelt),
         "cobertura": f"{len(de_gdelt)} noticias · detección {rango('fecha_deteccion', de_gdelt)}",
         "campos": "titulo, url, dominio, idioma, seendate",
         "licencia": "La API no transfiere derechos de los medios enlazados",
         "transformaciones": "seendate → fecha_deteccion (fecha_publicacion nula); ventanas "
                             "divididas al llegar a 250; deduplicación por URL", "sha256": sha_noticias},
        {"id": "SRC-WB", "fuente": "Banco Mundial · Indicators API v2", "url": cfg["banco_mundial"]["url"],
         "fecha_extraccion": ultima(indicadores), "registros": len(indicadores),
         "cobertura": f"{len(cfg['banco_mundial']['paises'])} países · {cfg['banco_mundial']['desde']}–"
                      f"{cfg['banco_mundial']['hasta']} · {len(cfg['banco_mundial']['indicadores'])} "
                      f"indicadores · {validos} valores no nulos",
         "campos": "pais_iso3, indicador_id, anio, valor, unidad",
         "licencia": cfg["banco_mundial"]["licencia"],
         "transformaciones": "Cuadrícula completa; nulos conservados con observación",
         "sha256": archivos["processed/indicadores.csv"]["sha256"]},
        {"id": "SRC-USGS", "fuente": "USGS · catálogo sísmico", "url": cfg["usgs"]["url"],
         "fecha_extraccion": (eventos.get("metadata") or {}).get("fecha_extraccion"),
         "registros": len(eventos["features"]),
         "cobertura": f"{cfg['usgs']['desde'][:10]} a {cfg['usgs']['hasta'][:10]} · lat "
                      f"{cfg['usgs']['minlatitude']} a {cfg['usgs']['maxlatitude']} · lon "
                      f"{cfg['usgs']['minlongitude']} a {cfg['usgs']['maxlongitude']} · "
                      f"magnitud ≥ {cfg['usgs']['minmagnitude']}",
         "campos": "id, magnitude, time, updated, longitude, latitude, depth, place, status, url",
         "licencia": "Verificar condiciones de datos de terceros",
         "transformaciones": "Tiempos de milisegundos a ISO UTC; solo para hechos sísmicos",
         "sha256": archivos["processed/eventos.geojson"]["sha256"]},
    ]

    manifest = {
        "version": cfg.get("version", "v0-dev"),
        "nota": "Snapshot de desarrollo propio, no es el paquete oficial de la organización.",
        "fecha_corte_utc": iso(corte),
        "consultas": consultas_gdelt + consultas_wb + consultas_usgs
                     + [{"fuente": "tvn_rss", "capturas": len(list((raw / "tvn").glob("rss_*.xml")))}],
        "archivos": archivos,
        "estadisticas_noticias": stats,
        "filtro_intervalo": cfg.get("filtro_intervalo"),
        "transformaciones": [
            "Deduplicación de noticias por URL normalizada (sin esquema, www, utm_*, fbclid, barra final)",
            "Duplicados fusionados: se conservan todos los temas y orígenes; fecha_deteccion más temprana",
            "fecha_publicacion de GDELT queda nula; seendate se guarda como fecha_deteccion",
            "Fechas convertidas a ISO 8601 UTC",
            "Indicadores: cuadrícula país × indicador × año completa; nulos conservados",
            "Registros inválidos o fuera de intervalo movidos a excluidos.csv con su motivo",
        ],
        "fuentes": fuentes_catalogo,
    }
    guardar_json(data / "manifest.json", manifest)
    return manifest


# ---------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser(description="Descarga y procesa el snapshot de datos del reto.")
    ap.add_argument("--solo", nargs="+", choices=["tvn", "gdelt", "wb", "usgs"],
                    help="descargar solo estas fuentes")
    ap.add_argument("--desde", help="inicio de la ventana de GDELT (YYYY-MM-DD)")
    ap.add_argument("--hasta", help="fin de la ventana de GDELT (YYYY-MM-DD)")
    ap.add_argument("--solo-procesar", action="store_true",
                    help="no descargar; regenerar processed/ desde raw/")
    args = ap.parse_args()

    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    data = RAIZ / cfg.get("data_dir", "data")
    raw = data / "raw"

    if not args.solo_procesar:
        fuentes = set(args.solo or ["tvn", "gdelt", "wb", "usgs"])
        hasta = fecha_iso_entrada(args.hasta) if args.hasta else ahora()
        desde = (fecha_iso_entrada(args.desde) if args.desde
                 else hasta - timedelta(days=cfg["gdelt"].get("dias_atras", 30)))
        log(f"Descargando {', '.join(sorted(fuentes))}…")
        pasos = [("tvn", lambda: descargar_tvn(cfg, raw)),
                 ("wb", lambda: descargar_banco_mundial(cfg, raw)),
                 ("usgs", lambda: descargar_usgs(cfg, raw)),
                 ("gdelt", lambda: descargar_gdelt(cfg, raw, desde, hasta))]
        for clave, paso in pasos:
            if clave in fuentes:
                try:
                    paso()
                except Exception as e:  # una fuente caída no detiene a las demás
                    log(f"  ! {clave}: {e}")

    log("Procesando…")
    m = procesar(cfg, data)
    for nombre, info in m["archivos"].items():
        log(f"  {nombre:<28} {info['registros']:>6} registros")
    s = m["estadisticas_noticias"]
    log(f"  duplicados fusionados: {s['duplicados_fusionados']} · excluidos: {s['excluidos']}")
    if m["archivos"]["processed/noticias.csv"]["registros"] < 100:
        log("  ! Menos de 100 noticias: el mínimo operativo del reto es 100 (al menos 20 de TVN).")
    log(f"Manifest: {data / 'manifest.json'}")


if __name__ == "__main__":
    sys.exit(main())
`````

### `tests/test_ingesta.py`

`````python
"""Pruebas de la ingesta con respuestas de ejemplo; no usan internet."""
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ingesta"))
import descargar_snapshot as ds  # noqa: E402

CFG = yaml.safe_load((Path(ds.__file__).parent / "config.yaml").read_text(encoding="utf-8"))

RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>TVN</title>
<item><title>Canal de Panam\xc3\xa1 anuncia restricci\xc3\xb3n de calado</title>
<link>https://www.tvn-2.com/nacionales/canal-calado_1/?utm_source=rss</link>
<pubDate>Mon, 05 Oct 2026 14:30:00 -0500</pubDate></item>
<item><title></title><link>https://www.tvn-2.com/sin-titulo/</link></item>
</channel></rss>"""


def escribir_raw(raw: Path) -> None:
    (raw / "tvn").mkdir(parents=True)
    (raw / "tvn" / "rss_20261006T170000Z.xml").write_bytes(RSS)
    ds.guardar_json(raw / "gdelt" / "canal_20260906_20261006.json", {
        "fuente": "gdelt", "consulta_id": "canal", "tema": "logistica_canal",
        "params": {"query": '"Panama Canal"', "startdatetime": "20260906000000",
                   "enddatetime": "20261006000000"},
        "fecha_extraccion": "2026-10-06T17:05:00Z", "http_status": 200, "error": None,
        "truncado": False,
        "articulos": [
            # Mismo artículo que el RSS de TVN, con otra forma de URL.
            {"url": "http://tvn-2.com/nacionales/canal-calado_1", "title": "Canal de Panamá anuncia",
             "seendate": "20261006T010000Z", "domain": "tvn-2.com", "language": "Spanish"},
            {"url": "https://example.com/panama-canal-draft", "title": "Panama Canal limits draft",
             "seendate": "20261005T220000Z", "domain": "example.com", "language": "English"},
            {"url": "no-es-una-url", "title": "Roto", "seendate": "malo", "language": "English"},
        ],
    })
    ds.guardar_json(raw / "worldbank" / "FP.CPI.TOTL.ZG.json", {
        "fuente": "banco_mundial", "indicador_id": "FP.CPI.TOTL.ZG", "url": "https://api.example",
        "params": {}, "fecha_extraccion": "2026-10-06T17:01:00Z", "http_status": 200, "error": None,
        "meta": {"lastupdated": "2026-07-01", "pages": 1},
        "filas": [
            {"indicator": {"id": "FP.CPI.TOTL.ZG", "value": "Inflation, consumer prices (annual %)"},
             "countryiso3code": "PAN", "date": "2022", "value": 2.86},
            {"indicator": {"id": "FP.CPI.TOTL.ZG", "value": "Inflation, consumer prices (annual %)"},
             "countryiso3code": "PAN", "date": "2024", "value": None},
        ],
    })
    ds.guardar_json(raw / "usgs" / "eventos.json", {
        "fuente": "usgs", "url": "https://usgs.example", "params": {},
        "fecha_extraccion": "2026-10-06T17:02:00Z",
        "respuesta": {"features": [{
            "id": "us7000abcd", "geometry": {"type": "Point", "coordinates": [-82.5, 7.9, 10.0]},
            "properties": {"mag": 4.5, "place": "30 km S of Example", "time": 1704067200000,
                           "updated": 1704153600000, "status": "reviewed", "url": "https://usgs/ev"}}]},
    })


def leer_csv(ruta: Path) -> list[dict]:
    with open(ruta, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_procesamiento_completo(tmp_path):
    escribir_raw(tmp_path / "raw")
    manifest = ds.procesar(CFG, tmp_path)
    proc = tmp_path / "processed"

    noticias = leer_csv(proc / "noticias.csv")
    assert len(noticias) == 2  # TVN y GDELT del mismo artículo quedan fusionados
    tvn = next(n for n in noticias if "tvn-2.com" in n["url"])
    assert tvn["origen"] == "tvn_rss|gdelt"
    assert tvn["fecha_publicacion"] == "2026-10-05T19:30:00Z"   # -05:00 convertido a UTC
    assert tvn["fecha_deteccion"] == "2026-10-06T01:00:00Z"     # tomado de GDELT
    assert tvn["tema"] == "logistica_canal"
    assert tvn["id_noticia"] == ds.id_noticia("https://tvn-2.com/nacionales/canal-calado_1")

    externa = next(n for n in noticias if "example.com" in n["url"])
    assert externa["fecha_publicacion"] == ""   # GDELT no la informa: nula, no se inventa
    assert externa["idioma"] == "en"

    excluidos = leer_csv(proc / "excluidos.csv")
    assert {e["motivo"] for e in excluidos} == {"sin_titulo", "url_invalida"}

    indicadores = leer_csv(proc / "indicadores.csv")
    assert len(indicadores) == 6 * 6 * 15        # cuadrícula completa
    fila_2022 = next(i for i in indicadores if i["id_evidencia"] == "IND-PAN-FP.CPI.TOTL.ZG-2022")
    assert fila_2022["valor"] == "2.86" and fila_2022["unidad"] == "% anual"
    fila_2024 = next(i for i in indicadores if i["id_evidencia"] == "IND-PAN-FP.CPI.TOTL.ZG-2024")
    assert fila_2024["valor"] == "" and fila_2024["observacion"] == "sin dato en la fuente"
    otra = next(i for i in indicadores if i["indicador_id"] == "SP.POP.TOTL")
    assert otra["observacion"] == "indicador no descargado"

    eventos = json.loads((proc / "eventos.geojson").read_text(encoding="utf-8"))
    p = eventos["features"][0]["properties"]
    assert p["time"] == "2024-01-01T00:00:00Z" and p["latitude"] == 7.9

    assert manifest["archivos"]["processed/noticias.csv"]["sha256"] == ds.sha256(proc / "noticias.csv")
    assert [f["id"] for f in manifest["fuentes"]] == ["SRC-TVN", "SRC-GDELT", "SRC-WB", "SRC-USGS"]


def test_procesamiento_es_determinista(tmp_path):
    escribir_raw(tmp_path / "raw")
    ds.procesar(CFG, tmp_path)
    primero = ds.sha256(tmp_path / "processed" / "noticias.csv")
    ds.procesar(CFG, tmp_path)
    assert ds.sha256(tmp_path / "processed" / "noticias.csv") == primero


def test_filtro_intervalo_mueve_a_excluidos(tmp_path):
    escribir_raw(tmp_path / "raw")
    cfg = {**CFG, "filtro_intervalo": {**CFG["filtro_intervalo"], "activo": True}}
    ds.procesar(cfg, tmp_path)
    assert leer_csv(tmp_path / "processed" / "noticias.csv") == []
    motivos = [e["motivo"] for e in leer_csv(tmp_path / "processed" / "excluidos.csv")]
    assert motivos.count("fuera_de_intervalo") == 2


def test_gdelt_divide_ventana_al_llegar_a_250(tmp_path, monkeypatch):
    ds.PAUSA_EXTRA = False
    llamadas = []

    class Resp:
        status_code, text = 200, ""

        def __init__(self, n):
            self.n = n

        def json(self):
            return {"articles": [{"url": f"https://x.com/{i}", "title": "t"} for i in range(self.n)]}

    def falso(url, params=None):
        llamadas.append(params["startdatetime"])
        return Resp(250 if len(llamadas) == 1 else 10)

    monkeypatch.setattr(ds, "obtener", falso)
    consulta = {"id": "eco", "tema": "economia", "query": "Panama economy"}
    ini = datetime(2026, 9, 1, tzinfo=timezone.utc)
    fin = datetime(2026, 9, 8, tzinfo=timezone.utc)
    ds._gdelt_ventana(CFG["gdelt"], tmp_path / "raw", consulta, ini, fin)
    assert len(llamadas) == 3                      # la primera se dividió en dos mitades
    assert len(list((tmp_path / "raw" / "gdelt").glob("*.json"))) == 2


def test_normalizar_url():
    a = ds.normalizar_url("https://www.TVN-2.com/nota/?utm_source=x&id=5#arriba")
    b = ds.normalizar_url("http://tvn-2.com/nota?id=5")
    assert a == b == "tvn-2.com/nota?id=5"
`````
