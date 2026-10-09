#!/usr/bin/env python3
"""Compute the human-review metrics from the filled sheets in data/revision/.

Support validity = supported / reviewed. Ambiguous counts as NOT supported (conservative);
the strict-free figure (ambiguous excluded) is reported alongside it.
Precision@5 = share of the system's top 5 that the reviewer marked relevant.
Reads precision5_clave.csv (the system ranking) only at this point, after the blind review.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
REV = RAIZ / "data" / "revision"
SI = {"si", "sí", "s", "yes", "y"}


def _leer(ruta: Path) -> list[dict]:
    with ruta.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _norm(valor: str) -> str:
    return (valor or "").strip().lower()


def validez(filas: list[dict]) -> dict:
    revisadas = [f for f in filas if _norm(f.get("veredicto"))]
    cuenta = {"respaldada": 0, "no respaldada": 0, "ambigua": 0}
    for f in revisadas:
        v = _norm(f["veredicto"])
        if v in cuenta:
            cuenta[v] += 1
    total = sum(cuenta.values())
    resp = cuenta["respaldada"]
    sin_ambiguas = total - cuenta["ambigua"]
    return {
        "total_filas": len(filas), "revisadas": total, **{k.replace(" ", "_"): v for k, v in cuenta.items()},
        "validez": resp / total if total else None,
        "validez_sin_ambiguas": resp / sin_ambiguas if sin_ambiguas else None,
        "no_respaldadas": [f["n"] for f in revisadas if _norm(f["veredicto"]) == "no respaldada"],
    }


def precision5(candidatos: list[dict], clave: list[dict]) -> dict:
    top5 = [c["grupo_id"] for c in sorted(clave, key=lambda c: int(c["rango_sistema"]))[:5]]
    por_id = {c["grupo_id"]: c for c in candidatos}
    relevantes = [g for g in top5 if _norm(por_id.get(g, {}).get("relevante_para_editor (si/no)")) in SI]
    elegidos = {c["grupo_id"] for c in candidatos if _norm(c.get("seleccion_top5 (si/no)")) in SI}
    return {
        "top5_sistema": top5, "relevantes_en_top5": len(relevantes), "precision_at_5": len(relevantes) / 5,
        "coincidencias_con_seleccion": len(elegidos & set(top5)), "elegidos_por_revisor": len(elegidos),
    }


def main() -> int:
    v = validez(_leer(REV / "validez_sustento.csv"))
    p = precision5(_leer(REV / "precision5_candidatos.csv"), _leer(REV / "precision5_clave.csv"))
    pct = lambda x: "n/d" if x is None else f"{x:.1%}"  # noqa: E731
    print(f"Validez del sustento: {v['respaldada']}/{v['revisadas']} = {pct(v['validez'])} "
          f"(ambiguas {v['ambigua']}, no respaldadas {v['no_respaldada']}; sin ambiguas: {pct(v['validez_sin_ambiguas'])})")
    print(f"Filas no respaldadas: {v['no_respaldadas']}")
    print(f"Precision@5: {p['relevantes_en_top5']}/5 = {p['precision_at_5']:.0%}; "
          f"coincidencias con el top 5 del revisor: {p['coincidencias_con_seleccion']}/5")
    return 0


if __name__ == "__main__":
    sys.exit(main())
