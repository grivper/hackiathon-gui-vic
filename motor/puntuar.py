#!/usr/bin/env python3
"""Puntaje de atención y estado de evidencia por grupo de evento (T4/T5, TAR-008).

P = 30R + 25I + 20U + 15N + 10E, cada componente normalizado a 0-1 con los criterios de
`motor/reglas_puntaje.yaml` (versionado: cambiar pesos/tramos/rangos sube `version`).
El estado de evidencia (`insuficiente` / `parcial` / `suficiente`) es independiente del
puntaje: una prioridad alta con evidencia insuficiente no habilita publicar nada, solo
señala que falta investigar.

Entradas (ambas solo lectura salvo la escritura final de las tablas propias):
  - `--out` (por defecto data/motor.duckdb): ya trae `grupos` / `grupo_noticias`
    (motor/agrupar.py) y `clasificacion` (motor/clasificar.py, metodo='embeddings').
    Este script le agrega SUS propias tablas (`puntaje`, `meta_puntaje`) sin tocar las
    demás, igual que agrupar.py respecto de clasificar.py.
  - `--db` (por defecto data/senales.duckdb): contexto oficial de solo lectura
    (`indicadores` del Banco Mundial, `eventos` sísmicos de USGS), de nivel-tema. Desde
    v0.2 es puro contexto informativo en la columna `contexto_oficial`: nunca suma al
    componente E ni afecta `estado_evidencia` (no hay vínculo verificable entre una
    noticia concreta y un dato agregado del tema, reto: "si no existe relación
    sustentada, no forzarla").

Nunca etiqueta una noticia como verdadera o falsa: el puntaje es una herramienta de
ordenamiento editorial, no una afirmación de hechos. El texto de las noticias (títulos)
se trata como dato a inspeccionar por palabras clave, nunca como instrucciones a seguir.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import yaml

SCHEMA_VERSION = 2  # v0.2: nueva columna `contexto_oficial` en `puntaje` (TAR-008 ampliacion)
RUTA_REGLAS_DEFECTO = Path(__file__).resolve().parent / "reglas_puntaje.yaml"


# --------------------------------------------------------------------------- reglas_puntaje.yaml

def cargar_reglas(ruta: Path) -> dict:
    """Lee y valida motor/reglas_puntaje.yaml: los pesos deben sumar 100 y los rangos
    de prioridad no deben solaparse ni dejar huecos entre 0 y 100."""
    datos = yaml.safe_load(Path(ruta).read_text(encoding="utf-8"))
    validar_reglas(datos)
    return datos


def validar_reglas(datos: dict) -> None:
    pesos = datos["pesos"]
    total = sum(pesos.values())
    if total != 100:
        raise ValueError(f"los pesos de reglas_puntaje.yaml deben sumar 100, suman {total}")

    rangos = datos["rangos"]
    ordenados = sorted(rangos.values(), key=lambda r: r["lo"])
    if ordenados[0]["lo"] != 0 or ordenados[-1]["hi"] != 100:
        raise ValueError("los rangos de reglas_puntaje.yaml deben cubrir 0 a 100 sin huecos")
    for anterior, siguiente in zip(ordenados, ordenados[1:]):
        if anterior["hi"] != siguiente["lo"]:
            raise ValueError(
                f"los rangos de reglas_puntaje.yaml se solapan o dejan un hueco: "
                f"{anterior} -> {siguiente}"
            )


# --------------------------------------------------------------------------- componentes

def componente_R(tema: str, es_nacional: bool, reglas: dict) -> float:
    """1.0 si el medio es nacional y el tema es uno de los 6 del reto; 0.5 si el tema
    es del reto pero el medio no es nacional; 0.0 para `otros` (o cualquier tema que
    no sea de los 6), sin importar el medio."""
    if tema not in reglas["temas_reto"]:
        return 0.0
    return 1.0 if es_nacional else 0.5


def componente_I(titulo: str | None, reglas: dict) -> float:
    """Alcance por palabras clave en el titular representativo del grupo: nacional >
    sectorial > local (por defecto, si ninguna palabra clave coincide)."""
    texto = (titulo or "").lower()
    cfg = reglas["impacto_alcance"]
    for nivel in ("nacional", "sectorial"):
        palabras = cfg[nivel].get("palabras_clave") or []
        if any(palabra.lower() in texto for palabra in palabras):
            return cfg[nivel]["score"]
    return cfg["local"]["score"]


def componente_U(fecha_max: datetime, fecha_ref: datetime, reglas: dict) -> float:
    """Urgencia por antigüedad de `fecha_max` respecto a `fecha_ref` (tramos de horas
    en orden; el primero que cubra la antigüedad gana). Un grupo "del futuro" respecto
    a la referencia (no debería pasar con fecha_ref = max(fecha_max)) se trata como la
    antigüedad mínima (0h)."""
    horas = max((fecha_ref - fecha_max).total_seconds() / 3600.0, 0.0)
    for tramo in reglas["u_tramos"]:
        if tramo["horas_max"] is None or horas <= tramo["horas_max"]:
            return tramo["score"]
    return reglas["u_tramos"][-1]["score"]


def componente_N(es_repeticion: bool, reglas: dict) -> float:
    """Novedad: 1.0 para un evento nuevo, bajo para una repetición. La duplicación
    nunca sube el puntaje (ver test `test_la_repeticion_nunca_sube_el_puntaje_total`)."""
    cfg = reglas["novedad"]
    return cfg["repeticion"] if es_repeticion else cfg["nuevo"]


def componente_E(corroboracion: int, es_fuente_primaria: bool, reglas: dict) -> float:
    """Evidencia disponible: procedencias independientes además de la primera
    (`corroboracion`, NUNCA n_noticias) + fuente primaria/oficial identificable
    (.gob.pa y similares), capado en 1.0. El contexto oficial de nivel-tema (Banco
    Mundial / USGS) NO suma aquí (v0.2): es puro contexto, ver `contexto_oficial_de`."""
    cfg = reglas["evidencia"]
    por_procedencias = min(
        cfg["peso_por_procedencia_adicional"] * max(corroboracion - 1, 0),
        cfg["tope_procedencias"],
    )
    total = por_procedencias
    if es_fuente_primaria:
        total += cfg["peso_fuente_primaria"]
    return min(total, 1.0)


def puntaje_total(R: float, I: float, U: float, N: float, E: float, pesos: dict) -> float:
    total = pesos["R"] * R + pesos["I"] * I + pesos["U"] * U + pesos["N"] * N + pesos["E"] * E
    return round(total, 1)


def prioridad(puntaje: float, rangos: dict) -> str:
    for nombre, rango in rangos.items():
        if rango["lo"] <= puntaje < rango["hi"]:
            return nombre
    # el límite superior del último rango es inclusivo (p. ej. puntaje == 100.0)
    maximo = max(rangos.values(), key=lambda r: r["hi"])
    for nombre, rango in rangos.items():
        if rango is maximo and puntaje == rango["hi"]:
            return nombre
    raise ValueError(f"puntaje {puntaje} fuera de los rangos de prioridad")


def estado_evidencia(corroboracion: int, es_fuente_primaria: bool) -> str:
    """Independiente del puntaje y del contexto oficial de nivel-tema (v0.2: Banco
    Mundial / USGS nunca afectan esto). `suficiente` exige corroboracion >= 2 Y fuente
    primaria; `parcial` exige al menos una de las dos condiciones; si no hay ninguna,
    `insuficiente`."""
    tiene_corroboracion = corroboracion >= 2
    if tiene_corroboracion and es_fuente_primaria:
        return "suficiente"
    if tiene_corroboracion or es_fuente_primaria:
        return "parcial"
    return "insuficiente"


# --------------------------------------------------------------------------- helpers de grupo

def tema_mayoritario(temas: list[str]) -> str:
    """Tema mayoritario de las noticias de un grupo (metodo='embeddings'). Empates se
    desempatan alfabéticamente, para que el resultado sea determinista."""
    conteo = Counter(temas)
    maximo = max(conteo.values())
    candidatos = sorted(tema for tema, n in conteo.items() if n == maximo)
    return candidatos[0]


def _lista_procedencias(procedencias: str | None) -> list[str]:
    return [p.strip() for p in (procedencias or "").split(";") if p.strip()]


def es_medio_nacional(procedencias: str | None, reglas: dict) -> bool:
    nacionales = set(reglas["medios_nacionales"])
    return any(p in nacionales for p in _lista_procedencias(procedencias))


def es_fuente_primaria(procedencias: str | None, reglas: dict) -> bool:
    cfg = reglas["fuentes_primarias"]
    dominios = set(cfg.get("dominios") or [])
    sufijos = cfg.get("sufijos_dominio") or []
    for p in _lista_procedencias(procedencias):
        if p in dominios or any(p.endswith(sufijo) for sufijo in sufijos):
            return True
    return False


def indicadores_vinculados(tema: str, indicadores_disponibles: set[str], reglas: dict) -> list[str]:
    """Indicadores del Banco Mundial (ids completos, ordenados) que coinciden con los
    prefijos de `contexto_oficial.contexto_por_tema` para `tema`. Puro contexto
    informativo (v0.2): no afecta a E ni a `estado_evidencia`."""
    prefijos = (reglas.get("contexto_oficial", {}).get("contexto_por_tema") or {}).get(tema) or []
    if not prefijos:
        return []
    return sorted(
        {indicador for indicador in indicadores_disponibles if any(indicador.startswith(p) for p in prefijos)}
    )


def contar_eventos_en_ventana(
    fecha_max: datetime, fechas_eventos: list[datetime], ventana_dias: float
) -> int:
    """Cantidad de eventos sísmicos de USGS dentro de la ventana (en días) alrededor de
    `fecha_max`. Puro contexto informativo (v0.2): no afecta a E ni a `estado_evidencia`."""
    limite_segundos = ventana_dias * 86400
    return sum(
        1 for fecha_evento in fechas_eventos if abs((fecha_max - fecha_evento).total_seconds()) <= limite_segundos
    )


def contexto_oficial_de(
    tema: str,
    fecha_max: datetime,
    indicadores_disponibles: set[str],
    fechas_eventos: list[datetime],
    reglas: dict,
) -> str:
    """Texto plano de contexto oficial de nivel-tema, sin afirmar una relación
    verificada con la noticia: indicadores del Banco Mundial para economía, cantidad de
    eventos USGS en ventana para eventos_naturales, cadena vacía en cualquier otro caso
    (reto: \"si no existe relación sustentada, no forzarla\"). Nunca contribuye a E ni a
    `estado_evidencia`."""
    if tema == "economia":
        encontrados = indicadores_vinculados(tema, indicadores_disponibles, reglas)
        return ", ".join(encontrados)
    if tema == "eventos_naturales":
        ventana = reglas["contexto_oficial"]["ventana_dias_evento_natural"]
        n = contar_eventos_en_ventana(fecha_max, fechas_eventos, ventana)
        if n == 0:
            return ""
        return f"{n} evento(s) sísmico(s) USGS en los últimos {ventana} días (contexto, sin relación establecida con la noticia)"
    return ""


def ordenar_filas(filas: list[dict]) -> list[dict]:
    """Orden final: puntaje descendente; empate -> mayor U; empate -> grupo_id
    ascendente (para que el orden sea siempre el mismo, no dependa del orden de SQL)."""
    return sorted(filas, key=lambda f: (-f["puntaje"], -f["U"], f["grupo_id"]))


def construir_motivos(tema: str, es_nacional: bool, alcance: str, R: float, I: float, U: float, N: float, E: float) -> str:
    return (
        f"R={R} (tema={tema}, medio_nacional={es_nacional}); "
        f"I={I} (alcance={alcance}); U={U} (antigüedad vs fecha_ref); "
        f"N={N} (repetición={'sí' if N < 1.0 else 'no'}); E={E} (procedencias/fuente primaria; "
        f"contexto oficial de nivel-tema no suma, ver contexto_oficial)"
    )


def _alcance_de(titulo: str | None, reglas: dict) -> str:
    texto = (titulo or "").lower()
    cfg = reglas["impacto_alcance"]
    for nivel in ("nacional", "sectorial"):
        palabras = cfg[nivel].get("palabras_clave") or []
        if any(palabra.lower() in texto for palabra in palabras):
            return nivel
    return "local"


# --------------------------------------------------------------------------- IO

def cargar_grupos(out_path: Path) -> list[dict]:
    con = duckdb.connect(str(out_path), read_only=True)
    try:
        filas = con.execute("""
            SELECT grupo_id, n_noticias, n_procedencias, procedencias, fecha_min, fecha_max,
                   titulo_representativo, corroboracion, es_repeticion
            FROM grupos
        """).fetchall()
        columnas = [
            "grupo_id", "n_noticias", "n_procedencias", "procedencias", "fecha_min", "fecha_max",
            "titulo_representativo", "corroboracion", "es_repeticion",
        ]
        grupos = [dict(zip(columnas, f)) for f in filas]

        temas_por_grupo: dict[str, list[str]] = {}
        for grupo_id, tema in con.execute("""
            SELECT gn.grupo_id, c.tema
            FROM grupo_noticias gn
            JOIN clasificacion c ON c.id_noticia = gn.id_noticia
            WHERE c.metodo = 'embeddings'
        """).fetchall():
            temas_por_grupo.setdefault(grupo_id, []).append(tema)
    finally:
        con.close()

    for g in grupos:
        temas = temas_por_grupo.get(g["grupo_id"]) or ["otros"]
        g["tema"] = tema_mayoritario(temas)
    return grupos


def cargar_contexto_oficial(db_path: Path) -> tuple[set[str], list[datetime]]:
    """Indicadores del Banco Mundial para Panamá (set de `indicador_id`) y fechas de
    eventos sísmicos de USGS, ambos de solo lectura desde `--db`."""
    if not db_path.exists():
        return set(), []
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        indicadores = {
            fila[0] for fila in con.execute(
                "SELECT DISTINCT indicador_id FROM indicadores WHERE pais_iso3 = 'PAN'"
            ).fetchall()
        }
        eventos = [fila[0] for fila in con.execute("SELECT time FROM eventos").fetchall()]
    finally:
        con.close()
    return indicadores, eventos


def hash_entrada(grupos: list[dict], version_reglas: str, fecha_ref: datetime) -> str:
    h = hashlib.sha256()
    h.update(version_reglas.encode())
    h.update(fecha_ref.isoformat().encode())
    for g in sorted(grupos, key=lambda g: g["grupo_id"]):
        h.update(g["grupo_id"].encode())
        h.update(str(g["corroboracion"]).encode())
        h.update(str(g["es_repeticion"]).encode())
        h.update(str(g["procedencias"]).encode())
        h.update(str(g["fecha_max"]).encode())
        h.update(str(g["titulo_representativo"]).encode())
        h.update(str(g["tema"]).encode())
    return h.hexdigest()


def sin_cambios(out_path: Path, entrada_hash: str) -> bool:
    con = duckdb.connect(str(out_path), read_only=True)
    try:
        fila = con.execute(
            "SELECT esquema_version, entrada_hash FROM meta_puntaje LIMIT 1"
        ).fetchone()
    except duckdb.Error:
        return False
    finally:
        con.close()
    if fila is None:
        return False
    version, hash_guardado = fila
    return version == SCHEMA_VERSION and hash_guardado == entrada_hash


def calcular_filas(
    grupos: list[dict],
    reglas: dict,
    fecha_ref: datetime,
    indicadores_disponibles: set[str],
    fechas_eventos: list[datetime],
) -> list[dict]:
    filas = []
    for g in grupos:
        tema = g["tema"]
        es_nacional = es_medio_nacional(g["procedencias"], reglas)
        alcance = _alcance_de(g["titulo_representativo"], reglas)
        primaria = es_fuente_primaria(g["procedencias"], reglas)
        contexto_oficial = contexto_oficial_de(
            tema, g["fecha_max"], indicadores_disponibles, fechas_eventos, reglas
        )

        R = componente_R(tema, es_nacional, reglas)
        I = componente_I(g["titulo_representativo"], reglas)
        U = componente_U(g["fecha_max"], fecha_ref, reglas)
        N = componente_N(g["es_repeticion"], reglas)
        E = componente_E(g["corroboracion"], primaria, reglas)

        puntaje = puntaje_total(R, I, U, N, E, reglas["pesos"])
        filas.append({
            "grupo_id": g["grupo_id"], "tema": tema, "R": R, "I": I, "U": U, "N": N, "E": E,
            "puntaje": puntaje, "prioridad": prioridad(puntaje, reglas["rangos"]),
            "estado_evidencia": estado_evidencia(g["corroboracion"], primaria),
            "version_reglas": reglas["version"],
            "motivos": construir_motivos(tema, es_nacional, alcance, R, I, U, N, E),
            "contexto_oficial": contexto_oficial,
        })
    return ordenar_filas(filas)


def escribir_resultados(out_path: Path, filas: list[dict], entrada_hash: str, fecha_ref: datetime) -> None:
    con = duckdb.connect(str(out_path))
    try:
        con.execute("BEGIN TRANSACTION")
        con.execute("DROP TABLE IF EXISTS puntaje")
        con.execute("DROP TABLE IF EXISTS meta_puntaje")
        con.execute("""
            CREATE TABLE puntaje (
                grupo_id TEXT, tema TEXT, R DOUBLE, I DOUBLE, U DOUBLE, N DOUBLE, E DOUBLE,
                puntaje DOUBLE, prioridad TEXT, estado_evidencia TEXT, version_reglas TEXT, motivos TEXT,
                contexto_oficial TEXT
            )
        """)
        con.execute("""
            CREATE TABLE meta_puntaje (
                esquema_version INTEGER, version_reglas TEXT, fecha_ref TIMESTAMP,
                entrada_hash TEXT, n_grupos INTEGER, built_at TIMESTAMP
            )
        """)
        con.executemany(
            "INSERT INTO puntaje VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    f["grupo_id"], f["tema"], f["R"], f["I"], f["U"], f["N"], f["E"], f["puntaje"],
                    f["prioridad"], f["estado_evidencia"], f["version_reglas"], f["motivos"],
                    f["contexto_oficial"],
                )
                for f in filas
            ],
        )
        version_reglas = filas[0]["version_reglas"] if filas else ""
        con.execute(
            "INSERT INTO meta_puntaje VALUES (?, ?, ?, ?, ?, ?)",
            [SCHEMA_VERSION, version_reglas, fecha_ref, entrada_hash, len(filas), datetime.now(timezone.utc)],
        )
        con.execute("COMMIT")
    finally:
        con.close()


# --------------------------------------------------------------------------- resumen

def imprimir_resumen(filas: list[dict]) -> None:
    print(f"\nGrupos puntuados: {len(filas)}")
    if not filas:
        return
    por_prioridad = Counter(f["prioridad"] for f in filas)
    print("Por prioridad:")
    for nombre in ("alto", "medio", "bajo"):
        print(f"  - {nombre}: {por_prioridad.get(nombre, 0)}")

    por_estado = Counter(f["estado_evidencia"] for f in filas)
    print("Por estado de evidencia:")
    for nombre in ("suficiente", "parcial", "insuficiente"):
        print(f"  - {nombre}: {por_estado.get(nombre, 0)}")

    print("\nTop 5 por puntaje:")
    for f in filas[:5]:
        print(f"  - [{f['grupo_id']}] puntaje={f['puntaje']} prioridad={f['prioridad']} tema={f['tema']} evidencia={f['estado_evidencia']}")


# --------------------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Calcula el puntaje de atención y el estado de evidencia por grupo de evento.")
    parser.add_argument("--forzar", action="store_true", help="recalcula aunque nada haya cambiado")
    parser.add_argument("--fecha-ref", default=None, help="fecha de referencia ISO (por defecto, max(fecha_max) en grupos: reproducible, no 'ahora')")
    parser.add_argument("--db", default="data/senales.duckdb", help="base DuckDB de contexto oficial (solo lectura: indicadores, eventos)")
    parser.add_argument("--out", default="data/motor.duckdb", help="base DuckDB con grupos/clasificacion de entrada y puntaje/meta_puntaje de salida")
    parser.add_argument("--reglas", default=str(RUTA_REGLAS_DEFECTO), help="ruta a reglas_puntaje.yaml")
    args = parser.parse_args(argv)

    out_path = Path(args.out)
    if not out_path.exists():
        print(f"Error fatal: no existe {out_path} (correr antes make agrupar / make clasificar)", file=sys.stderr)
        return 1

    reglas = cargar_reglas(Path(args.reglas))
    grupos = cargar_grupos(out_path)
    if not grupos:
        print("Sin grupos que puntuar.", file=sys.stderr)
        return 1

    if args.fecha_ref:
        fecha_ref = datetime.fromisoformat(args.fecha_ref)
    else:
        fecha_ref = max(g["fecha_max"] for g in grupos)

    entrada_hash = hash_entrada(grupos, reglas["version"], fecha_ref)
    if not args.forzar and sin_cambios(out_path, entrada_hash):
        print(f"sin cambios: {out_path} ya refleja esta entrada ({entrada_hash[:12]}...)")
        return 0

    inicio = time.monotonic()
    indicadores_disponibles, fechas_eventos = cargar_contexto_oficial(Path(args.db))
    filas = calcular_filas(grupos, reglas, fecha_ref, indicadores_disponibles, fechas_eventos)
    escribir_resultados(out_path, filas, entrada_hash, fecha_ref)
    duracion = time.monotonic() - inicio

    print(f"Puntaje calculado en {duracion:.2f}s ({len(filas)} grupos, reglas {reglas['version']}, fecha_ref={fecha_ref.isoformat()}) -> {out_path}")
    imprimir_resumen(filas)
    return 0


if __name__ == "__main__":
    sys.exit(main())
