#!/usr/bin/env python3
"""Clasifica titulares en los 6 temas del reto (TAR-007) + `otros` (abstención).

Dos métodos:
  - `embeddings`: zero-shot, similitud coseno del titular contra prototipos de tema
    (embedding de descripcion + semillas de motor/temas.yaml). Modelo multilingüe,
    cacheado en `modelos/` (ver `make modelos`).
  - `tfidf`: baseline, TfidfVectorizer (sklearn) ajustado sobre todos los titulares;
    prototipo de tema = TF-IDF de descripcion + semillas.

Ambos abstienen a `otros` cuando el mejor score < umbral_score o el margen con el
segundo mejor tema < umbral_margen (umbrales en motor/temas.yaml, propios por método).

Escribe en una base DuckDB SEPARADA de la de entrada (por defecto data/motor.duckdb,
nunca tocada por `make db`): tabla `clasificacion` (id_noticia, metodo, tema, score,
segundo_tema, margen, modelo) y `meta_clasificacion` (metadatos de la corrida).
Idempotente: si nada relevante cambió, no reconstruye (--forzar fuerza la corrida).
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from motor import embeddings as emb_mod  # noqa: E402

SCHEMA_VERSION = 1
RUTA_TEMAS_DEFECTO = Path(__file__).resolve().parent / "temas.yaml"


# --------------------------------------------------------------------------- temas.yaml

def cargar_temas(ruta: Path) -> tuple[dict, list[dict]]:
    """Lee motor/temas.yaml. Devuelve (parametros, lista de temas con su `texto` prototipo)."""
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    parametros = datos.get("parametros", {})
    temas = []
    for nombre, info in datos.get("temas", {}).items():
        descripcion = (info.get("descripcion") or "").strip()
        semillas = info.get("semillas") or []
        texto = descripcion + ". " + ". ".join(semillas)
        temas.append({
            "nombre": nombre,
            "descripcion": descripcion,
            "semillas": semillas,
            "texto": texto,
        })
    return parametros, temas


def hash_archivo(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


# --------------------------------------------------------------------------- clasificación genérica

def _top2(fila_scores: np.ndarray, nombres_temas: list[str]) -> tuple[str, float, str | None, float]:
    """Dado un vector de scores (uno por tema), devuelve (mejor_tema, score, segundo_tema, margen)."""
    orden = np.argsort(fila_scores)[::-1]
    mejor_idx = orden[0]
    mejor_tema = nombres_temas[mejor_idx]
    mejor_score = float(fila_scores[mejor_idx])
    if len(orden) > 1:
        segundo_idx = orden[1]
        segundo_tema = nombres_temas[segundo_idx]
        segundo_score = float(fila_scores[segundo_idx])
    else:
        segundo_tema = None
        segundo_score = 0.0
    margen = mejor_score - segundo_score
    return mejor_tema, mejor_score, segundo_tema, margen


def clasificar_matriz(
    matriz_similitud: np.ndarray,
    nombres_temas: list[str],
    umbral_score: float,
    umbral_margen: float,
) -> list[tuple[str, float, str | None, float]]:
    """matriz_similitud: (n_titulares, n_temas). Devuelve una lista de
    (tema, score, segundo_tema, margen) por titular; `tema` es `otros` si abstiene."""
    resultados = []
    for fila in matriz_similitud:
        tema, score, segundo_tema, margen = _top2(fila, nombres_temas)
        if score < umbral_score or margen < umbral_margen:
            tema = "otros"
        resultados.append((tema, score, segundo_tema, margen))
    return resultados


# --------------------------------------------------------------------------- método embeddings

def construir_prototipos_embeddings(encoder, temas: list[dict]) -> np.ndarray:
    """(n_temas, dim) normalizado L2, mismo orden que `temas`."""
    textos = [t["texto"] for t in temas]
    return emb_mod.codificar(encoder, textos)


def clasificar_embeddings(
    encoder,
    modelo: str,
    temas: list[dict],
    ids: list[str],
    titulos: list[str],
    umbral_score: float,
    umbral_margen: float,
    cache_dir: Path | None = None,
) -> list[tuple[str, float, str | None, float]]:
    # Resuelto en llamada (no como default fijo) para que un monkeypatch de
    # emb_mod.EMBEDDINGS_DIR (tests) surta efecto.
    if cache_dir is None:
        cache_dir = emb_mod.EMBEDDINGS_DIR
    nombres_temas = [t["nombre"] for t in temas]
    prototipos = construir_prototipos_embeddings(encoder, temas)

    vectores_por_id = emb_mod.embeddings_incrementales(encoder, modelo, ids, titulos, cache_dir)
    matriz = np.vstack([vectores_por_id[id_] for id_ in ids])

    matriz_similitud = matriz @ prototipos.T
    return clasificar_matriz(matriz_similitud, nombres_temas, umbral_score, umbral_margen)


# --------------------------------------------------------------------------- método tfidf

def construir_vectorizador_tfidf(titulos: list[str]):
    from sklearn.feature_extraction.text import TfidfVectorizer

    vectorizador = TfidfVectorizer(sublinear_tf=True, strip_accents="unicode", lowercase=True)
    vectorizador.fit(titulos)
    return vectorizador


def clasificar_tfidf(
    vectorizador,
    temas: list[dict],
    titulos: list[str],
    umbral_score: float,
    umbral_margen: float,
) -> list[tuple[str, float, str | None, float]]:
    from sklearn.metrics.pairwise import cosine_similarity

    nombres_temas = [t["nombre"] for t in temas]
    matriz_titulos = vectorizador.transform(titulos)
    matriz_temas = vectorizador.transform([t["texto"] for t in temas])
    matriz_similitud = cosine_similarity(matriz_titulos, matriz_temas)
    return clasificar_matriz(matriz_similitud, nombres_temas, umbral_score, umbral_margen)


# --------------------------------------------------------------------------- IO

def cargar_noticias(db_path: Path, desde: str | None) -> list[tuple[str, str, object, str | None]]:
    """Lee (id_noticia, titulo, fecha, origen) desde la base de origen, solo lectura.

    `fecha` es coalesce(fecha_deteccion, fecha_publicacion); `origen` se lee junto con
    el resto aunque la clasificación actual no lo use (queda disponible para análisis
    y para el futuro agrupamiento por evento). Omite titulares vacíos.
    """
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
            SELECT id_noticia, titulo, coalesce(fecha_deteccion, fecha_publicacion) AS fecha, origen
            FROM noticias WHERE {where} ORDER BY id_noticia
            """,
            parametros,
        ).fetchall()
    finally:
        con.close()
    return filas


