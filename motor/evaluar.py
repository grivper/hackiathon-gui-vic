#!/usr/bin/env python3
"""Evalua los metodos de clasificacion (embeddings, tfidf) contra etiquetas humanas
(TAR-007, T4): macro-F1, precision/recall/F1 por tema, matriz de confusion y tasa de
abstencion (el metodo dijo `otros`), para cada metodo registrado en `clasificacion`.

Lee:
  - el CSV de etiquetas humanas (por defecto data/etiquetas/muestra_etiquetado.csv,
    producido por motor/muestra_etiquetado.py y llenado a mano, columna `tema_humano`).
  - la tabla `clasificacion` de la base de salida de motor/clasificar.py (por defecto
    data/motor.duckdb), solo lectura.

Escribe un reporte markdown (por defecto data/evaluacion_clasificacion.md) y tambien
imprime un resumen en pantalla. Si hay menos de 10 filas etiquetadas validas, no
escribe un reporte enganoso: imprime "faltan etiquetas" y termina con codigo 0 (no es
un error del script, es que todavia no hay suficiente trabajo humano).
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import duckdb

TEMAS_VALIDOS = [
    "economia", "logistica_canal", "turismo",
    "servicios_publicos", "eventos_naturales", "regulacion", "otros",
]
MINIMO_ETIQUETAS = 10
RUTA_ETIQUETAS_DEFECTO = "data/etiquetas/muestra_etiquetado.csv"
RUTA_MOTOR_DEFECTO = "data/motor.duckdb"
RUTA_OUT_DEFECTO = "data/evaluacion_clasificacion.md"


class EtiquetaInvalidaError(ValueError):
    pass


# --------------------------------------------------------------------------- etiquetas humanas

def cargar_etiquetas(ruta: Path) -> list[dict]:
    """Lee el CSV de etiquetas humanas. Descarta filas con `tema_humano` vacio (sin
    etiquetar todavia). Si una fila SI tiene un valor pero no es uno de los 7 validos,
    falla con un mensaje claro (evita que un typo se cuele silenciosamente).
    """
    with ruta.open(encoding="utf-8", newline="") as f:
        filas = list(csv.DictReader(f))

    columnas_opcionales = set()
    if filas:
        columnas_opcionales = set(filas[0].keys()) & {"labelador", "metodo_etiquetado"}

    validas = []
    for fila in filas:
        tema_humano = (fila.get("tema_humano") or "").strip()
        if not tema_humano:
            continue
        if tema_humano not in TEMAS_VALIDOS:
            raise EtiquetaInvalidaError(
                f"valor de tema_humano desconocido en id_noticia={fila.get('id_noticia')!r}: "
                f"{tema_humano!r}. Valores validos: {', '.join(TEMAS_VALIDOS)}."
            )
        entrada = {
            "id_noticia": fila["id_noticia"],
            "titulo": fila.get("titulo", ""),
            "tema_humano": tema_humano,
        }
        for col in columnas_opcionales:
            entrada[col] = fila.get(col)
        validas.append(entrada)
    return validas


# --------------------------------------------------------------------------- clasificacion del motor

def cargar_predicciones(db_path: Path) -> dict[str, dict[str, str]]:
    """Devuelve {metodo: {id_noticia: tema}} leyendo la tabla `clasificacion`."""
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        filas = con.execute("SELECT metodo, id_noticia, tema FROM clasificacion").fetchall()
    finally:
        con.close()
    predicciones: dict[str, dict[str, str]] = {}
    for metodo, id_noticia, tema in filas:
        predicciones.setdefault(metodo, {})[id_noticia] = tema
    return predicciones


# --------------------------------------------------------------------------- metricas

def calcular_metricas(y_true: list[str], y_pred: list[str]) -> dict:
    """Macro-F1, precision/recall/F1/soporte por clase y matriz de confusion, usando
    sklearn. `etiquetas` = union ordenada de clases vistas en y_true o y_pred."""
    from sklearn.metrics import confusion_matrix, precision_recall_fscore_support

    presentes = set(y_true) | set(y_pred)
    etiquetas = [t for t in TEMAS_VALIDOS if t in presentes]
    etiquetas += sorted(presentes - set(etiquetas))  # por si aparece algo fuera de TEMAS_VALIDOS
    precision, recall, f1, soporte = precision_recall_fscore_support(
        y_true, y_pred, labels=etiquetas, zero_division=0
    )
    macro_f1 = float(f1.mean()) if len(f1) else 0.0
    matriz = confusion_matrix(y_true, y_pred, labels=etiquetas)

    por_clase = []
    for i, tema in enumerate(etiquetas):
        por_clase.append({
            "tema": tema,
            "precision": float(precision[i]),
            "recall": float(recall[i]),
            "f1": float(f1[i]),
            "soporte": int(soporte[i]),
        })

    return {
        "etiquetas": etiquetas,
        "macro_f1": macro_f1,
        "por_clase": por_clase,
        "matriz_confusion": matriz.tolist(),
    }


def tasa_abstencion(y_pred: list[str]) -> float:
    if not y_pred:
        return 0.0
    return sum(1 for p in y_pred if p == "otros") / len(y_pred)


def evaluar_metodo(etiquetas: list[dict], predicciones_metodo: dict[str, str]) -> dict | None:
    """Une `etiquetas` (humanas) con las predicciones de un metodo por id_noticia.
    Devuelve None si no hay ningun id_noticia en comun (el metodo no cubre la muestra)."""
    pares = [
        (e["tema_humano"], predicciones_metodo[e["id_noticia"]])
        for e in etiquetas
        if e["id_noticia"] in predicciones_metodo
    ]
    if not pares:
        return None
    y_true = [p[0] for p in pares]
    y_pred = [p[1] for p in pares]
    metricas = calcular_metricas(y_true, y_pred)
    metricas["n"] = len(pares)
    metricas["abstencion"] = tasa_abstencion(y_pred)
    return metricas


# --------------------------------------------------------------------------- reporte

def formatear_reporte(
    etiquetas: list[dict],
    resultados_por_metodo: dict[str, dict],
) -> str:
    lineas = ["# Evaluacion de la clasificacion por tema (TAR-007)", ""]
    lineas.append(f"- Tamano de la muestra etiquetada: {len(etiquetas)}")
    lineas.append("- Metodo de etiquetado: manual, a ciegas (sin ver la salida del modelo), "
                   "ver `motor/muestra_etiquetado.py` / `LEEME_etiquetado.md`.")
    labeladores = sorted({e["labelador"] for e in etiquetas if e.get("labelador")})
    if labeladores:
        lineas.append(f"- Etiquetado por: {', '.join(labeladores)}")
    metodos_etiquetado = sorted({e["metodo_etiquetado"] for e in etiquetas if e.get("metodo_etiquetado")})
    if metodos_etiquetado:
        lineas.append(f"- Metodo de etiquetado (campo libre): {', '.join(metodos_etiquetado)}")
    lineas.append("")

    for metodo, metricas in resultados_por_metodo.items():
        lineas.append(f"## Metodo: {metodo}")
        if metricas is None:
            lineas.append("")
            lineas.append("Sin cobertura: ninguna de las noticias etiquetadas aparece en "
                           "`clasificacion` para este metodo.")
            lineas.append("")
            continue
        lineas.append("")
        lineas.append(f"- Noticias evaluadas (con etiqueta humana y prediccion de este metodo): {metricas['n']}")
        lineas.append(f"- Macro-F1: {metricas['macro_f1']:.3f}")
        lineas.append(f"- Tasa de abstencion (el metodo dijo `otros`): {100 * metricas['abstencion']:.1f}%")
        lineas.append("")
        lineas.append("| tema | precision | recall | F1 | soporte |")
        lineas.append("|---|---|---|---|---|")
        for fila in metricas["por_clase"]:
            lineas.append(
                f"| {fila['tema']} | {fila['precision']:.3f} | {fila['recall']:.3f} | "
                f"{fila['f1']:.3f} | {fila['soporte']} |"
            )
        lineas.append("")
        lineas.append("Matriz de confusion (filas = etiqueta humana, columnas = prediccion), "
                       f"orden: {', '.join(metricas['etiquetas'])}")
        lineas.append("")
        lineas.append("```")
        for fila in metricas["matriz_confusion"]:
            lineas.append(" ".join(str(v) for v in fila))
        lineas.append("```")
        lineas.append("")

    return "\n".join(lineas)


# --------------------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evalua los metodos de clasificacion contra etiquetas humanas (macro-F1, etc.)."
    )
    parser.add_argument("--etiquetas", default=RUTA_ETIQUETAS_DEFECTO, help="CSV de etiquetas humanas")
    parser.add_argument("--motor", default=RUTA_MOTOR_DEFECTO, help="base DuckDB con la tabla clasificacion")
    parser.add_argument("--out", default=RUTA_OUT_DEFECTO, help="ruta del reporte markdown de salida")
    args = parser.parse_args(argv)

    ruta_etiquetas = Path(args.etiquetas)
    ruta_motor = Path(args.motor)
    ruta_out = Path(args.out)

    if not ruta_etiquetas.exists():
        print(f"Error fatal: no existe el CSV de etiquetas {ruta_etiquetas}", file=sys.stderr)
        return 1
    if not ruta_motor.exists():
        print(f"Error fatal: no existe la base de clasificacion {ruta_motor}", file=sys.stderr)
        return 1

    try:
        etiquetas = cargar_etiquetas(ruta_etiquetas)
    except EtiquetaInvalidaError as e:
        print(f"Error fatal: {e}", file=sys.stderr)
        return 1

    if len(etiquetas) < MINIMO_ETIQUETAS:
        print(
            f"Faltan etiquetas: solo hay {len(etiquetas)} fila(s) con tema_humano valido "
            f"en {ruta_etiquetas} (se requieren al menos {MINIMO_ETIQUETAS}). "
            "No se genera el reporte todavia; sigue etiquetando y vuelve a correr "
            "'make evaluar' cuando haya mas."
        )
        return 0

    predicciones = cargar_predicciones(ruta_motor)
    resultados_por_metodo = {
        metodo: evaluar_metodo(etiquetas, predicciones_metodo)
        for metodo, predicciones_metodo in sorted(predicciones.items())
    }

    reporte = formatear_reporte(etiquetas, resultados_por_metodo)
    ruta_out.parent.mkdir(parents=True, exist_ok=True)
    ruta_out.write_text(reporte, encoding="utf-8")

    print(f"Evaluacion escrita en {ruta_out} (muestra: {len(etiquetas)} etiquetas)")
    for metodo, metricas in resultados_por_metodo.items():
        if metricas is None:
            print(f"  [{metodo}] sin cobertura")
            continue
        print(
            f"  [{metodo}] n={metricas['n']} macro-F1={metricas['macro_f1']:.3f} "
            f"abstencion={100 * metricas['abstencion']:.1f}%"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
