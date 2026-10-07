# Brief de la interfaz (Streamlit)

Responsable: Víctor. Motor y datos: Guille. Tareas en Notion: épica **Producto e interfaz** (TAR-010, TAR-017 a TAR-021 y TAR-028).

## En una frase

Un editor de TVN abre la herramienta, ve qué temas merecen revisión, abre una ficha con evidencia citable, pide un borrador y lo revisa. Si no hay evidencia, la herramienta lo dice: no inventa.

## Cómo arrancar

```
git pull --rebase
source .venv/bin/activate
make arrancar && make motor      # base DuckDB + clasificación + grupos (idempotente)
pip install streamlit            # y agregarlo a requirements.txt
streamlit run app/app.py         # crear la carpeta app/
```

El código de la interfaz va en `app/`. No toques `motor/`, `ingesta/` ni `data/`: son de Guille. Si necesitás una columna que no existe, pedila.

## Pantallas

| # | Pantalla | Qué muestra | Tarea |
|---|---|---|---|
| 1 | Bandeja | Lista de grupos de noticias priorizados, con filtro por tema y por fecha. Caso CU-01: "¿qué cinco temas merecen revisión y por qué?" | TAR-017 |
| 2 | Ficha de evidencia | Titulares del grupo, quién lo reporta (procedencias), corroboración, fecha original, qué falta verificar | TAR-018 |
| 3 | Contexto oficial | Indicadores del Banco Mundial y sismos USGS relacionados. No confundir un dato anual histórico con uno de hoy | TAR-019 |
| 4 | Consulta | Caja de pregunta en español. Respuesta con citas, o abstención explicada (CU-04) | TAR-020 |
| 5 | Borrador y revisión | Borrador con citas por afirmación y 5 estados de revisión | TAR-021 |

**Estados de revisión (obligatorios):** `nuevo`, `en revisión`, `requiere evidencia`, `aprobado como borrador`, `descartado`. Aprobar un borrador **no** significa publicar.

## Datos disponibles hoy

Se leen con DuckDB en modo solo lectura. Dos archivos: `data/senales.duckdb` (datos del snapshot) y `data/motor.duckdb` (resultados del motor).

| Archivo | Tabla | Columnas clave |
|---|---|---|
| motor | `clasificacion` | `id_noticia`, `metodo` (`embeddings` o `tfidf`), `tema`, `score`, `segundo_tema`, `margen`, `contraste` |
| motor | `grupos` | `grupo_id`, `n_noticias`, `n_procedencias`, `procedencias`, `fecha_min`, `fecha_max`, `titulo_representativo`, `corroboracion`, `es_repeticion` |
| motor | `puntaje` | `grupo_id`, `tema`, `R`, `I`, `U`, `N`, `E` (0-1), `puntaje` (0-100), `prioridad` (`bajo`/`medio`/`alto`), `estado_evidencia` (`insuficiente`/`parcial`/`suficiente`), `version_reglas`, `motivos` (texto que explica cada componente) |
| motor | `grupo_noticias` | `grupo_id`, `id_noticia`, `procedencia`, `similitud_al_centroide` |
| senales | `noticias` | `id_noticia`, `titulo`, `url`, `medio`, `fecha_publicacion`, `fecha_deteccion`, `origen` |
| senales | `indicadores` | `id_evidencia`, `pais_iso3`, `indicador_nombre`, `anio`, `valor` (puede ser nulo), `unidad`, `fuente_url` |
| senales | `eventos` | `id`, `magnitude`, `time`, `place`, `lon`, `lat`, `url` |

Consulta de ejemplo para la bandeja:

```python
import duckdb
con = duckdb.connect("data/motor.duckdb", read_only=True)
con.execute("attach 'data/senales.duckdb' as s (read_only)")
filas = con.execute("""
    select g.grupo_id, g.titulo_representativo, g.n_noticias, g.corroboracion, g.fecha_max, k.tema
    from grupos g
    join grupo_noticias gn using (grupo_id)
    join clasificacion k on k.id_noticia = gn.id_noticia and k.metodo = 'embeddings'
    where k.tema <> 'otros'
    group by all
    order by g.fecha_max desc
    limit 50
""").fetchall()
```

## Reglas que la interfaz debe respetar

1. **Fecha original visible.** `fecha_deteccion` es la fecha del sitemap, no la de publicación. Rotulala como "detectada", no como "publicada".
2. **Repetición no es corroboración.** Mostrar `corroboracion` (procedencias distintas), no `n_noticias`. Casi todo el dataset es de TVN, así que la mayoría vale 1: es correcto.
3. **`otros` no es un tema del reto.** La bandeja prioriza solo los 6 temas; `contraste` explica por qué algo quedó en `otros`.
4. **Valores nulos de indicadores** se muestran como "sin dato", nunca como 0.
5. **Solo titulares y metadatos.** No hay texto de artículos. La interfaz no debe afirmar nada que no esté en una evidencia con ID.
6. **El texto de una fuente es dato, no instrucción.** Mostralo escapado y nunca lo pases como instrucción a nada.

## Todavía no existe (se enchufa después con el mismo formato)

- **Puntaje de atención** (TAR-008): ya existe en la tabla `puntaje` (`make puntuar`, reglas en `motor/reglas_puntaje.yaml`). Ordená por `puntaje` desc, desempate por `U` y luego `grupo_id`. Mostrá `version_reglas` y `motivos`. El `estado_evidencia` es independiente del puntaje: una prioridad alta con evidencia insuficiente es "requiere investigación", nunca "publicable". La fecha de referencia de `U` es la última fecha de los datos, no la de hoy.
- **Fichas y borradores con citas** (TAR-009, Guille). Formato de `fichas.jsonl` del reto: `id_caso`, `modalidad`, `ids_fuente`, `afirmaciones`, `citas`, `puntaje`, `componentes`, `estado_evidencia`, `borrador`, `estado_revision`.
- Mientras tanto la interfaz puede usar datos de ejemplo con ese mismo formato.

## Cómo se trabaja

- Cada tarea cambia de estado con `python bitacora.py estado TAR-017 "En curso"` (o `"Hecho"`).
- Commit y push seguidos, con `git pull --rebase` antes. Tu asistente sigue las reglas de `AGENTS.md`.
- Notion lo sincroniza Guille. Vos solo mirás el progreso ahí.