def hash_entrada(ids: list[str], temas_sha256: str, parametros: dict, desde: str | None) -> str:
    h = hashlib.sha256()
    h.update(temas_sha256.encode())
    h.update(repr(sorted(parametros.items())).encode())
    h.update((desde or "").encode())
    h.update(str(len(ids)).encode())
    for id_ in ids:
        h.update(id_.encode())
    return h.hexdigest()


def sin_cambios(out_path: Path, entrada_hash: str) -> bool:
    if not out_path.exists():
        return False
    try:
        con = duckdb.connect(str(out_path), read_only=True)
    except duckdb.Error:
        return False
    try:
        fila = con.execute(
            "SELECT esquema_version, entrada_hash FROM meta_clasificacion LIMIT 1"
        ).fetchone()
    except duckdb.Error:
        return False
    finally:
        con.close()
    if fila is None:
        return False
    version, hash_guardado = fila
    return version == SCHEMA_VERSION and hash_guardado == entrada_hash


def escribir_resultados(
    out_path: Path,
    filas_clasificacion: list[tuple],
    modelo: str,
    parametros: dict,
    temas_sha256: str,
    entrada_hash: str,
) -> None:
    tmp_path = out_path.with_name(out_path.name + ".tmp")
    if tmp_path.exists():
        tmp_path.unlink()
    tmp_path.parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(tmp_path))
    try:
        con.execute("BEGIN TRANSACTION")
        con.execute("""
            CREATE TABLE clasificacion (
                id_noticia TEXT, metodo TEXT, tema TEXT, score DOUBLE,
                segundo_tema TEXT, margen DOUBLE, modelo TEXT
            )
        """)
        con.execute("""
            CREATE TABLE meta_clasificacion (
                esquema_version INTEGER, modelo TEXT, parametros TEXT,
                temas_sha256 TEXT, entrada_hash TEXT, built_at TIMESTAMP
            )
        """)
        con.executemany(
            "INSERT INTO clasificacion VALUES (?, ?, ?, ?, ?, ?, ?)", filas_clasificacion
        )
        con.execute(
            "INSERT INTO meta_clasificacion VALUES (?, ?, ?, ?, ?, ?)",
            [
                SCHEMA_VERSION, modelo, repr(sorted(parametros.items())),
                temas_sha256, entrada_hash, datetime.now(timezone.utc),
            ],
        )
        con.execute("COMMIT")
    finally:
        con.close()

    tmp_path.replace(out_path)


# --------------------------------------------------------------------------- resumen

