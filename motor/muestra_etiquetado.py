#!/usr/bin/env python3
"""Genera una muestra de titulares para que un humano los etiquete A CIEGAS (TAR-007, T4).

Lee `noticias` de la base de origen (solo lectura, por defecto data/senales.duckdb),
toma una muestra aleatoria estratificada por mes (mismo numero de titulares por cada
mes presente en los datos, reproducible con --semilla) y escribe un CSV con columnas
`id_noticia, titulo, medio, fecha, tema_humano, notas`. `tema_humano` y `notas` quedan
vacias para que la persona que etiqueta las llene.

A PROPOSITO no incluye ningun resultado del modelo (ni tema, ni score, ni contraste):
la idea es que la persona etiquete sin saber que dijo el clasificador, para que
motor/evaluar.py pueda comparar contra una etiqueta independiente.
"""
from __future__ import annotations

import argparse
import csv
import random
import sys
from pathlib import Path

import duckdb

RUTA_OUT_DEFECTO = "data/etiquetas/muestra_etiquetado.csv"
TEMAS_VALIDOS = [
    "economia", "logistica_canal", "turismo",
    "servicios_publicos", "eventos_naturales", "regulacion", "otros",
]

LEEME_TEXTO = """\
# Como etiquetar `muestra_etiquetado.csv`

Este archivo tiene una muestra aleatoria de titulares reales (estratificada por mes,
para no concentrarse en un solo periodo) para que una persona los clasifique A MANO,
SIN mirar lo que dijo el clasificador automatico. Esa etiqueta independiente es la que
usa `motor/evaluar.py` para medir macro-F1 y las demas metricas del reto.

## Como etiquetar

1. Abrir `muestra_etiquetado.csv` (columnas: `id_noticia, titulo, medio, fecha,
   tema_humano, notas`). No tiene ninguna columna del modelo (ni tema ni score):
   es intencional, para que la etiqueta sea independiente.
2. Para cada fila, llenar `tema_humano` con UNO de estos valores (exactos, en
   minusculas):
   - `economia`
   - `logistica_canal`
   - `turismo`
   - `servicios_publicos`
   - `eventos_naturales`
   - `regulacion`
   - `otros` (si el titular no encaja claramente en ninguno de los 6 temas de arriba)
3. Un solo tema por titular (el que mejor encaje; no hay etiquetas multiples).
4. `notas` es opcional: usarla solo para dejar un comentario corto (por ejemplo, si
   dudaste entre dos temas).
5. Etiquetar SIN mirar la salida del clasificador (no abrir `data/motor.duckdb` ni los
   reportes de clasificacion mientras se etiqueta). Si ya viste esos resultados antes,
   avisa igual: `evaluar.py` lo va a usar de todas formas, pero es mejor saberlo.
6. Etiquetar de forma independiente: no discutir las respuestas con otra persona que
   tambien vaya a etiquetar la misma muestra, hasta que ambas terminen.
7. Al terminar, agregar al final de este archivo (o en un commit aparte) quien
   etiqueto y la fecha, por ejemplo: `Etiquetado por: <nombre> el <YYYY-MM-DD>`.

## Siguiente paso

Con el CSV ya etiquetado, correr `make evaluar` (o
`python motor/evaluar.py --etiquetas data/etiquetas/muestra_etiquetado.csv`) para
generar el reporte de macro-F1, precision/recall por tema, matriz de confusion y tasa
de abstencion de cada metodo (embeddings y tfidf).
"""


