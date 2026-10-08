# HackIAthon · Reto TVN Media

Entrega: jueves 8 de octubre de 2026, 23:59 (hora de Panamá). Equipo: Guille (datos, motor e IA)
y Víctor (producto, interfaz, Notion y pruebas). Plan detallado: `documentacion/traspaso-hackiathon-tvn.md`.

## Empezar (compañero nuevo)

1. `git clone https://github.com/grivper/hackiathon-gui-vic.git` y `cd hackiathon-gui-vic`.
2. `make instalar`.
3. Para ver el avance, abre las páginas de Notion que te compartieron. No necesitas el token.

### Bandeja editorial en Windows (sin GNU Make)

Con el entorno virtual creado y las bases DuckDB preparadas, inicia la interfaz con:

```
.venv\Scripts\python.exe -m streamlit run app/app.py
```

**Quién sincroniza:** solo una persona ejecuta `python notion_sync.py`. El estado de la sincronización
(`.notion_state.json`) es local y no se sube a git: si dos personas sincronizan, Notion queda con
páginas duplicadas. Los demás editan los archivos de `bitacora/` (`tareas.yaml`, `decisiones.yaml`,
`paginas/*.md`), hacen `git push` y quien sincroniza hace `git pull` y ejecuta el sync.

## Datos para trabajar (espejo entre los dos)

El snapshot (`data/processed/`, `data/manifest.json`, `data/diccionario.md`, `data/reporte_calidad.md`) está en
git. La base DuckDB (`data/senales.duckdb`) es derivada y no se sube: se construye igual en cada máquina.

```
git pull --rebase
source .venv/bin/activate
make arrancar        # instalar dependencias + construir la base (idempotente)
```

`make db` vuelve a construir la base solo si cambió el `manifest.json` (compara su SHA-256). Para forzarla:
`python motor/cargar_db.py --forzar`. El hash del manifest aparece en `data/reporte_calidad.md`: el mismo hash
en las dos máquinas significa los mismos datos. Los registros con fecha inválida o sin campos obligatorios van a
la tabla `rechazados` y no frenan la carga (prueba T01). Solo una persona regenera el snapshot (`make datos`) y
lo commitea; la otra solo hace `git pull`.

Para el paquete oficial, el contrato (sección 7) excluye lo que esté fuera de [2024-01-01, 2025-10-01). Por defecto
la carga no filtra por fecha (el RSS de desarrollo solo trae noticias recientes). Para aplicar el rango:
`make db-oficial` (equivale a `python motor/cargar_db.py --rango 2024-01-01 2025-10-01`). Las noticias fuera de
rango van a la tabla `excluidos` (las de fecha vacía se conservan) y la base siempre se reconstruye. Flujo para
cargar el paquete oficial: copiar sus archivos a `data/processed/` y `data/manifest.json`, correr
`make db-oficial` y después `make motor`, y revisar `data/reporte_calidad.md`. No commitear esos archivos
oficiales sin acordarlo antes con quien es dueño del snapshot.

## Motor: clasificación por tema y agrupación de eventos

```
make motor        # descarga el modelo si falta (una vez, ~470 MB) y corre clasificar + agrupar + puntuar (idempotente)
make generar      # fichas con borrador citado (tabla `fichas` y data/fichas.jsonl); necesita Ollama, ver abajo
make muestra      # genera la muestra ciega a etiquetar a mano (data/etiquetas/muestra_etiquetado.csv)
make evaluar      # macro-F1 contra las etiquetas humanas (data/evaluacion_clasificacion.md)
```

- **Temas:** se editan en `motor/temas.yaml` (descripción y semillas de los 6 temas del reto, más grupos de
  contraste como deportes, sucesos o política que se mapean a `otros`).
- **Clasificación:** por defecto, embeddings multilingües (`paraphrase-multilingual-MiniLM-L12-v2`, en CPU,
  sin red una vez descargado) comparados contra prototipos de cada tema; si el parecido es bajo o hay
  empate, el sistema se abstiene (`otros`). El baseline es TF-IDF con las mismas semillas.
- **Agrupación:** titulares del mismo evento por similitud de embeddings dentro de una ventana de 3 días y
  con un máximo de 3 días por grupo. La corroboración cuenta procedencias distintas, no cantidad de
  notas: una agencia repetida por varios medios vale una sola.
- Los resultados viven en `data/motor.duckdb` (derivado, no se sube a git).
- **Etiquetado humano:** quien etiqueta sigue `data/etiquetas/LEEME_etiquetado.md`, sin mirar el modelo. Las
  etiquetas sí se suben a git. Mientras no existan, no se reporta macro-F1.

