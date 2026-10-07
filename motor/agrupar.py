#!/usr/bin/env python3
"""Agrupa titulares que hablan del mismo evento (T3, TAR-007).

Entrada: `noticias` en la base de origen (solo lectura, por defecto data/senales.duckdb).
Salida: tablas `grupos`, `grupo_noticias` y `meta_agrupacion` en una base DuckDB derivada
(por defecto data/motor.duckdb, la misma que usa motor/clasificar.py para `clasificacion` /
`meta_clasificacion`; este script solo reemplaza SUS propias tablas, nunca esas otras).

Algoritmo (pensado para correr en CPU en un par de minutos con ~30k titulares, sin
construir nunca una matriz 30k x 30k):

  1. Ordena los titulares por fecha de evento (fecha_publicacion si existe, si no
     fecha_deteccion) y calcula sus embeddings (reusa la cache de motor/embeddings.py:
     solo codifica los ids que falten).
  2. Etapa 1 (candidatos): recorre la lista ordenada en bloques (BLOQUE titulares);
     para cada bloque multiplica sus vectores contra los vectores de una ventana de
     fechas vecinas (+-ventana_dias) con un único matmul de numpy, y une con
     union-find los pares con similitud coseno >= umbral y diferencia de fecha dentro
     de la ventana. Esto nunca compara dos titulares que ya sabemos lejos en el
     tiempo, y evita la matriz completa.
  3. Etapa 2 (partición exacta dentro de cada componente): un componente conexo de
     union-find puede encadenar A~B~C aunque A y C no se parezcan (A enlaza con B, B
     con C, pero el coseno A-C es bajo: "union-find puro" encadenaría los tres). Para
     evitarlo, cada componente (normalmente chico: docenas de titulares, nunca miles)
     se re-particiona con clustering aglomerativo de enlace promedio (average-linkage):
     empieza con cada titular en su propio clúster y va fusionando el par de clústeres
     con mayor similitud promedio entre todos sus miembros, mientras esa similitud
     promedio sea >= umbral. Esto es más fiel al enunciado ("average-linkage dentro de
     los componentes") que el criterio alternativo de podar por distancia al centroide,
     y en la práctica evita el encadenamiento sin necesitar un segundo umbral.
  4. Etapa 3 (tope de duración): un grupo real no dura meses. Aun sin encadenamiento
     A~B~C, una serie de titulares casi idénticos que se repite todos los días (un
     segmento fijo como "Clima en Panamá" o "Resultados de béisbol") queda enlazada de
     a pares consecutivos por la ventana de ±ventana_dias, y la etapa 2 no la separa
     porque todos los pares vecinos sí son parecidos entre sí: el componente entero
     puede terminar abarcando semanas o meses. `--max-span-dias` (por defecto igual a
     la ventana, 3 días) pone un techo duro: ningún grupo final puede abarcar más de
     esos días entre su miembro más viejo y el más nuevo. Se aplica recorriendo cada
     grupo ya formado en orden de fecha y cortando un subgrupo nuevo apenas un miembro
     queda a más de `max_span_dias` del primero del subgrupo vigente (barrido simple,
     determinista, sin volver a tocar similitud coseno).

Procedencia: la clave de procedencia de un titular es su dominio (`medio`), salvo que
el título o la URL traigan una marca de agencia/cable (EFE, AFP, AP, Reuters, Europa
Press/EP, Sputnik, DPA, ANSA) como palabra suelta (p. ej. "| AFP", "(EFE)", un slug de
URL) -- en ese caso la procedencia es `agencia:<NOMBRE>` sin importar qué medio la
publicó (CU-03: una nota de agencia repetida por varios medios cuenta como UNA sola
procedencia). El detector es deliberadamente chico y puede tener falsos positivos
raros (p. ej. un acrónimo de 2-3 letras que coincida con una marca de agencia como
palabra suelta); en este dataset (30154 titulares, ~150 de fuera de tvn-2.com) no se
observó ningún caso real de marca de agencia en título o URL, así que la colapsación
por agencia casi no se ejerce en la corrida real: la inmensa mayoría de "repeticiones"
son el mismo medio (tvn-2.com) cubriendo su propio evento en varias secciones, que es
la repetición honesta que T02/CU-03 piden no contar como corroboración extra.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from motor import embeddings as emb_mod  # noqa: E402

SCHEMA_VERSION = 1
BLOQUE = 2000  # tamaño de bloque para la etapa 1 (ver docstring del módulo)
MARGEN_SPLIT_CENTROIDE = 0.10  # ver nota en `clusterizar_average_link` (no se usa para
# cortar por centroide; se documenta porque el enunciado lo ofrece como alternativa).

# --------------------------------------------------------------------------- procedencia

# Marcas de agencia/cable reconocidas como palabra suelta (no subcadena: "jefe" no debe
# matchear "EFE"). "EP" y "EUROPA PRESS" colapsan al mismo nombre canónico.
_AGENCIAS = {
    "EFE": "EFE",
    "AFP": "AFP",
    "AP": "AP",
    "REUTERS": "REUTERS",
    "EUROPA PRESS": "EUROPA_PRESS",
    "EP": "EUROPA_PRESS",
    "SPUTNIK": "SPUTNIK",
    "DPA": "DPA",
    "ANSA": "ANSA",
}
# Las de dos palabras van primero (si matchean, ya no hace falta mirar las de una).
_PATRONES_AGENCIA = [
    (nombre, re.compile(r"(?<![A-Za-z0-9])" + re.escape(marca) + r"(?![A-Za-z0-9])", re.IGNORECASE))
    for marca, nombre in sorted(_AGENCIAS.items(), key=lambda kv: -len(kv[0]))
]


def procedencia(medio: str | None, titulo: str | None, url: str | None) -> str:
    """Clave de procedencia: dominio del medio, o `agencia:<NOMBRE>` si el título o la
    URL traen una marca de agencia como palabra suelta (ver `_PATRONES_AGENCIA`)."""
    texto = f"{titulo or ''} {url or ''}"
    for nombre, patron in _PATRONES_AGENCIA:
        if patron.search(texto):
            return f"agencia:{nombre}"
    return medio or "desconocido"


# --------------------------------------------------------------------------- union-find

class UnionFind:
    def __init__(self, n: int):
        self.padre = list(range(n))
        self.rango = [0] * n

    def encontrar(self, x: int) -> int:
        raiz = x
        while self.padre[raiz] != raiz:
            raiz = self.padre[raiz]
        while self.padre[x] != raiz:
            self.padre[x], x = raiz, self.padre[x]
        return raiz

    def unir(self, a: int, b: int) -> None:
        ra, rb = self.encontrar(a), self.encontrar(b)
        if ra == rb:
            return
        if self.rango[ra] < self.rango[rb]:
            ra, rb = rb, ra
        self.padre[rb] = ra
        if self.rango[ra] == self.rango[rb]:
            self.rango[ra] += 1


def _buscar_candidatos(
    dias: np.ndarray, vectores: np.ndarray, ventana_dias: float, umbral: float
) -> UnionFind:
    """Etapa 1: enlaza (union-find) pares con coseno >= umbral y |diferencia de fecha|
    <= ventana_dias, recorriendo `dias`/`vectores` (ya ordenados por fecha) en bloques
    para no construir nunca la matriz completa n x n."""
    n = len(dias)
    uf = UnionFind(n)
    i0 = 0
    while i0 < n:
        i1 = min(i0 + BLOQUE, n)
        lo = int(np.searchsorted(dias, dias[i0] - ventana_dias, side="left"))
        hi = int(np.searchsorted(dias, dias[i1 - 1] + ventana_dias, side="right"))
        sims = vectores[i0:i1] @ vectores[lo:hi].T

        filas_globales = np.arange(i0, i1)[:, None]
        columnas_globales = np.arange(lo, hi)[None, :]
        dif_fechas = np.abs(dias[i0:i1][:, None] - dias[lo:hi][None, :])
        mascara = (sims >= umbral) & (dif_fechas <= ventana_dias) & (columnas_globales > filas_globales)

        filas_local, columnas_local = np.nonzero(mascara)
        for fl, cl in zip(filas_local, columnas_local):
            uf.unir(i0 + int(fl), lo + int(cl))

        i0 = i1
    return uf


def clusterizar_average_link(vectores_componente: np.ndarray, umbral: float) -> list[list[int]]:
    """Etapa 2: reparte un componente conexo (vectores ya indexados localmente 0..m-1)
    en clústeres por enlace promedio (average-linkage), para no encadenar A~B~C cuando
    A y C son distintos entre sí aunque ambos estén enlazados a través de B. Fusiona
    siempre el par de clústeres con mayor similitud promedio entre TODOS sus miembros,
    mientras esa similitud promedio sea >= umbral. m es, en la práctica, chico (docenas
    de titulares como mucho), así que el costo O(m^3) del agrupamiento es irrelevante."""
    m = vectores_componente.shape[0]
    if m <= 1:
        return [[i] for i in range(m)]

    sim = vectores_componente @ vectores_componente.T
    clusters = [[i] for i in range(m)]
    while len(clusters) > 1:
        mejor_par = None
        mejor_promedio = -1.0
        for a in range(len(clusters)):
            for b in range(a + 1, len(clusters)):
                valores = sim[np.ix_(clusters[a], clusters[b])]
                promedio = float(valores.mean())
                if promedio > mejor_promedio:
                    mejor_promedio = promedio
                    mejor_par = (a, b)
        if mejor_par is None or mejor_promedio < umbral:
            break
        a, b = mejor_par
        clusters[a] = clusters[a] + clusters[b]
        del clusters[b]
    return clusters


def agrupar_por_similitud(
    dias: np.ndarray, vectores: np.ndarray, ventana_dias: float, umbral: float
) -> list[list[int]]:
    """Devuelve la lista final de grupos como listas de índices globales (posiciones en
    el arreglo ordenado por fecha que se pasó)."""
    uf = _buscar_candidatos(dias, vectores, ventana_dias, umbral)

    componentes: dict[int, list[int]] = {}
    for i in range(len(dias)):
        componentes.setdefault(uf.encontrar(i), []).append(i)

    grupos: list[list[int]] = []
    for miembros in componentes.values():
        if len(miembros) == 1:
            grupos.append(miembros)
            continue
        sub_vectores = vectores[miembros]
        for cluster_local in clusterizar_average_link(sub_vectores, umbral):
            grupos.append([miembros[i] for i in cluster_local])
    return grupos


def limitar_span_grupos(
    indices_grupos: list[list[int]], dias: np.ndarray, max_span_dias: float
) -> list[list[int]]:
    """Etapa 3: parte cada grupo ya formado para que ningún subgrupo resultante abarque
    más de `max_span_dias` entre su miembro más viejo y el más nuevo (ver docstring del
    módulo). Recorre los índices del grupo en orden de fecha y corta un subgrupo nuevo
    apenas un miembro queda a más de `max_span_dias` del primero del subgrupo vigente;
    es un barrido simple y determinista, no vuelve a mirar similitud coseno. Grupos de
    tamaño <= 1 no se pueden partir y se devuelven tal cual."""
    resultado: list[list[int]] = []
    for indices in indices_grupos:
        if len(indices) <= 1:
            resultado.append(indices)
            continue
        orden = sorted(indices, key=lambda i: dias[i])
        subgrupo = [orden[0]]
        inicio = dias[orden[0]]
        for i in orden[1:]:
            if dias[i] - inicio > max_span_dias:
                resultado.append(subgrupo)
                subgrupo = [i]
                inicio = dias[i]
            else:
                subgrupo.append(i)
        resultado.append(subgrupo)
    return resultado


# --------------------------------------------------------------------------- IO

def cargar_noticias(db_path: Path, desde: str | None) -> list[tuple[str, str, str, str, object]]:
    """Lee (id_noticia, titulo, url, medio, fecha_evento) desde la base de origen, solo
    lectura. `fecha_evento` es coalesce(fecha_publicacion, fecha_deteccion) (la
    publicación, si existe; si no, el lastmod del sitemap). Omite titulares vacíos o
    sin fecha utilizable (no se los puede ubicar en el tiempo para agrupar)."""
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        condiciones = [
            "titulo IS NOT NULL", "trim(titulo) != ''",
            "coalesce(fecha_publicacion, fecha_deteccion) IS NOT NULL",
        ]
        parametros: list = []
        if desde:
            condiciones.append("coalesce(fecha_publicacion, fecha_deteccion) >= ?")
            parametros.append(desde)
        where = " AND ".join(condiciones)
        filas = con.execute(
            f"""
            SELECT id_noticia, titulo, url, medio,
                   coalesce(fecha_publicacion, fecha_deteccion) AS fecha_evento
            FROM noticias WHERE {where} ORDER BY fecha_evento, id_noticia
            """,
            parametros,
        ).fetchall()
    finally:
        con.close()
    return filas


def hash_entrada(ids: list[str], parametros: dict, desde: str | None, modelo: str) -> str:
    h = hashlib.sha256()
    h.update(modelo.encode())
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
            "SELECT esquema_version, entrada_hash FROM meta_agrupacion LIMIT 1"
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
    filas_grupos: list[tuple],
    filas_grupo_noticias: list[tuple],
    modelo: str,
    parametros: dict,
    entrada_hash: str,
) -> None:
    """Escribe `grupos`, `grupo_noticias` y `meta_agrupacion` en `out_path` dentro de una
    sola transacción, sin tocar ninguna otra tabla que ya exista en esa base (p. ej.
    `clasificacion` / `meta_clasificacion` de motor/clasificar.py). A diferencia de
    clasificar.py/cargar_db.py no se puede reemplazar el archivo entero (compartido con
    otras tablas ajenas); la atomicidad la da la transacción de DuckDB: si el proceso
    muere a mitad de camino, al reabrir la base la transacción no confirmada no dejó
    rastro."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(out_path))
    try:
        con.execute("BEGIN TRANSACTION")
        con.execute("DROP TABLE IF EXISTS grupo_noticias")
        con.execute("DROP TABLE IF EXISTS grupos")
        con.execute("DROP TABLE IF EXISTS meta_agrupacion")
        con.execute("""
            CREATE TABLE grupos (
                grupo_id TEXT, n_noticias INTEGER, n_procedencias INTEGER,
                procedencias TEXT, fecha_min TIMESTAMP, fecha_max TIMESTAMP,
                titulo_representativo TEXT, corroboracion INTEGER, es_repeticion BOOLEAN
            )
        """)
        con.execute("""
            CREATE TABLE grupo_noticias (
                grupo_id TEXT, id_noticia TEXT, procedencia TEXT, similitud_al_centroide DOUBLE
            )
        """)
        con.execute("""
            CREATE TABLE meta_agrupacion (
                esquema_version INTEGER, modelo TEXT, parametros TEXT,
                entrada_hash TEXT, built_at TIMESTAMP
            )
        """)
        con.executemany("INSERT INTO grupos VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", filas_grupos)
        con.executemany(
            "INSERT INTO grupo_noticias VALUES (?, ?, ?, ?)", filas_grupo_noticias
        )
        con.execute(
            "INSERT INTO meta_agrupacion VALUES (?, ?, ?, ?, ?)",
            [
                SCHEMA_VERSION, modelo, repr(sorted(parametros.items())),
                entrada_hash, datetime.now(timezone.utc),
            ],
        )
        con.execute("COMMIT")
    finally:
        con.close()


