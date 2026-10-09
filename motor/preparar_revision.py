#!/usr/bin/env python3
"""Prepare the human review sheets for the final metrics (TAR-034).

Writes three files under data/revision/ (read-only access to the databases):
  - validez_sustento.csv: every claim of the real fichas, with the cited news item,
    for a person to mark supported / not supported / ambiguous.
  - precision5_candidatos.csv: 20 candidate groups in a fixed shuffled order, WITHOUT
    scores or rank, so the reviewer picks a top 5 independently (blind).
  - precision5_clave.csv: the system's own ranking, kept apart until the reviewer is done.

The system ranking follows the interface brief: score descending, then U descending,
then grupo_id ascending.
"""
from __future__ import annotations

import csv
import json
import random
import sys
from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "data" / "revision"
N_CANDIDATOS = 20
SEMILLA = 7


def reclamos_reales(motor: duckdb.DuckDBPyConnection, fichas_jsonl: Path) -> list[dict]:
    """Claims of the five final fichas plus any other real ficha stored in the engine DB."""
    vistos, filas, finales = set(), [], set()
    for linea in fichas_jsonl.read_text(encoding="utf-8").splitlines():
        if not linea.strip():
            continue
        ficha = json.loads(linea)
        finales.add(ficha.get("id_caso") or ficha.get("grupo_id"))
        for a in ficha.get("afirmaciones", []):
            clave = (a["id_evidencia"], a["texto"])
            if clave not in vistos:
                vistos.add(clave)
                filas.append({"origen": "ficha final", **a})
    for id_caso, ficha_json in motor.execute("SELECT id_caso, ficha FROM fichas ORDER BY id_caso").fetchall():
        for a in json.loads(ficha_json).get("afirmaciones", []):
            clave = (a["id_evidencia"], a["texto"])
            if clave not in vistos:
                vistos.add(clave)
                origen = "borrador previo de ficha final" if id_caso in finales else "ficha generada en la app"
                filas.append({"origen": origen, "grupo_id": id_caso, **a})
    return filas


def escribir_validez(filas: list[dict], senales: duckdb.DuckDBPyConnection, ruta: Path) -> None:
    columnas = ["n", "origen", "afirmacion", "campo", "id_evidencia", "medio", "titulo_noticia",
                "fecha", "url", "veredicto", "motivo", "revisor"]
    with ruta.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columnas)
        w.writeheader()
        for i, a in enumerate(filas, 1):
            n = senales.execute(
                "SELECT medio, titulo, COALESCE(fecha_publicacion, fecha_deteccion), url "
                "FROM noticias WHERE id_noticia = ?", [a["id_evidencia"]]).fetchone()
            if n is None:  # official indicator (World Bank) instead of a news item
                n = senales.execute(
                    "SELECT 'Banco Mundial', indicador_nombre || ' ' || anio || ': ' || valor || ' ' || unidad, "
                    "CAST(anio AS VARCHAR), fuente_url FROM indicadores WHERE id_evidencia = ?",
                    [a["id_evidencia"]]).fetchone()
            medio, titulo, fecha, url = n if n else ("", "(noticia no encontrada)", "", "")
            w.writerow({"n": i, "origen": a["origen"], "afirmacion": a["texto"], "campo": a.get("campo", ""),
                        "id_evidencia": a["id_evidencia"], "medio": medio, "titulo_noticia": titulo,
                        "fecha": fecha, "url": url, "veredicto": "", "motivo": "", "revisor": ""})


def escribir_precision5(motor: duckdb.DuckDBPyConnection, ruta_cand: Path, ruta_clave: Path) -> None:
    filas = motor.execute(
        "SELECT p.grupo_id, p.tema, p.puntaje, p.\"U\", g.titulo_representativo, g.n_noticias, "
        "g.n_procedencias, g.fecha_max FROM puntaje p JOIN grupos g USING (grupo_id) "
        "ORDER BY p.puntaje DESC, p.\"U\" DESC, p.grupo_id ASC LIMIT ?", [N_CANDIDATOS]).fetchall()
    with ruta_clave.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["rango_sistema", "grupo_id", "tema", "puntaje"])
        for rango, r in enumerate(filas, 1):
            w.writerow([rango, r[0], r[1], r[2]])
    barajadas = list(filas)
    random.Random(SEMILLA).shuffle(barajadas)
    with ruta_cand.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["grupo_id", "tema", "titulo_representativo", "n_noticias", "n_fuentes", "fecha_max",
                    "seleccion_top5 (si/no)", "relevante_para_editor (si/no)", "motivo", "revisor"])
        for r in barajadas:
            w.writerow([r[0], r[1], r[4], r[5], r[6], r[7], "", "", "", ""])


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    motor = duckdb.connect(str(RAIZ / "data" / "motor.duckdb"), read_only=True)
    senales = duckdb.connect(str(RAIZ / "data" / "senales.duckdb"), read_only=True)
    filas = reclamos_reales(motor, RAIZ / "data" / "fichas.jsonl")
    escribir_validez(filas, senales, SALIDA / "validez_sustento.csv")
    escribir_precision5(motor, SALIDA / "precision5_candidatos.csv", SALIDA / "precision5_clave.csv")
    print(f"validez_sustento.csv: {len(filas)} afirmaciones reales (el reto pide al menos 30)")
    print(f"precision5_candidatos.csv: {N_CANDIDATOS} grupos sin puntaje ni rango")
    return 0


if __name__ == "__main__":
    sys.exit(main())