## Datos: snapshot propio de desarrollo

Mientras no llegue el paquete oficial, `ingesta/descargar_snapshot.py` descarga las cuatro
fuentes y genera los archivos del contrato de la sección 7 en `data/`.

1. Copia la URL del RSS de TVN (enlace [2] del PDF del reto) en `ingesta/config.yaml` → `tvn.url`.
2. `make datos` (GDELT pide una consulta cada 5 segundos: la descarga completa tarda varios minutos).
3. `make test` para verificar el procesamiento.

El RSS solo trae noticias recientes: conviene ejecutar `python ingesta/descargar_snapshot.py --solo tvn`
varias veces durante el reto; las capturas se acumulan y se deduplican.
Para otro período de GDELT: `--solo gdelt --desde 2025-07-01 --hasta 2025-09-30`.

GDELT a veces responde con HTTP 200 y un texto de "limit requests" en lugar de JSON. El script reintenta con
pausas crecientes y omite las ventanas ya descargadas, así que una corrida cortada se reanuda repitiendo el
mismo comando **con fechas fijas** (`--desde` y `--hasta`); sin ellas la ventana depende de la hora actual.

### Reproducibilidad: `data/raw/` no está en git

`make procesar` (y el paso final de cada descarga) procesa **todo** lo que haya en `data/raw/`, que no se
sube a git. El snapshot que se commitea es `data/processed/` + `data/manifest.json`; por eso solo una persona
lo regenera. Antes de reprocesar, revisa que `data/raw/` no tenga descargas parciales o de prueba: muévelas a
`data/_descartado/` (ignorada por git y no leída por el procesamiento). Con `raw/` limpio, `make procesar`
regenera los mismos archivos byte a byte; solo cambia `fecha_corte_utc` en el manifest.

### Historial de TVN por sitemaps

El RSS solo trae ~150 ítems recientes y GDELT solo cubre ~90 días (y devuelve 429 con facilidad). Para el
historial se usan los sitemaps mensuales de TVN (`tvn_sitemap_contents_AAAA_MM.xml`, declarados en su `robots.txt`):

```
python ingesta/descargar_snapshot.py --solo sitemaps            # de 2025-10 a hoy (config: tvn.sitemaps)
python ingesta/descargar_snapshot.py --solo sitemaps --refrescar # vuelve a bajar todos los meses
```

Solo se guardan título, URL y fecha (no se descarga ningún artículo). **`fecha_deteccion` es el `lastmod` del
sitemap, no la fecha de publicación**, por eso `fecha_publicacion` queda vacía. Al deduplicar por URL, el RSS
gana sobre el sitemap y el sitemap sobre GDELT. Los XML crudos no se suben a git.

El `manifest.json` alimenta automáticamente el Catálogo de datos en Notion.

### Período y fuentes (respuesta de la organización)

- Las fuentes del PDF son ejemplos: se puede hacer scraping general y buscar otras fuentes.
- Para entrenar y desarrollar sirve cualquier fecha. Para la demo presencial hay que usar datos
  recientes: el período válido empieza el 2025-10-02 (el rango `[2024-01-01, 2025-10-01)` queda excluido
  de la demo). La fecha final exacta está por confirmar.

## Bitácora del proyecto sincronizada con Notion

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
7. Opcional: `NOTION_TAREAS_PAGE_ID` en `.env` para que la base Tareas viva en su propia página.
8. Primera sincronización: `python notion_sync.py`

Si tu shell ya define `NOTION_TOKEN`, el valor de `.env` tiene prioridad. Notion limita los bloques
del plan gratuito en workspaces con varios miembros: invita a tu compañero como **invitado** de las
páginas, no como miembro, y guarda el `.env` del espacio oficial aparte (nunca en git).

Se crean las 8 páginas que exige el reto, con bases de datos de Tareas, Decisiones,
Fuentes, Fichas y Matriz de pruebas.

## Uso diario

```
python bitacora.py decision "Usar embeddings multilingües para agrupar"
python bitacora.py tarea "Implementar validador de citas"
python bitacora.py estado TAR-009 "En curso"
python bitacora.py epica "Datos"
python bitacora.py tarea "Cargar DuckDB" --epica EPI-002
python bitacora.py prueba T07 Falló --observado "El agente obedeció al artículo"
python bitacora.py prueba T07 Corregida --correccion "Fuentes delimitadas como datos"
python bitacora.py resumen
```

Las **épicas** (`EPI-`) agrupan tareas con `--epica`. Su estado y su barra de progreso
(`██████░░░░ 60% (3/5)`) se calculan solos al sincronizar a partir de sus tareas: no se editan a mano.
Para que la base Tareas viva en una página propia de Notion, define `NOTION_TAREAS_PAGE_ID` en `.env`.

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

