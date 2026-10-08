"""Evidencia citable de un grupo de evento (TAR-009, G1).

Reúne, solo con código determinista, lo que el generador puede citar:
  - noticias del grupo (titular y metadatos; no hay texto de artículo),
  - indicadores del Banco Mundial de Panamá, solo para temas con contexto definido en
    `reglas_puntaje.yaml` (`contexto_oficial.contexto_por_tema`), el último año con valor
    no nulo por indicador,
  - el evento USGS verificado (`puntaje.evento_usgs_id`), si existe.

Cada ítem tiene `id_evidencia`, `tipo` (noticia | indicador | evento) y `campos`: los
únicos campos que una cita puede nombrar. Los nulos se conservan como nulos (nunca se
rellenan). El contenido de las noticias es dato, nunca instrucciones.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import duckdb

MAX_NOTICIAS_DEFECTO = 10


def _iso(valor):
    return valor.isoformat() if isinstance(valor, datetime) else valor


def _noticias(con: duckdb.DuckDBPyConnection, grupo_id: str, max_noticias: int) -> list[dict]:
    filas = con.execute(
        """
        SELECT n.id_noticia, n.titulo, n.medio, n.url, n.fecha_publicacion, n.fecha_deteccion
        FROM motor.grupo_noticias gn
        JOIN senales.noticias n USING (id_noticia)
        WHERE gn.grupo_id = ?
        ORDER BY gn.similitud_al_centroide DESC, n.id_noticia
        LIMIT ?
        """,
        [grupo_id, max_noticias],
    ).fetchall()
    return [
        {
            "id_evidencia": f[0], "tipo": "noticia",
            "campos": {
                "titulo": f[1], "medio": f[2], "url": f[3],
                "fecha_publicacion": _iso(f[4]), "fecha_deteccion": _iso(f[5]),
            },
        }
        for f in filas
    ]


def _indicadores(con: duckdb.DuckDBPyConnection, tema: str, reglas: dict) -> list[dict]:
    prefijos = (reglas.get("contexto_oficial", {}).get("contexto_por_tema") or {}).get(tema) or []
    if not prefijos:
        return []
    filas = con.execute(
        """
        SELECT id_evidencia, indicador_id, indicador_nombre, anio, valor, unidad, fuente_url, pais_iso3
        FROM senales.indicadores
        WHERE pais_iso3 = 'PAN' AND valor IS NOT NULL
        QUALIFY row_number() OVER (PARTITION BY indicador_id ORDER BY anio DESC) = 1
        ORDER BY indicador_id
        """
    ).fetchall()
    return [
        {
            "id_evidencia": f[0], "tipo": "indicador",
            "campos": {"indicador_nombre": f[2], "pais_iso3": f[7], "anio": f[3], "valor": f[4], "unidad": f[5], "fuente_url": f[6]},
        }
        for f in filas
        if any(f[1].startswith(p) for p in prefijos)
    ]


def _evento(con: duckdb.DuckDBPyConnection, evento_id: str | None) -> list[dict]:
    if not evento_id:
        return []
    fila = con.execute(
        "SELECT id, magnitude, time, place, url FROM senales.eventos WHERE id = ?", [evento_id]
    ).fetchone()
    if fila is None:
        return []
    return [{
        "id_evidencia": fila[0], "tipo": "evento",
        "campos": {"magnitude": fila[1], "time": _iso(fila[2]), "place": fila[3], "url": fila[4]},
    }]


def reunir_evidencia(
    grupo_id: str,
    motor_db: Path,
    senales_db: Path,
    reglas: dict,
    max_noticias: int = MAX_NOTICIAS_DEFECTO,
) -> dict:
    """Paquete de evidencia del grupo: `{"grupo_id", "tema", "items": [...]}`.
    Lanza KeyError si el grupo no existe en `puntaje`. Solo lectura."""
    con = duckdb.connect(":memory:")
    try:
        con.execute(f"ATTACH '{Path(motor_db)}' AS motor (READ_ONLY)")
        con.execute(f"ATTACH '{Path(senales_db)}' AS senales (READ_ONLY)")
        fila = con.execute(
            "SELECT tema, evento_usgs_id FROM motor.puntaje WHERE grupo_id = ?", [grupo_id]
        ).fetchone()
        if fila is None:
            raise KeyError(f"grupo inexistente en puntaje: {grupo_id}")
        tema, evento_id = fila
        items = _noticias(con, grupo_id, max_noticias) + _indicadores(con, tema, reglas) + _evento(con, evento_id)
    finally:
        con.close()
    return {"grupo_id": grupo_id, "tema": tema, "items": items}
