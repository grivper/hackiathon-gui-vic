#!/usr/bin/env python3
"""Corre el benchmark de desarrollo de 40 consultas (`data/benchmark.jsonl`) contra el
camino real de consulta (`app.data.ask_group_question`, TAR-011 parte 2, tarea B1).

Es una MEDICION, no un portón de calidad: no decide pasar/fallar el build, solo deja
un reporte honesto de cómo se comporta hoy el chat determinista y extractivo contra
las 40 consultas curadas. No corrige debilidades que el benchmark exponga (eso es
decisión aparte) y no toca `data/benchmark.jsonl`.

Limitaciones conocidas y explicitadas en el reporte:
  - El chat (`ask_group_question`) es determinista y extractivo: nunca produce un tipo
    de respuesta "contradiccion". Todo registro con `expected_response_type ==
    "contradiccion"` se cuenta aparte como `contradiccion_no_soportada`, nunca oculto
    dentro de una tasa de acierto que no podría alcanzar.
  - `forbidden_claims` es texto libre: no se puede chequear automáticamente. Queda
    listado para revisión manual humana, nunca verificado por este script.

Lee:
  - data/benchmark.jsonl (--benchmark): 40 registros, ver tests/test_benchmark_schema.py.
  - data/motor.duckdb (--motor), data/senales.duckdb (--senales), data/fichas.jsonl
    (--fichas): solo lectura, pasados tal cual a `ask_group_question`.

Escribe un reporte markdown (por defecto documentacion/evidencia-benchmark.md).
Siempre termina con código 0 (es una medición), salvo que falte algún archivo de
entrada, en cuyo caso termina con código 1 y un mensaje en stderr.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.data import ask_group_question  # noqa: E402

ABSTENTION_MESSAGE = "No hay evidencia validada en esta ficha para responder a esa consulta."

RUTA_BENCHMARK_DEFECTO = "data/benchmark.jsonl"
RUTA_MOTOR_DEFECTO = "data/motor.duckdb"
RUTA_SENALES_DEFECTO = "data/senales.duckdb"
RUTA_FICHAS_DEFECTO = "data/fichas.jsonl"
RUTA_SALIDA_DEFECTO = "documentacion/evidencia-benchmark.md"


# --------------------------------------------------------------------------- carga (I/O)

def load_benchmark(path: Path) -> list[dict]:
    """Lee los registros del benchmark, uno por línea JSON."""
    with Path(path).open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def evaluate_records(
    records: list[dict],
    *,
    ask=ask_group_question,
    motor_path,
    signals_path,
    fichas_path,
) -> list[dict]:
    """Corre cada registro contra `ask` (por defecto `ask_group_question`) y anota el
    resultado. `ask` es inyectable para pruebas sin Ollama ni DuckDB reales."""
    results = []
    for record in records:
        response = ask(
            record.get("target_group_id") or "",
            record["question"],
            motor_path=motor_path,
            signals_path=signals_path,
            fichas_path=fichas_path,
        )
        results.append(score_record(record, response))
    return results


# --------------------------------------------------------------------------- scoring (puro)

def score_record(record: dict, response) -> dict:
    """Anota un único registro contra la respuesta observada del chat. No decide
    pasar/fallar nada; solo describe lo que pasó."""
    expected = record["expected_response_type"]
    observed = "abstencion" if response.abstencion else "respuesta"

    contradiccion_no_soportada = expected == "contradiccion"
    if contradiccion_no_soportada:
        # No existe un tipo de respuesta "contradiccion" en el chat: nunca puede ser
        # type_ok, y se cuenta aparte en vez de mezclarse con los demás fallos.
        type_ok = False
    else:
        type_ok = observed == expected

    required_ids = record.get("required_evidence_ids") or []
    if required_ids:
        presentes = set(response.citas) & set(required_ids)
        required_evidence_recall = len(presentes) / len(required_ids)
    else:
        required_evidence_recall = None

    abstention_clean = (len(response.citas) == 0) if observed == "abstencion" else None

    return {
        "id": record["id"],
        "case": record["case"],
        "expected_response_type": expected,
        "observed_response_type": observed,
        "type_ok": type_ok,
        "contradiccion_no_soportada": contradiccion_no_soportada,
        "required_evidence_recall": required_evidence_recall,
        "abstention_clean": abstention_clean,
        "forbidden_claims": record.get("forbidden_claims") or [],
    }


# --------------------------------------------------------------------------- resumen (puro)

def _rate(values: list[bool]) -> float:
    return sum(1 for v in values if v) / len(values) if values else 0.0


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def summarize(records: list[dict], results: list[dict]) -> dict:
    """Cuentas y tasas globales, por `expected_response_type` y por `case`."""
    total = len(results)

    def _group_by(key: str) -> dict:
        grupos: dict[str, list[dict]] = {}
        for r in results:
            grupos.setdefault(r[key], []).append(r)
        return {
            nombre: {
                "count": len(items),
                "type_ok_rate": _rate([i["type_ok"] for i in items]),
            }
            for nombre, items in grupos.items()
        }

    recall_respuesta = [
        r["required_evidence_recall"]
        for r in results
        if r["expected_response_type"] == "respuesta" and r["required_evidence_recall"] is not None
    ]
    abstenciones = [r for r in results if r["abstention_clean"] is not None]

    return {
        "total": total,
        "overall_type_ok_rate": _rate([r["type_ok"] for r in results]),
        "mean_recall_respuesta": _mean(recall_respuesta),
        "abstention_clean_rate": _rate([r["abstention_clean"] for r in abstenciones]),
        "contradiccion_no_soportada_count": sum(1 for r in results if r["contradiccion_no_soportada"]),
        "failing_ids": [r["id"] for r in results if not r["type_ok"]],
        "by_expected_response_type": _group_by("expected_response_type"),
        "by_case": _group_by("case"),
    }


# --------------------------------------------------------------------------- reporte (puro)

def render_report(records: list[dict], results: list[dict], summary: dict, *, manifest_hash: str) -> str:
    lineas = [
        "# Evidencia del benchmark de desarrollo (TAR-011, B1)",
        "",
        f"- Manifiesto de datos (snapshot): `{manifest_hash}`",
        f"- Registros evaluados: {summary['total']}",
        f"- Acierto global de tipo de respuesta (type_ok): {100 * summary['overall_type_ok_rate']:.1f}%",
        f"- Recall promedio de evidencia requerida (casos `respuesta`): "
        f"{100 * summary['mean_recall_respuesta']:.1f}%",
        f"- Tasa de abstención limpia (sin citas) sobre las respuestas observadas como "
        f"abstención: {100 * summary['abstention_clean_rate']:.1f}%",
        f"- Casos `contradiccion` (sin soporte posible en el chat actual): "
        f"{summary['contradiccion_no_soportada_count']}",
        "",
        "**Estas métricas son medidas automáticas y deterministas/extractivas del chat "
        "actual** (`app.data.ask_group_question`); no evalúan calidad editorial ni "
        "verifican `forbidden_claims`, que requieren revisión humana (ver sección al "
        "final).",
        "",
        "## Resumen por tipo de respuesta esperado",
        "",
        "| tipo esperado | n | acierto de tipo |",
        "|---|---|---|",
    ]
    for tipo, datos in sorted(summary["by_expected_response_type"].items()):
        lineas.append(f"| {tipo} | {datos['count']} | {100 * datos['type_ok_rate']:.1f}% |")

    lineas += ["", "## Resumen por caso (`case`)", "", "| case | n | acierto de tipo |", "|---|---|---|"]
    for caso, datos in sorted(summary["by_case"].items()):
        lineas.append(f"| {caso} | {datos['count']} | {100 * datos['type_ok_rate']:.1f}% |")

    lineas += [
        "",
        "## Detalle por registro",
        "",
        "| id | case | esperado | observado | type_ok | recall evidencia | abstención limpia |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in results:
        recall = "n/a" if r["required_evidence_recall"] is None else f"{100 * r['required_evidence_recall']:.0f}%"
        limpia = "n/a" if r["abstention_clean"] is None else ("sí" if r["abstention_clean"] else "no")
        lineas.append(
            f"| {r['id']} | {r['case']} | {r['expected_response_type']} | {r['observed_response_type']} | "
            f"{'sí' if r['type_ok'] else 'no'} | {recall} | {limpia} |"
        )

    lineas += ["", "## Revisión manual pendiente", "", (
        "`forbidden_claims` es texto libre y no se verifica automáticamente. Cada "
        "afirmación listada abajo requiere que una persona confirme que el borrador "
        "actual (o uno futuro) no la contiene."
    ), ""]
    con_prohibidas = [r for r in results if r["forbidden_claims"]]
    if not con_prohibidas:
        lineas.append("Ningún registro evaluado declara `forbidden_claims`.")
    else:
        for r in con_prohibidas:
            lineas.append(f"- **{r['id']}** ({r['case']}):")
            for claim in r["forbidden_claims"]:
                lineas.append(f"  - {claim}")
    lineas.append("")

    if summary["failing_ids"]:
        lineas += ["## Registros con type_ok=False", "", ", ".join(summary["failing_ids"]), ""]

    return "\n".join(lineas)


# --------------------------------------------------------------------------- main (I/O)

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Corre el benchmark de desarrollo contra ask_group_question y reporta resultados."
    )
    parser.add_argument("--benchmark", default=RUTA_BENCHMARK_DEFECTO, help="JSONL con las consultas del benchmark")
    parser.add_argument("--motor", default=RUTA_MOTOR_DEFECTO, help="base DuckDB del motor")
    parser.add_argument("--senales", default=RUTA_SENALES_DEFECTO, help="base DuckDB de señales")
    parser.add_argument("--fichas", default=RUTA_FICHAS_DEFECTO, help="JSONL de fichas")
    parser.add_argument("--salida", default=RUTA_SALIDA_DEFECTO, help="ruta del reporte markdown de salida")
    args = parser.parse_args(argv)

    ruta_benchmark = Path(args.benchmark)
    ruta_motor = Path(args.motor)
    ruta_senales = Path(args.senales)
    ruta_fichas = Path(args.fichas)
    ruta_salida = Path(args.salida)

    for ruta, nombre in (
        (ruta_benchmark, "benchmark"),
        (ruta_motor, "motor"),
        (ruta_senales, "señales"),
        (ruta_fichas, "fichas"),
    ):
        if not ruta.exists():
            print(f"Error fatal: no existe el archivo de {nombre} {ruta}", file=sys.stderr)
            return 1

    records = load_benchmark(ruta_benchmark)
    results = evaluate_records(
        records,
        motor_path=ruta_motor,
        signals_path=ruta_senales,
        fichas_path=ruta_fichas,
    )
    summary = summarize(records, results)
    manifest_hash = records[0].get("snapshot_manifest_sha256", "") if records else ""
    reporte = render_report(records, results, summary, manifest_hash=manifest_hash)

    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    ruta_salida.write_text(reporte, encoding="utf-8")

    print(f"Benchmark evaluado: {summary['total']} registros -> {ruta_salida}")
    print(f"  acierto de tipo global: {100 * summary['overall_type_ok_rate']:.1f}%")
    print(f"  recall promedio (respuesta): {100 * summary['mean_recall_respuesta']:.1f}%")
    print(f"  abstención limpia: {100 * summary['abstention_clean_rate']:.1f}%")
    if summary["failing_ids"]:
        print(f"  registros con type_ok=False: {', '.join(summary['failing_ids'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