# --------------------------------------------------------------------------- construcción de grupos

def construir_grupos(
    ids: list[str],
    titulos: list[str],
    urls: list[str],
    medios: list[str],
    fechas: list,
    vectores: np.ndarray,
    indices_grupos: list[list[int]],
) -> tuple[list[tuple], list[tuple]]:
    """A partir de los índices por grupo (posiciones en los arreglos ordenados por
    fecha), arma las filas de `grupos` y `grupo_noticias`."""
    filas_grupos: list[tuple] = []
    filas_grupo_noticias: list[tuple] = []

    for indices in indices_grupos:
        ids_grupo = [ids[i] for i in indices]
        procedencias_por_indice = {i: procedencia(medios[i], titulos[i], urls[i]) for i in indices}
        procedencias_distintas = sorted(set(procedencias_por_indice.values()))
        n_noticias = len(indices)
        n_procedencias = len(procedencias_distintas)

        sub_vectores = vectores[indices]
        centroide = sub_vectores.mean(axis=0)
        norma = np.linalg.norm(centroide)
        if norma > 0:
            centroide = centroide / norma
        similitudes = sub_vectores @ centroide

        idx_representativo_local = int(np.argmax(similitudes))
        idx_representativo = indices[idx_representativo_local]

        fechas_grupo = [fechas[i] for i in indices]
        grupo_id = "G-" + hashlib.sha256(min(ids_grupo).encode()).hexdigest()[:12]

        filas_grupos.append((
            grupo_id, n_noticias, n_procedencias, "; ".join(procedencias_distintas),
            min(fechas_grupo), max(fechas_grupo), titulos[idx_representativo],
            n_procedencias, n_noticias > n_procedencias,
        ))
        for local, i in enumerate(indices):
            filas_grupo_noticias.append((
                grupo_id, ids[i], procedencias_por_indice[i], float(similitudes[local]),
            ))

    return filas_grupos, filas_grupo_noticias