## Generación con LLM local (Ollama)

`make generar` usa un LLM local por Ollama (sin API externa). El código valida las citas y decide la abstención; el modelo solo redacta.

1. Instalá Ollama (https://ollama.com) y bajá un modelo: `ollama pull gemma3:4b` (modelo vigente para la demo). Si el binario no está en el `PATH` (instalación en `~/.local/ollama`), usá la ruta completa y apuntá a los modelos: `export OLLAMA_MODELS=~/.local/ollama/models`.
2. Levantá el servidor y dejalo corriendo en una terminal aparte: `ollama serve` (o `~/.local/ollama/bin/ollama serve`). Comprobá que responde con `curl localhost:11434/api/tags`; debe listar `gemma3:4b`.
3. Con el servidor en marcha, desde la raíz del repo y con el venv activo, generá las fichas:
   - `LLM_MODELO=gemma3:4b make generar`: toma `--top 5 --min-noticias 2` por defecto. Con los datos actuales casi todos los grupos tienen una sola noticia, así que esto genera muy pocas fichas.
   - `make generar GRUPOS="--top 10 --min-noticias 1"`: los N grupos de mayor puntaje, sin filtrar por cantidad de noticias.
   - `make generar GRUPOS="--grupo G-xxxx --grupo G-yyyy"`: grupos concretos (`--forzar` regenera fichas ya revisadas por una persona).
   Tarda unos 19 s por ficha (mediana medida en la máquina de demo).
4. Qué escribe: hace upsert por grupo en la tabla `fichas` de `data/motor.duckdb` y **reescribe `data/fichas.jsonl` completo desde esa tabla**. Si tu `motor.duckdb` local no tiene las fichas que ya estaban en el jsonl commiteado, esas líneas desaparecen del archivo. Antes de commitear mirá `git diff --stat data/fichas.jsonl` y regenerá los grupos que falten (`--grupo ...`) para no perder fichas.
5. Qué se ve en la app: las tarjetas con ficha muestran el borrador y el selector de estado de revisión; el resto muestra "Borrador no generado para este grupo (ejecutar `make generar`)". Recargá la página de Streamlit después de generar.
6. Variables opcionales: `OLLAMA_HOST`, `LLM_NUM_THREAD` (núcleos físicos, 4 por defecto), `LLM_NUM_CTX` (4096), `LLM_NUM_PREDICT` (768).
7. Para el benchmark oficial de la máquina de demo, con los overrides de entorno desactivados, usa `.venv/Scripts/python.exe motor/medir_llm.py --modelo gemma3:4b --n 10`. El comando informa mediana, p95 y cuántas salidas conservan JSON y citas válidas; la evidencia oficial queda en `documentacion/evidencia-modelo-real.md`.

La medición oficial de la máquina de demo (Ollama 0.40.1, `gemma3:4b`, n=10) obtuvo mediana 18,86863055 s, p95 41,04204075 s, 9,856653 tok/s, JSON válido 10/10 y al menos una cita válida 9/10 (TAR-022). No alcanzó la meta de mediana ≤ 15 s; por esa decisión, las fichas finales se pregeneran antes de la demo. Las corridas n=3 exploratoria y n=5 de desarrollo permanecen separadas como contexto histórico en la evidencia oficial.

## Demo sin internet (T10)

Todo el flujo corre en local: DuckDB, el modelo de embeddings en `modelos/` (con la caché presente, `motor/embeddings.py` fuerza `HF_HUB_OFFLINE=1`) y Ollama en `localhost`. Verificado en un entorno sin red (`unshare -rn`, solo loopback): `make arrancar`, `make motor`, la app Streamlit y `motor/medir_llm.py` con gemma3:4b funcionaron sin errores.

Preparación (con internet, una sola vez en la máquina de la demo):
1. `make instalar` y `make arrancar && make motor`: deja las dependencias, `modelos/` y las bases listas.
2. `ollama pull gemma3:4b`.
3. `make generar`: pregenera las fichas con borrador citado. Se guardan en la tabla `fichas` de `data/motor.duckdb` (local, no va a git), así que hay que correrlo en esa máquina o copiar ese archivo.

Durante la demo no hace falta red. Fallbacks:
- Si Ollama no responde, la app muestra las fichas ya generadas y marca "Borrador no generado" en el resto; el motor se abstiene en vez de inventar.
- Si falta `data/motor.duckdb`, `make arrancar && make motor` lo reconstruye desde el snapshot en un minuto aproximadamente, sin red.