def imprimir_resumen(
    ids: list[str],
    resultado_embeddings: list[tuple],
    resultado_tfidf: list[tuple],
    nombres_temas: list[str],
) -> None:
    from collections import Counter

    n = len(ids)
    print(f"\nTitulares clasificados: {n}")
    for nombre_metodo, resultado in (("embeddings", resultado_embeddings), ("tfidf", resultado_tfidf)):
        conteo = Counter(tema for tema, *_ in resultado)
        otros = conteo.get("otros", 0)
        print(f"\n[{nombre_metodo}] conteo por tema:")
        for tema in nombres_temas + ["otros"]:
            if conteo.get(tema):
                print(f"  - {tema}: {conteo[tema]}")
        print(f"  -> otros: {otros} ({100 * otros / n:.1f}%)" if n else "  -> otros: 0")

    coincidencias = sum(
        1 for a, b in zip(resultado_embeddings, resultado_tfidf) if a[0] == b[0]
    )
    print(f"\nAcuerdo entre métodos (mismo tema, incluyendo otros): {coincidencias}/{n} ({100 * coincidencias / n:.1f}%)" if n else "")


# --------------------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Clasifica titulares por tema (embeddings + baseline TF-IDF).")
    parser.add_argument("--forzar", action="store_true", help="reconstruye aunque nada haya cambiado")
    parser.add_argument("--desde", default=None, help="solo noticias con fecha >= YYYY-MM-DD")
    parser.add_argument("--db", default="data/senales.duckdb", help="base DuckDB de origen (solo lectura)")
    parser.add_argument("--out", default="data/motor.duckdb", help="base DuckDB de salida (derivada)")
    parser.add_argument("--temas", default=str(RUTA_TEMAS_DEFECTO), help="ruta a temas.yaml")
    args = parser.parse_args(argv)

    db_path = Path(args.db)
    out_path = Path(args.out)
    ruta_temas = Path(args.temas)

    if not db_path.exists():
        print(f"Error fatal: no existe la base de origen {db_path}", file=sys.stderr)
        return 1
    if not ruta_temas.exists():
        print(f"Error fatal: no existe {ruta_temas}", file=sys.stderr)
        return 1

    parametros, temas = cargar_temas(ruta_temas)
    temas_sha256 = hash_archivo(ruta_temas)
    nombres_temas = [t["nombre"] for t in temas]
    modelo = parametros.get("modelo", "paraphrase-multilingual-MiniLM-L12-v2")

    filas_noticias = cargar_noticias(db_path, args.desde)
    ids = [f[0] for f in filas_noticias]
    titulos = [f[1] for f in filas_noticias]
    # fecha y origen se leen pero no son necesarios para clasificar por tema (f[2], f[3]).

    if not ids:
        print("Sin noticias que clasificar (titular vacío o filtro --desde sin resultados).", file=sys.stderr)
        return 1

    entrada_hash = hash_entrada(ids, temas_sha256, parametros, args.desde)
    if not args.forzar and sin_cambios(out_path, entrada_hash):
        print(f"sin cambios: {out_path} ya refleja esta entrada ({entrada_hash[:12]}...)")
        return 0

    inicio = time.monotonic()

    umbral_score = float(parametros.get("umbral_score", 0.30))
    umbral_margen = float(parametros.get("umbral_margen", 0.03))
    umbral_score_tfidf = float(parametros.get("umbral_score_tfidf", 0.12))
    umbral_margen_tfidf = float(parametros.get("umbral_margen_tfidf", 0.02))

    encoder = emb_mod.cargar_modelo(modelo)
    resultado_embeddings = clasificar_embeddings(
        encoder, modelo, temas, ids, titulos, umbral_score, umbral_margen
    )

    vectorizador = construir_vectorizador_tfidf(titulos)
    resultado_tfidf = clasificar_tfidf(
        vectorizador, temas, titulos, umbral_score_tfidf, umbral_margen_tfidf
    )

    filas_clasificacion = []
    for id_, (tema, score, segundo, margen) in zip(ids, resultado_embeddings):
        filas_clasificacion.append((id_, "embeddings", tema, score, segundo, margen, modelo))
    for id_, (tema, score, segundo, margen) in zip(ids, resultado_tfidf):
        filas_clasificacion.append((id_, "tfidf", tema, score, segundo, margen, "tfidf"))

    escribir_resultados(out_path, filas_clasificacion, modelo, parametros, temas_sha256, entrada_hash)

    duracion = time.monotonic() - inicio
    print(f"Clasificación completa en {duracion:.2f}s -> {out_path}")
    imprimir_resumen(ids, resultado_embeddings, resultado_tfidf, nombres_temas)
    return 0


if __name__ == "__main__":
    sys.exit(main())