# --------------------------------------------------------------------------- resumen

def imprimir_resumen(filas_grupos: list[tuple], filas_grupo_noticias: list[tuple]) -> None:
    from collections import Counter

    n_grupos = len(filas_grupos)
    print(f"\nGrupos formados: {n_grupos}")
    if n_grupos == 0:
        return

    tamanios = Counter(n for _, n, *_ in filas_grupos)
    grupos_mult = sum(n for tam, n in tamanios.items() if tam >= 2)
    print(f"Grupos con n_noticias >= 2: {grupos_mult}")
    print("Distribución de tamaños (n_noticias -> cantidad de grupos):")
    for tam in sorted(tamanios):
        print(f"  - {tam}: {tamanios[tam]}")

    mas_grande = max(filas_grupos, key=lambda g: g[1])
    print(
        f"\nGrupo más grande: \"{mas_grande[6]}\" "
        f"(n_noticias={mas_grande[1]}, n_procedencias={mas_grande[2]})"
    )

    promedio_corroboracion = sum(g[7] for g in filas_grupos) / n_grupos
    print(f"Corroboración promedio (n_procedencias por grupo): {promedio_corroboracion:.2f}")

    con_2_mas_procedencias = sum(1 for g in filas_grupos if g[2] >= 2)
    print(f"Grupos con n_procedencias >= 2 (corroborados por más de una fuente): {con_2_mas_procedencias}")

    grandes = sorted((g for g in filas_grupos if g[1] >= 2), key=lambda g: -g[1])
    print(f"\nMuestra de hasta 10 grupos con n_noticias >= 2:")
    for g in grandes[:10]:
        print(f"  - [{g[0]}] n_noticias={g[1]} n_procedencias={g[2]} procedencias={g[3]!r} :: \"{g[6]}\"")

    singulares = [g for g in filas_grupos if g[1] == 1]
    print(f"\nMuestra de hasta 5 grupos de tamaño 1:")
    for g in singulares[:5]:
        print(f"  - [{g[0]}] :: \"{g[6]}\"")


