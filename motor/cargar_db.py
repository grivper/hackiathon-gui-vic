#!/usr/bin/env python3
"""Carga el snapshot procesado (data/processed/*) en un espejo local de DuckDB.

Valida fechas y campos obligatorios (T01): las filas con fecha no parseable o sin un
campo obligatorio van a la tabla `rechazados` y quedan fuera de la tabla principal;
los nulos en campos opcionales se conservan. La carga nunca aborta por filas malas.

Genera además un reporte de calidad (data/reporte_calidad.md por defecto, junto a la
base de datos) y es idempotente: si la base existe y el hash del manifest no cambió,
no reconstruye nada (--forzar fuerza la reconstrucción).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

import duckdb

SCHEMA_VERSION = 1

# Columnas obligatorias por tabla (ver data/diccionario.md).
NOTICIAS_OBLIGATORIAS = ("id_noticia", "url")
NOTICIAS_FECHAS = ("fecha_publicacion", "fecha_deteccion", "fecha_extraccion")
INDICADORES_OBLIGATORIAS = ("id_evidencia",)
INDICADORES_FECHAS = ("fecha_extraccion",)
EVENTOS_OBLIGATORIAS = ("id",)
EVENTOS_FECHAS = ("time", "updated")
EXCLUIDOS_FECHAS = ("fecha_publicacion", "fecha_deteccion")

# Parámetros de seguimiento que no identifican contenido distinto.
_PARAMS_UTM = {"fbclid"}


def parse_fecha(valor: str | None) -> tuple[datetime | None, str | None]:
    """Parsea una fecha ISO-8601 UTC. Vacío -> (None, None): es válido, no un error."""
    if valor is None or valor.strip() == "":
        return None, None
    texto = valor.strip()
    try:
        dt = datetime.fromisoformat(texto)
    except ValueError:
        return None, f"fecha no parseable: {texto!r}"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt, None


def normalizar_url(url: str) -> str:
    """Normaliza una URL para detectar duplicados (sin esquema, www, utm_*/fbclid, barra final)."""
    if not url:
        return ""
    partes = urlsplit(url.strip())
    netloc = partes.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    query = [
        (k, v) for k, v in parse_qsl(partes.query, keep_blank_values=True)
        if not k.lower().startswith("utm_") and k.lower() not in _PARAMS_UTM
    ]
    path = partes.path.rstrip("/")
    return urlunsplit(("", netloc, path, urlencode(query), ""))


def _vacio_a_none(valor: str | None) -> str | None:
    if valor is None:
        return None
    valor = valor.strip()
    return valor if valor != "" else None


def _a_entero(valor: str | None) -> int | None:
    valor = _vacio_a_none(valor)
    return int(valor) if valor is not None else None


def _a_flotante(valor: str | None) -> float | None:
    valor = _vacio_a_none(valor)
    return float(valor) if valor is not None else None


def leer_csv(ruta: Path) -> list[dict]:
    with ruta.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def validar_y_cargar(
    filas: list[dict],
    tabla: str,
    obligatorias: tuple[str, ...],
    fechas: tuple[str, ...],
    id_campo: str | None,
    rechazados: list[dict],
) -> list[dict]:
    """Valida filas crudas: separa las inválidas a `rechazados`, conserva nulos opcionales."""
    buenas: list[dict] = []
    for idx, fila in enumerate(filas):
        errores: list[tuple[str, str]] = []
        for campo in obligatorias:
            if not (fila.get(campo) or "").strip():
                errores.append((campo, "campo obligatorio vacío"))
        fechas_parseadas: dict[str, datetime | None] = {}
        for campo in fechas:
            dt, err = parse_fecha(fila.get(campo))
            if err:
                errores.append((campo, err))
            fechas_parseadas[campo] = dt
        if errores:
            for campo, motivo in errores:
                rechazados.append({
                    "tabla": tabla,
                    "fila": idx,
                    "id": fila.get(id_campo) if id_campo else None,
                    "campo": campo,
                    "motivo": motivo,
                })
            continue
        fila_limpia = dict(fila)
        for campo in fechas:
            fila_limpia[campo] = fechas_parseadas[campo]
        for campo, valor in fila_limpia.items():
            if campo not in fechas and isinstance(valor, str):
                fila_limpia[campo] = _vacio_a_none(valor)
        buenas.append({"_fila": idx, **fila_limpia})
    return buenas


def deduplicar_por_id(
    filas: list[dict], tabla: str, id_campo: str, rechazados: list[dict]
) -> tuple[list[dict], int]:
    """Conserva la primera fila por id; las siguientes van a rechazados. Devuelve (filas, duplicados)."""
    vistos: set[str] = set()
    resultado: list[dict] = []
    duplicados = 0
    for fila in filas:
        valor_id = fila[id_campo]
        if valor_id in vistos:
            duplicados += 1
            rechazados.append({
                "tabla": tabla,
                "fila": fila["_fila"],
                "id": valor_id,
                "campo": id_campo,
                "motivo": f"{id_campo} duplicado",
            })
            continue
        vistos.add(valor_id)
        resultado.append(fila)
    return resultado, duplicados


def cargar_eventos(ruta: Path, rechazados: list[dict]) -> list[dict]:
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    filas_crudas = []
    for feature in datos.get("features", []):
        props = feature.get("properties", {}) or {}
        coords = (feature.get("geometry") or {}).get("coordinates", [None, None, None])
        lon = coords[0] if len(coords) > 0 else None
        lat = coords[1] if len(coords) > 1 else None
        depth = coords[2] if len(coords) > 2 else props.get("depth")
        filas_crudas.append({
            "id": feature.get("id") or props.get("id") or "",
            "lon": lon,
            "lat": lat,
            "depth": props.get("depth", depth),
            "magnitude": props.get("magnitude"),
            "time": props.get("time") or "",
            "updated": props.get("updated") or "",
            "place": props.get("place"),
            "status": props.get("status"),
            "url": props.get("url"),
        })
    # lon/lat/depth/magnitude ya llegan numéricos (o None) desde el JSON; no hace falta reconvertir.
    return validar_y_cargar(
        filas_crudas, "eventos", EVENTOS_OBLIGATORIAS, EVENTOS_FECHAS, "id", rechazados
    )


def crear_esquema(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("""
        CREATE TABLE noticias (
            id_noticia TEXT, titulo TEXT, url TEXT, medio TEXT, idioma TEXT,
            fecha_publicacion TIMESTAMP, fecha_deteccion TIMESTAMP, fecha_extraccion TIMESTAMP,
            tema TEXT, origen TEXT, alcance_texto TEXT
        )
    """)
    con.execute("""
        CREATE TABLE indicadores (
            id_evidencia TEXT, pais_iso3 TEXT, indicador_id TEXT, indicador_nombre TEXT,
            anio INTEGER, valor DOUBLE, unidad TEXT, observacion TEXT, fuente_url TEXT,
            fecha_extraccion TIMESTAMP, licencia TEXT
        )
    """)
    con.execute("""
        CREATE TABLE eventos (
            id TEXT, lon DOUBLE, lat DOUBLE, depth DOUBLE, magnitude DOUBLE,
            time TIMESTAMP, updated TIMESTAMP, place TEXT, status TEXT, url TEXT
        )
    """)
    con.execute("""
        CREATE TABLE excluidos (
            origen TEXT, _archivo TEXT, titulo TEXT, url TEXT,
            fecha_publicacion TIMESTAMP, fecha_deteccion TIMESTAMP, motivo TEXT
        )
    """)
    con.execute("""
        CREATE TABLE rechazados (
            tabla TEXT, fila INTEGER, id TEXT, campo TEXT, motivo TEXT
        )
    """)
    con.execute("CREATE TABLE calidad (metrica TEXT, clave TEXT, valor TEXT)")
    con.execute("""
        CREATE TABLE meta (
            esquema_version INTEGER, manifest_sha256 TEXT, built_at TIMESTAMP,
            filas_noticias INTEGER, filas_indicadores INTEGER, filas_eventos INTEGER,
            filas_excluidos INTEGER, filas_rechazados INTEGER
        )
    """)


def _insertar(con: duckdb.DuckDBPyConnection, tabla: str, columnas: list[str], filas: list[dict]) -> None:
    if not filas:
        return
    placeholders = ", ".join("?" for _ in columnas)
    sql = f"INSERT INTO {tabla} ({', '.join(columnas)}) VALUES ({placeholders})"
    datos = [tuple(fila.get(c) for c in columnas) for fila in filas]
    con.executemany(sql, datos)


def manifest_sha256(ruta_manifest: Path) -> str:
    return hashlib.sha256(ruta_manifest.read_bytes()).hexdigest()


def sin_cambios(db_path: Path, hash_manifest: str) -> bool:
    if not db_path.exists():
        return False
    try:
        con = duckdb.connect(str(db_path), read_only=True)
    except duckdb.Error:
        return False
    try:
        fila = con.execute(
            "SELECT esquema_version, manifest_sha256 FROM meta LIMIT 1"
        ).fetchone()
    except duckdb.Error:
        return False
    finally:
        con.close()
    if fila is None:
        return False
    version, hash_guardado = fila
    return version == SCHEMA_VERSION and hash_guardado == hash_manifest


def construir_reporte(
    con: duckdb.DuckDBPyConnection,
    rechazados: list[dict],
    hash_manifest: str,
    duplicados_id: int,
    duplicados_url: int,
) -> str:
    n_noticias = con.execute("SELECT count(*) FROM noticias").fetchone()[0]
    n_indicadores = con.execute("SELECT count(*) FROM indicadores").fetchone()[0]
    n_eventos = con.execute("SELECT count(*) FROM eventos").fetchone()[0]
    n_excluidos = con.execute("SELECT count(*) FROM excluidos").fetchone()[0]

    columnas_noticias = [
        "id_noticia", "titulo", "url", "medio", "idioma", "fecha_publicacion",
        "fecha_deteccion", "fecha_extraccion", "tema", "origen", "alcance_texto",
    ]
    nulos = {}
    for col in columnas_noticias:
        n = con.execute(f"SELECT count(*) FROM noticias WHERE {col} IS NULL").fetchone()[0]
        nulos[col] = n

    por_motivo = Counter(r["motivo"] for r in rechazados)

    por_mes = con.execute("""
        SELECT strftime(coalesce(fecha_deteccion, fecha_publicacion), '%Y-%m') AS mes, count(*)
        FROM noticias WHERE coalesce(fecha_deteccion, fecha_publicacion) IS NOT NULL
        GROUP BY mes ORDER BY mes
    """).fetchall()

    por_origen = con.execute(
        "SELECT origen, count(*) FROM noticias GROUP BY origen ORDER BY count(*) DESC"
    ).fetchall()

    paises = con.execute("SELECT count(DISTINCT pais_iso3) FROM indicadores").fetchone()[0]
    indicadores_distintos = con.execute("SELECT count(DISTINCT indicador_id) FROM indicadores").fetchone()[0]
    anios = con.execute("SELECT count(DISTINCT anio) FROM indicadores").fetchone()[0]
    esperado = paises * indicadores_distintos * anios
    nulos_valor = con.execute("SELECT count(*) FROM indicadores WHERE valor IS NULL").fetchone()[0]

    lineas = [
        "# Reporte de calidad",
        "",
        f"Generado: {datetime.now(timezone.utc).isoformat()}",
        f"Hash del manifest (mismo hash = mismos datos): `{hash_manifest}`",
        "",
        "## Filas por tabla",
        f"- noticias: {n_noticias}",
        f"- indicadores: {n_indicadores}",
        f"- eventos (USGS): {n_eventos}",
        f"- excluidos: {n_excluidos}",
        f"- rechazados: {len(rechazados)}",
        "",
        "## Nulos por columna (noticias)",
    ]
    for col, n in nulos.items():
        lineas.append(f"- {col}: {n}")
    lineas += ["", "## Rechazados por motivo"]
    if por_motivo:
        for motivo, n in por_motivo.most_common():
            lineas.append(f"- {motivo}: {n}")
    else:
        lineas.append("- ninguno")
    lineas += [
        "",
        "## Duplicados",
        f"- id_noticia duplicado: {duplicados_id}",
        f"- URL normalizada duplicada: {duplicados_url}",
        "",
        "## Noticias por mes (fecha_deteccion o fecha_publicacion)",
    ]
    for mes, n in por_mes:
        lineas.append(f"- {mes}: {n}")
    lineas += ["", "## Noticias por origen"]
    for origen, n in por_origen:
        lineas.append(f"- {origen}: {n}")
    lineas += [
        "",
        "## Cuadrícula Banco Mundial (país × indicador × año)",
        f"- países: {paises}, indicadores: {indicadores_distintos}, años: {anios}",
        f"- combinaciones esperadas: {esperado}, filas cargadas: {n_indicadores}",
        f"- valores nulos (sin dato en la fuente): {nulos_valor}",
    ]
    return "\n".join(lineas) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Carga el snapshot en DuckDB y genera el reporte de calidad.")
    parser.add_argument("--forzar", action="store_true", help="reconstruye aunque el manifest no haya cambiado")
    parser.add_argument("--data-dir", default="data", help="directorio con processed/ y manifest.json")
    parser.add_argument("--db", default="data/senales.duckdb", help="ruta de la base DuckDB a generar")
    args = parser.parse_args(argv)

    data_dir = Path(args.data_dir)
    db_path = Path(args.db)
    processed = data_dir / "processed"
    ruta_manifest = data_dir / "manifest.json"

    requeridos = {
        "noticias": processed / "noticias.csv",
        "indicadores": processed / "indicadores.csv",
        "eventos": processed / "eventos.geojson",
        "excluidos": processed / "excluidos.csv",
        "manifest": ruta_manifest,
    }
    faltantes = [str(r) for r in requeridos.values() if not r.exists()]
    if faltantes:
        print(f"Error fatal: archivos de entrada faltantes: {', '.join(faltantes)}", file=sys.stderr)
        return 1

    hash_manifest = manifest_sha256(ruta_manifest)

    if not args.forzar and sin_cambios(db_path, hash_manifest):
        print(f"sin cambios: {db_path} ya refleja el manifest actual ({hash_manifest[:12]}...)")
        return 0

    inicio = time.monotonic()

    rechazados: list[dict] = []

    filas_noticias_crudas = leer_csv(requeridos["noticias"])
    noticias = validar_y_cargar(
        filas_noticias_crudas, "noticias", NOTICIAS_OBLIGATORIAS, NOTICIAS_FECHAS, "id_noticia", rechazados
    )
    noticias, duplicados_id = deduplicar_por_id(noticias, "noticias", "id_noticia", rechazados)

    if not noticias:
        print("Error fatal: la tabla noticias quedó vacía tras la validación.", file=sys.stderr)
        return 1

    urls_normalizadas = Counter(normalizar_url(f.get("url", "")) for f in noticias)
    duplicados_url = sum(n - 1 for n in urls_normalizadas.values() if n > 1)

    filas_indicadores_crudas = leer_csv(requeridos["indicadores"])
    indicadores = validar_y_cargar(
        filas_indicadores_crudas, "indicadores", INDICADORES_OBLIGATORIAS, INDICADORES_FECHAS,
        "id_evidencia", rechazados,
    )
    indicadores, _ = deduplicar_por_id(indicadores, "indicadores", "id_evidencia", rechazados)
    for fila in indicadores:
        fila["anio"] = _a_entero(fila.get("anio"))
        fila["valor"] = _a_flotante(fila.get("valor"))

    eventos = cargar_eventos(requeridos["eventos"], rechazados)
    eventos, _ = deduplicar_por_id(eventos, "eventos", "id", rechazados)

    filas_excluidos_crudas = leer_csv(requeridos["excluidos"])
    excluidos = validar_y_cargar(
        filas_excluidos_crudas, "excluidos", (), EXCLUIDOS_FECHAS, None, rechazados
    )

    # Chequeo defensivo: no deberían quedar duplicados de clave primaria tras la deduplicación.
    for filas, id_campo, nombre in (
        (noticias, "id_noticia", "noticias"),
        (indicadores, "id_evidencia", "indicadores"),
        (eventos, "id", "eventos"),
    ):
        vistos = [f[id_campo] for f in filas]
        if len(vistos) != len(set(vistos)):
            print(f"Error fatal: claves primarias duplicadas en {nombre} tras la carga.", file=sys.stderr)
            return 1

    tmp_path = db_path.with_name(db_path.name + ".tmp")
    if tmp_path.exists():
        tmp_path.unlink()
    tmp_path.parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(tmp_path))
    try:
        # Una sola transacci\u00f3n evita un commit/fsync por fila (ser\u00eda muy lento con ~30k noticias).
        con.execute("BEGIN TRANSACTION")
        crear_esquema(con)
        _insertar(con, "noticias", [
            "id_noticia", "titulo", "url", "medio", "idioma", "fecha_publicacion",
            "fecha_deteccion", "fecha_extraccion", "tema", "origen", "alcance_texto",
        ], noticias)
        _insertar(con, "indicadores", [
            "id_evidencia", "pais_iso3", "indicador_id", "indicador_nombre", "anio", "valor",
            "unidad", "observacion", "fuente_url", "fecha_extraccion", "licencia",
        ], indicadores)
        _insertar(con, "eventos", [
            "id", "lon", "lat", "depth", "magnitude", "time", "updated", "place", "status", "url",
        ], eventos)
        _insertar(con, "excluidos", [
            "origen", "_archivo", "titulo", "url", "fecha_publicacion", "fecha_deteccion", "motivo",
        ], excluidos)
        _insertar(con, "rechazados", ["tabla", "fila", "id", "campo", "motivo"], rechazados)

        reporte = construir_reporte(con, rechazados, hash_manifest, duplicados_id, duplicados_url)
        for linea in reporte.splitlines():
            if linea.startswith("- ") and ": " in linea:
                clave, _, valor = linea[2:].partition(": ")
                con.execute(
                    "INSERT INTO calidad VALUES (?, ?, ?)", ["reporte", clave, valor]
                )
        con.execute(
            "INSERT INTO calidad VALUES (?, ?, ?)", ["mirror", "manifest_sha256", hash_manifest]
        )

        con.execute(
            "INSERT INTO meta VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                SCHEMA_VERSION, hash_manifest, datetime.now(timezone.utc),
                len(noticias), len(indicadores), len(eventos), len(excluidos), len(rechazados),
            ],
        )
        con.execute("COMMIT")
    finally:
        con.close()

    tmp_path.replace(db_path)

    ruta_reporte = db_path.parent / "reporte_calidad.md"
    ruta_reporte.write_text(reporte, encoding="utf-8")

    duracion = time.monotonic() - inicio
    print(
        f"Carga completa en {duracion:.2f}s: {len(noticias)} noticias, {len(indicadores)} indicadores, "
        f"{len(eventos)} eventos, {len(excluidos)} excluidos, {len(rechazados)} rechazados -> {db_path}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
