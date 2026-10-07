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

## Motor: clasificación por tema y agrupación de eventos

```
make motor        # descarga el modelo si falta (una vez, ~470 MB) y corre clasificar + agrupar + puntuar (idempotente)
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
