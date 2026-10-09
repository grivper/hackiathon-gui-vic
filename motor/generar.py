#!/usr/bin/env python3
"""Fichas con borrador citado por grupo de evento (TAR-009, G6).

Une las piezas del RAG en capas: evidencia (`evidencia.py`) -> abstención por código
(`abstencion.py`) -> prompt (`prompt.py`) -> LLM local (`llm.py`) -> validador de citas
(`citas.py`). El LLM solo propone afirmaciones; el BORRADOR lo arma este módulo con las
que sobrevivieron al validador, nunca con texto libre del modelo. Sin evidencia, con
error del modelo, sin afirmaciones sustentadas o ante una inyección obedecida, la ficha
es una abstención con estado de revisión `requiere evidencia`.

Salida: tabla `fichas` en data/motor.duckdb (upsert por `id_caso`) y export `fichas.jsonl`
con el formato del reto (id_caso, modalidad, ids_fuente, afirmaciones, citas, puntaje,
componentes, estado_evidencia, borrador, estado_revision). Nada se publica: aprobar un
borrador no es publicar.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from motor import abstencion, citas, evidencia, llm, prompt  # noqa: E402

ESTADO_NUEVO = "nuevo"
ESTADO_REQUIERE_EVIDENCIA = "requiere evidencia"
ESTADOS_REVISADOS = {"en revisión", "aprobado como borrador", "descartado"}
MODALIDAD = "editorial"


def _datos_puntaje(motor_db: Path, grupo_id: str) -> dict:
    con = duckdb.connect(str(motor_db), read_only=True)
    try:
        fila = con.execute(
            "SELECT R, I, U, N, E, puntaje, prioridad, estado_evidencia, version_reglas, motivos "
            "FROM puntaje WHERE grupo_id = ?", [grupo_id]
        ).fetchone()
    finally:
        con.close()
    if fila is None:
        raise KeyError(f"grupo inexistente en puntaje: {grupo_id}")
    return {
        "componentes": dict(zip("RIUNE", fila[:5])), "puntaje": fila[5], "prioridad": fila[6],
        "estado_evidencia": fila[7], "version_reglas": fila[8], "motivos_puntaje": fila[9],
    }


def _generacion(r: llm.Respuesta | None) -> dict:
    if r is None:
        return {}
    return {
        "modelo": r.modelo, "opciones": r.opciones, "duracion_s": r.duracion_s,
        "tokens_salida": r.tokens_salida, "tokens_por_segundo": r.tokens_por_segundo,
    }


PAISES = {"PAN": "Panamá"}


def _contexto_dato(campos: dict) -> str:
    """País, año y unidad de un indicador anual, escritos por código (CU-02, T04)."""
    pais = PAISES.get(campos.get("pais_iso3"), campos.get("pais_iso3") or "país no indicado")
    unidad = campos.get("unidad") or "unidad no indicada"
    return f" ({pais} · {campos.get('anio')} · {unidad}; dato anual, no una medición de hoy)"


DIAS_RECIRCULACION = 30


def _dia(iso: str | None) -> datetime | None:
    return datetime.fromisoformat(iso[:10]) if iso else None


def _contexto_noticia(campos: dict) -> str:
    """Fecha original de una noticia, escrita por código (T03): una nota publicada mucho antes
    de ser detectada vuelve a circular y no se presenta como un evento nuevo."""
    publicada, detectada = _dia(campos.get("fecha_publicacion")), _dia(campos.get("fecha_deteccion"))
    if publicada is None:
        return f" (detectada {detectada:%Y-%m-%d}; fecha de publicación no disponible)" if detectada else ""
    if detectada is not None and (detectada - publicada).days > DIAS_RECIRCULACION:
        return (f" (publicada originalmente {publicada:%Y-%m-%d}; detectada de nuevo {detectada:%Y-%m-%d}: "
                "vuelve a circular, no es un evento nuevo)")
    return f" (publicada {publicada:%Y-%m-%d})"


def _borrador(
    afirmaciones: list[dict], versiones: list, vacios: list, alcance: str, items: dict[str, dict] | None = None,
    tipo_respuesta: str = "respuesta",
) -> str:
    items = items or {}
    lineas = []
    for a in afirmaciones:
        item = items.get(a["id_evidencia"])
        contexto = ""
        if item and item.get("tipo") == "indicador":
            contexto = _contexto_dato(item["campos"])
        elif item and item.get("tipo") == "noticia":
            contexto = _contexto_noticia(item["campos"])
        lineas.append(f"- {a['texto']} [{a['id_evidencia']} · {a['campo']}]{contexto}")
    if versiones:
        lineas.append("Versiones: " + "; ".join(str(v) for v in versiones))
    if tipo_respuesta == "contradiccion":
        lineas.append("Revisión pendiente: las fuentes no coinciden; una persona debe revisarlas antes de usar este borrador.")
    if vacios:
        lineas.append("Vacíos: " + "; ".join(str(v) for v in vacios))
    lineas.append(f"Alcance: {alcance}")
    return "\n".join(lineas)


def _abstencion(base: dict, motivo: str, vacios: list[str], alcance: str, r: llm.Respuesta | None,
                descartadas: list | None = None) -> dict:
    return {
        **base, "afirmaciones": [], "citas": [], "tipo_respuesta": "abstencion", "motivo_abstencion": motivo,
        "vacios": vacios, "versiones": [], "alcance": alcance, "descartadas": descartadas or [],
        "cobertura_citas": 0.0,
        "borrador": "Sin borrador: " + "; ".join(vacios) + f"\nAlcance: {alcance}",
        "estado_revision": ESTADO_REQUIERE_EVIDENCIA, "generacion": _generacion(r),
    }


def generar_ficha(
    grupo_id: str, cliente, motor_db: Path, senales_db: Path, reglas: dict, canarios: list[str] | None = None
) -> dict:
    """Ficha completa de un grupo. Nunca lanza por fallos del modelo: se abstiene."""
    paquete = evidencia.reunir_evidencia(grupo_id, motor_db, senales_db, reglas)
    puntaje = _datos_puntaje(motor_db, grupo_id)
    alcance = abstencion.alcance_de(paquete)
    base = {
        "id_caso": grupo_id, "modalidad": MODALIDAD, "tema": paquete["tema"],
        "ids_fuente": [i["id_evidencia"] for i in paquete["items"]], **puntaje,
    }

    previa = abstencion.decidir_abstencion_grupo(paquete)
    if previa is not None:
        return _abstencion(base, previa["motivo"], previa["vacios"], previa["alcance"], None)

    p = prompt.construir_prompt(paquete, alcance)
    r = cliente.generar(p["sistema"], p["usuario"], p["esquema"])
    if r.contenido is None:
        return _abstencion(base, "llm_error", [f"El modelo no devolvió una salida utilizable ({r.error})."], alcance, r)
    if canarios and prompt.obedecio_inyeccion(r.contenido, canarios):
        return _abstencion(base, "inyeccion", ["La salida del modelo obedeció contenido de una fuente."], alcance, r)

    v = citas.validar_citas(r.contenido, paquete)
    if not v["valida"]:
        return _abstencion(base, "esquema_invalido", v["errores_esquema"], alcance, r)
    if v["tipo_respuesta"] == "abstencion":
        motivo = "modelo_abstuvo" if r.contenido.get("tipo_respuesta") == "abstencion" else "sin_sustento"
        vacios = v["vacios"] or ["Ninguna afirmación del modelo quedó sustentada por la evidencia."]
        return _abstencion(base, motivo, vacios, alcance, r, v["descartadas"])

    # Un modelo chico llenó `versiones` pero dijo `respuesta` (T05 con gemma3:4b): dos o más
    # versiones declaradas son una contradicción, sin importar la etiqueta.
    tipo = "contradiccion" if v["tipo_respuesta"] == "respuesta" and len(v["versiones"]) >= 2 else v["tipo_respuesta"]
    citas_usadas: list[dict] = []
    for a in v["afirmaciones"]:
        cita = {"id_evidencia": a["id_evidencia"], "campo": a["campo"]}
        if cita not in citas_usadas:
            citas_usadas.append(cita)
    return {
        **base, "afirmaciones": v["afirmaciones"], "citas": citas_usadas,
        "tipo_respuesta": tipo, "motivo_abstencion": None,
        "vacios": v["vacios"], "versiones": v["versiones"], "alcance": alcance,
        "descartadas": v["descartadas"], "cobertura_citas": v["cobertura"],
        "borrador": _borrador(
            v["afirmaciones"], v["versiones"], v["vacios"], alcance, {i["id_evidencia"]: i for i in paquete["items"]},
            tipo,
        ),
        "estado_revision": ESTADO_NUEVO, "generacion": _generacion(r),
    }


# --------------------------------------------------------------------------- IO

def _crear_tabla(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        "CREATE TABLE IF NOT EXISTS fichas (id_caso TEXT, estado_revision TEXT, tipo_respuesta TEXT, "
        "ficha TEXT, generado_en TIMESTAMP)"
    )


def estados_existentes(motor_db: Path) -> dict[str, str]:
    con = duckdb.connect(str(motor_db))
    try:
        _crear_tabla(con)
        return dict(con.execute("SELECT id_caso, estado_revision FROM fichas").fetchall())
    finally:
        con.close()


def escribir_fichas(motor_db: Path, fichas: list[dict], jsonl: Path) -> None:
    """Upsert por `id_caso` (no se pierden las fichas no regeneradas) y export JSONL completo."""
    con = duckdb.connect(str(motor_db))
    try:
        _crear_tabla(con)
        con.execute("BEGIN TRANSACTION")
        ahora = datetime.now(timezone.utc)
        for f in fichas:
            con.execute("DELETE FROM fichas WHERE id_caso = ?", [f["id_caso"]])
            con.execute(
                "INSERT INTO fichas VALUES (?, ?, ?, ?, ?)",
                [f["id_caso"], f.get("estado_revision"), f.get("tipo_respuesta"),
                 json.dumps(f, ensure_ascii=False, sort_keys=True), ahora],
            )
        con.execute("COMMIT")
        todas = [json.loads(fila[0]) for fila in con.execute("SELECT ficha FROM fichas ORDER BY id_caso").fetchall()]
    finally:
        con.close()
    jsonl.parent.mkdir(parents=True, exist_ok=True)
    jsonl.write_text("".join(json.dumps(t, ensure_ascii=False, sort_keys=True) + "\n" for t in todas), encoding="utf-8")


def guardar_ficha(motor_db: Path, ficha: dict, jsonl: Path) -> None:
    """Guarda UNA ficha sin tocar las demás (la usa el botón de la interfaz).

    La tabla recibe un upsert de esa fila. El JSONL se fusiona por `id_caso`: las líneas de
    otras fichas se conservan aunque la base local no las tenga (a diferencia de
    `escribir_fichas`, que reescribe el export completo desde la tabla).
    """
    con = duckdb.connect(str(motor_db))
    try:
        _crear_tabla(con)
        con.execute("BEGIN TRANSACTION")
        con.execute("DELETE FROM fichas WHERE id_caso = ?", [ficha["id_caso"]])
        con.execute(
            "INSERT INTO fichas VALUES (?, ?, ?, ?, ?)",
            [ficha["id_caso"], ficha.get("estado_revision"), ficha.get("tipo_respuesta"),
             json.dumps(ficha, ensure_ascii=False, sort_keys=True), datetime.now(timezone.utc)],
        )
        con.execute("COMMIT")
    finally:
        con.close()
    previas: list[dict] = []
    if jsonl.exists():
        previas = [json.loads(linea) for linea in jsonl.read_text(encoding="utf-8").splitlines() if linea.strip()]
    fusion = {f["id_caso"]: f for f in previas}
    fusion[ficha["id_caso"]] = ficha
    jsonl.parent.mkdir(parents=True, exist_ok=True)
    jsonl.write_text(
        "".join(json.dumps(fusion[k], ensure_ascii=False, sort_keys=True) + "\n" for k in sorted(fusion)),
        encoding="utf-8",
    )


def _grupos_top(motor_db: Path, n: int, min_noticias: int) -> list[str]:
    con = duckdb.connect(str(motor_db), read_only=True)
    try:
        return [f[0] for f in con.execute(
            "SELECT p.grupo_id FROM puntaje p JOIN grupos g USING (grupo_id) WHERE g.n_noticias >= ? "
            "ORDER BY p.puntaje DESC, p.grupo_id LIMIT ?", [min_noticias, n]).fetchall()]
    finally:
        con.close()


def main(argv: list[str] | None = None, cliente=None) -> int:
    ap = argparse.ArgumentParser(description="Genera fichas con borrador citado (TAR-009).")
    ap.add_argument("--grupo", action="append", default=[], help="grupo_id (repetible)")
    ap.add_argument("--top", type=int, default=0, help="los N grupos de mayor puntaje")
    ap.add_argument("--min-noticias", type=int, default=1)
    ap.add_argument("--forzar", action="store_true", help="regenera también fichas ya revisadas por una persona")
    ap.add_argument("--db", default="data/senales.duckdb")
    ap.add_argument("--motor", default="data/motor.duckdb")
    ap.add_argument("--jsonl", default="data/fichas.jsonl")
    ap.add_argument("--reglas", default="motor/reglas_puntaje.yaml")
    args = ap.parse_args(argv)

    motor, senales = Path(args.motor), Path(args.db)
    reglas = yaml.safe_load(Path(args.reglas).read_text(encoding="utf-8"))
    grupos = list(args.grupo) + (_grupos_top(motor, args.top, args.min_noticias) if args.top else [])
    if not grupos:
        print("nada que generar: indicá --grupo o --top", file=sys.stderr)
        return 2

    existentes = estados_existentes(motor)
    cliente = cliente or llm.cliente_desde_entorno()
    fichas = []
    for g in grupos:
        if not args.forzar and existentes.get(g) in ESTADOS_REVISADOS:
            print(f"{g}: ya revisada ({existentes[g]}), se conserva (usá --forzar para regenerar)")
            continue
        f = generar_ficha(g, cliente, motor, senales, reglas)
        fichas.append(f)
        print(f"{g}: {f['tipo_respuesta']}"
              + (f" ({f['motivo_abstencion']})" if f["motivo_abstencion"] else "")
              + f" · {len(f['afirmaciones'])} afirmaciones · estado {f['estado_revision']}")
    escribir_fichas(motor, fichas, Path(args.jsonl))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