# --------------------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Agrupa titulares por evento (embeddings + ventana de tiempo).")
    parser.add_argument("--forzar", action="store_true", help="reconstruye aunque nada haya cambiado")
    parser.add_argument("--ventana-dias", type=float, default=3.0, help="ventana de tiempo (±días) para comparar titulares")
    parser.add_argument("--umbral", type=float, default=0.80, help="similitud coseno mínima para enlazar dos titulares")
    parser.add_argument(
        "--max-span-dias", type=float, default=3.0,
        help="tope duro de duración de un grupo: ningún grupo abarca más de estos días "
             "entre su miembro más viejo y el más nuevo (por defecto, igual a la ventana)",
    )
    parser.add_argument("--desde", default=None, help="solo noticias con fecha de evento >= YYYY-MM-DD")
    parser.add_argument("--db", default="data/senales.duckdb", help="base DuckDB de origen (solo lectura)")
    parser.add_argument("--out", default="data/motor.duckdb", help="base DuckDB de salida (derivada)")
    parser.add_argument("--modelo", default="paraphrase-multilingual-MiniLM-L12-v2", help="modelo de embeddings")
    args = parser.parse_args(argv)

    db_path = Path(args.db)
    out_path = Path(args.out)

    if not db_path.exists():
        print(f"Error fatal: no existe la base de origen {db_path}", file=sys.stderr)
        return 1

    filas_noticias = cargar_noticias(db_path, args.desde)
    ids = [f[0] for f in filas_noticias]
    titulos = [f[1] for f in filas_noticias]
    urls = [f[2] for f in filas_noticias]
    medios = [f[3] for f in filas_noticias]
    fechas = [f[4] for f in filas_noticias]

    if not ids:
        print("Sin noticias que agrupar (titular vacío, sin fecha, o filtro --desde sin resultados).", file=sys.stderr)
        return 1

    parametros = {
        "ventana_dias": args.ventana_dias, "umbral": args.umbral, "max_span_dias": args.max_span_dias,
    }
    entrada_hash = hash_entrada(ids, parametros, args.desde, args.modelo)
    if not args.forzar and sin_cambios(out_path, entrada_hash):
        print(f"sin cambios: {out_path} ya refleja esta entrada ({entrada_hash[:12]}...)")
        return 0

    inicio = time.monotonic()

    encoder = emb_mod.cargar_modelo(args.modelo)
    # cache_dir se resuelve aqui (no como default fijo del parametro) para que un
    # monkeypatch de emb_mod.EMBEDDINGS_DIR en los tests surta efecto (ver misma nota
    # en motor/clasificar.py).
    vectores_por_id = emb_mod.embeddings_incrementales(
        encoder, args.modelo, ids, titulos, cache_dir=emb_mod.EMBEDDINGS_DIR
    )
    vectores = np.vstack([vectores_por_id[id_] for id_ in ids]).astype(np.float32)

    # Fechas como float (días desde época) para poder restar/comparar con ventana_dias.
    dias = np.array([
        (f - datetime(1970, 1, 1)).total_seconds() / 86400.0 for f in fechas
    ])

    indices_grupos = agrupar_por_similitud(dias, vectores, args.ventana_dias, args.umbral)
    indices_grupos = limitar_span_grupos(indices_grupos, dias, args.max_span_dias)
    filas_grupos, filas_grupo_noticias = construir_grupos(
        ids, titulos, urls, medios, fechas, vectores, indices_grupos
    )

    escribir_resultados(out_path, filas_grupos, filas_grupo_noticias, args.modelo, parametros, entrada_hash)

    duracion = time.monotonic() - inicio
    print(f"Agrupación completa en {duracion:.2f}s ({len(ids)} titulares, {len(filas_grupos)} grupos) -> {out_path}")
    imprimir_resumen(filas_grupos, filas_grupo_noticias)
    return 0


if __name__ == "__main__":
    sys.exit(main())
