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
