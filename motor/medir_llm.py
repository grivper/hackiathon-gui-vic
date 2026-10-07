#!/usr/bin/env python3
"""Mide latencia y calidad de citas de un modelo local sobre grupos reales (TAR-009, G5).

Para cada grupo: arma la evidencia, el prompt y la llamada al LLM, valida las citas por
código y reporta mediana y p95 de tiempo, tokens por segundo y cuántas salidas son JSON
válido y conservan al menos una afirmación con cita válida. Sirve para elegir modelo con
datos (meta del reto: mediana <= 15 s) y para documentar parámetros y limitaciones.

Uso: python motor/medir_llm.py --modelo qwen2.5:3b-instruct-q4_K_M --n 5
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

import duckdb
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from motor import abstencion, citas, evidencia, llm, prompt  # noqa: E402


def _p95(valores: list[float]) -> float:
    ordenados = sorted(valores)
    if len(ordenados) == 1:
        return ordenados[0]
    posicion = 0.95 * (len(ordenados) - 1)
    bajo = int(posicion)
    return ordenados[bajo] + (ordenados[min(bajo + 1, len(ordenados) - 1)] - ordenados[bajo]) * (posicion - bajo)


def medir(cliente, paquetes: list[dict]) -> dict:
    tiempos, tps, validas, con_cita = [], [], 0, 0
    modelo = getattr(cliente, "modelo", "")
    for paquete in paquetes:
        p = prompt.construir_prompt(paquete, abstencion.alcance_de(paquete))
        r = cliente.generar(p["sistema"], p["usuario"], p["esquema"])
        modelo = r.modelo or modelo
        tiempos.append(r.duracion_s)
        if r.tokens_por_segundo:
            tps.append(r.tokens_por_segundo)
        if r.contenido is not None:
            validas += 1
            if citas.validar_citas(r.contenido, paquete)["afirmaciones"]:
                con_cita += 1
    return {
        "modelo": modelo, "n": len(paquetes),
        "tiempo_mediana_s": statistics.median(tiempos), "tiempo_p95_s": _p95(tiempos),
        "tokens_por_segundo_mediana": statistics.median(tps) if tps else 0.0,
        "salidas_validas": validas, "con_cita_valida": con_cita,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Mide latencia y calidad de citas de un modelo Ollama.")
    ap.add_argument("--modelo", default=llm.MODELO_DEFECTO)
    ap.add_argument("--n", type=int, default=5, help="cantidad de grupos (los de mayor puntaje)")
    ap.add_argument("--min-noticias", type=int, default=1, help="solo grupos con al menos esta cantidad de noticias")
    ap.add_argument("--db", default="data/senales.duckdb")
    ap.add_argument("--motor", default="data/motor.duckdb")
    ap.add_argument("--reglas", default="motor/reglas_puntaje.yaml")
    args = ap.parse_args(argv)

    reglas = yaml.safe_load(Path(args.reglas).read_text(encoding="utf-8"))
    con = duckdb.connect(args.motor, read_only=True)
    grupos = [f[0] for f in con.execute("SELECT p.grupo_id FROM puntaje p JOIN grupos g USING (grupo_id) WHERE g.n_noticias >= ? "
        "ORDER BY p.puntaje DESC, p.grupo_id LIMIT ?", [args.min_noticias, args.n]).fetchall()]
    con.close()
    paquetes = [evidencia.reunir_evidencia(g, Path(args.motor), Path(args.db), reglas) for g in grupos]

    cliente = llm.cliente_desde_entorno()
    cliente.modelo = args.modelo
    resultado = medir(cliente, paquetes)
    resultado["opciones"] = cliente.opciones
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
