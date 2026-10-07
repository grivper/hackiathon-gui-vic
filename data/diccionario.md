# Diccionario de datos

Fechas en ISO 8601 UTC (sufijo Z). Celda vacía = valor nulo; nunca se rellena con cero.

## processed/noticias.csv
- **id_noticia**: `N-` + SHA-1 de la URL normalizada (estable entre ejecuciones).
- **titulo, url, medio, idioma**: metadatos de la noticia; idioma en código ISO cuando se conoce.
- **fecha_publicacion**: publicación según el medio. Nula en GDELT, que no la informa.
- **fecha_deteccion**: `seendate` de GDELT (cuándo GDELT la detectó). No es la publicación.
- **fecha_extraccion**: cuándo se descargó.
- **tema**: tema de la CONSULTA que la encontró (varios separados por `|`). No es una etiqueta verificada.
- **origen**: `tvn_rss`, `tvn_sitemap`, `gdelt` o varios separados por `|`. Si un duplicado existe
  en varios orígenes, titulo/idioma/medio se quedan con el de mayor prioridad (tvn_rss > tvn_sitemap > gdelt).
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