def muestrear_estratificado_por_mes(
    filas: list[tuple], n: int, semilla: int
) -> list[tuple]:
    """`filas`: (id_noticia, titulo, medio, fecha). Reparte `n` entre los meses
    presentes (mismo cupo por mes, sobrante a los primeros meses en orden cronologico),
    y dentro de cada mes toma una muestra aleatoria sin reemplazo (semillada, por lo
    tanto reproducible). Si un mes tiene menos candidatos que su cupo, toma todos los
    que haya (la muestra final puede quedar por debajo de `n`)."""
    por_mes: dict[str, list[tuple]] = {}
    for fila in filas:
        fecha = fila[3]
        mes = str(fecha)[:7] if fecha is not None else "sin-fecha"
        por_mes.setdefault(mes, []).append(fila)

    meses = sorted(por_mes.keys())
    if not meses:
        return []

    # Orden determinista dentro de cada mes (por id_noticia) antes de muestrear: el
    # resultado de random.Random(semilla).sample depende del orden de la lista.
    for mes in meses:
        por_mes[mes].sort(key=lambda f: f[0])

    num_meses = len(meses)
    cupo_base = n // num_meses
    sobrante = n % num_meses

    rng = random.Random(semilla)
    seleccion: list[tuple] = []
    for i, mes in enumerate(meses):
        cupo = cupo_base + (1 if i < sobrante else 0)
        candidatos = por_mes[mes]
        elegidos = rng.sample(candidatos, k=min(cupo, len(candidatos)))
        seleccion.extend(elegidos)
    return seleccion


def cargar_noticias(db_path: Path, desde: str | None) -> list[tuple]:
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        condiciones = ["titulo IS NOT NULL", "trim(titulo) != ''"]
        parametros: list = []
        if desde:
            condiciones.append("coalesce(fecha_deteccion, fecha_publicacion) >= ?")
            parametros.append(desde)
        where = " AND ".join(condiciones)
        filas = con.execute(
            f"""
            SELECT id_noticia, titulo, medio, coalesce(fecha_deteccion, fecha_publicacion) AS fecha
            FROM noticias WHERE {where} ORDER BY id_noticia
            """,
            parametros,
        ).fetchall()
    finally:
        con.close()
    return filas


def escribir_muestra(ruta_out: Path, filas: list[tuple]) -> None:
    ruta_out.parent.mkdir(parents=True, exist_ok=True)
    with ruta_out.open("w", encoding="utf-8", newline="") as f:
        escritor = csv.writer(f)
        escritor.writerow(["id_noticia", "titulo", "medio", "fecha", "tema_humano", "notas"])
        for id_noticia, titulo, medio, fecha in filas:
            fecha_str = str(fecha)[:10] if fecha is not None else ""
            escritor.writerow([id_noticia, titulo, medio or "", fecha_str, "", ""])


def escribir_leeme(ruta_leeme: Path) -> None:
    ruta_leeme.parent.mkdir(parents=True, exist_ok=True)
    ruta_leeme.write_text(LEEME_TEXTO, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Genera una muestra estratificada por mes para etiquetar a ciegas."
    )
    parser.add_argument("--n", type=int, default=100, help="tamano de la muestra (defecto 100)")
    parser.add_argument("--desde", default=None, help="solo noticias con fecha >= YYYY-MM-DD")
    parser.add_argument("--semilla", type=int, default=7, help="semilla para reproducibilidad")
    parser.add_argument("--db", default="data/senales.duckdb", help="base DuckDB de origen (solo lectura)")
    parser.add_argument("--out", default=RUTA_OUT_DEFECTO, help="ruta del CSV de salida")
    args = parser.parse_args(argv)

    db_path = Path(args.db)
    out_path = Path(args.out)

    if not db_path.exists():
        print(f"Error fatal: no existe la base de origen {db_path}", file=sys.stderr)
        return 1

    filas = cargar_noticias(db_path, args.desde)
    if not filas:
        print("Sin noticias para muestrear (titular vacío o filtro --desde sin resultados).", file=sys.stderr)
        return 1

    seleccion = muestrear_estratificado_por_mes(filas, args.n, args.semilla)
    escribir_muestra(out_path, seleccion)
    ruta_leeme = out_path.parent / "LEEME_etiquetado.md"
    escribir_leeme(ruta_leeme)

    meses = sorted({str(f[3])[:7] for f in seleccion if f[3] is not None})
    print(f"Muestra escrita en {out_path}: {len(seleccion)} titulares, {len(meses)} meses.")
    if len(seleccion) < args.n:
        print(
            f"Nota: se pidieron {args.n} pero solo hay {len(seleccion)} disponibles "
            "repartidos entre los meses presentes.",
            file=sys.stderr,
        )
    print(f"Instrucciones para etiquetar en {ruta_leeme}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
