#!/usr/bin/env python3
"""
Registro rápido de la bitácora. Escribe en bitacora/*.yaml con fecha y hora de Panamá
y sincroniza con Notion al terminar si NOTION_AUTOSYNC=1 (o si pasas --sync).

  python bitacora.py decision "Usar DuckDB como base local"
  python bitacora.py tarea "Script de descarga de GDELT" --responsable Guille
  python bitacora.py estado TAR-005 "En curso"
  python bitacora.py prueba T07 Falló --observado "El agente siguió la instrucción del artículo"
  python bitacora.py prueba T07 Corregida --correccion "Contenido de fuentes delimitado y validado"
  python bitacora.py resumen
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml
from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent
BITACORA = RAIZ / "bitacora"
PANAMA = timezone(timedelta(hours=-5))
ESTADOS_TAREA = ["Pendiente", "En curso", "Hecho", "Bloqueada"]
ESTADOS_DECISION = ["Propuesta", "Vigente", "Reemplazada"]
ESTADOS_PRUEBA = ["Pendiente", "Pasó", "Falló", "Corregida"]


def ahora() -> str:
    return datetime.now(PANAMA).isoformat(timespec="minutes")


def leer(nombre: str) -> list:
    ruta = BITACORA / f"{nombre}.yaml"
    return (yaml.safe_load(ruta.read_text(encoding="utf-8")) or []) if ruta.exists() else []


def escribir(nombre: str, datos: list) -> None:
    (BITACORA / f"{nombre}.yaml").write_text(
        yaml.safe_dump(datos, allow_unicode=True, sort_keys=False, width=100), encoding="utf-8")


def siguiente_id(items: list, prefijo: str) -> str:
    nums = [int(str(i["id"]).rsplit("-", 1)[-1]) for i in items
            if str(i.get("id", "")).startswith(prefijo + "-")]
    return f"{prefijo}-{(max(nums) if nums else 0) + 1:03d}"


def pedir(valor: str | None, pregunta: str, obligatorio: bool = False) -> str:
    while not valor:
        valor = input(f"{pregunta}: ").strip()
        if valor or not obligatorio:
            break
        print("  Este campo es obligatorio.")
    return valor or ""


def buscar(items: list, ident: str) -> dict:
    for it in items:
        if str(it.get("id")) == ident:
            return it
    sys.exit(f"No existe el ID {ident}.")


# ---------------------------------------------------------------- comandos

def cmd_decision(a) -> None:
    items = leer("decisiones")
    nueva = {
        "id": siguiente_id(items, "DEC"),
        "decision": a.titulo,
        "fecha": ahora(),
        "estado": a.estado,
        "contexto": pedir(a.contexto, "Contexto (qué problema o duda la originó)"),
        "alternativas": pedir(a.alternativas, "Alternativas consideradas"),
        "justificacion": pedir(a.justificacion, "Justificación", obligatorio=True),
        "decidio": a.por or os.getenv("BITACORA_AUTOR", ""),
    }
    items.append(nueva)
    escribir("decisiones", items)
    print(f"Decisión {nueva['id']} registrada.")


def cmd_tarea(a) -> None:
    items = leer("tareas")
    nueva = {"id": siguiente_id(items, "TAR"), "tarea": a.titulo,
             "responsable": a.responsable or os.getenv("BITACORA_AUTOR", ""),
             "estado": a.estado, "fecha": ahora(), "notas": a.notas or ""}
    items.append(nueva)
    escribir("tareas", items)
    print(f"Tarea {nueva['id']} registrada.")


def cmd_estado(a) -> None:
    if a.id.startswith("DEC-"):
        nombre, validos = "decisiones", ESTADOS_DECISION
    else:
        nombre, validos = "tareas", ESTADOS_TAREA
    if a.estado not in validos:
        sys.exit(f"Estado inválido. Opciones: {', '.join(validos)}")
    items = leer(nombre)
    it = buscar(items, a.id)
    it["estado"] = a.estado
    it["fecha"] = ahora()
    if a.notas:
        previas = it.get("notas") or ""
        it["notas"] = (previas + "\n" if previas else "") + f"{ahora()} · {a.notas}"
    escribir(nombre, items)
    print(f"{a.id} -> {a.estado}")


def cmd_prueba(a) -> None:
    items = leer("pruebas")
    it = buscar(items, a.id)
    it["estado"] = a.estado
    it["fecha"] = ahora()
    for campo in ("entrada", "observado", "evidencia", "correccion"):
        valor = getattr(a, campo)
        if valor:
            it[campo] = valor
    detalle = a.observado or a.correccion or ""
    linea = f"{ahora()} · {a.estado}" + (f" · {detalle}" if detalle else "")
    it["historial"] = ((it.get("historial") or "") + "\n" + linea).strip()
    escribir("pruebas", items)
    print(f"{a.id} -> {a.estado}")


def cmd_resumen(_a) -> None:
    tareas, decisiones, pruebas = leer("tareas"), leer("decisiones"), leer("pruebas")
    print(f"Tareas: {len(tareas)} (mínimo exigido: 8)")
    for e in ESTADOS_TAREA:
        print(f"  {e:<10} {sum(1 for t in tareas if t.get('estado') == e)}")
    vigentes = sum(1 for d in decisiones if d.get("estado") == "Vigente")
    print(f"Decisiones: {len(decisiones)} ({vigentes} vigentes; mínimo exigido: 3)")
    print("Pruebas:")
    for p in pruebas:
        print(f"  {p['id']:<4} {p.get('estado', ''):<10} {p.get('prueba', '')}")
    if not any(p.get("estado") == "Corregida" for p in pruebas):
        print("Aviso: el jurado pedirá ver una prueba fallida y su corrección.")


# ---------------------------------------------------------------- main

def main() -> None:
    load_dotenv(RAIZ / ".env")
    comun = argparse.ArgumentParser(add_help=False)
    comun.add_argument("--sync", action="store_true", help="sincronizar con Notion al terminar")

    ap = argparse.ArgumentParser(description="Bitácora del proyecto.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("decision", parents=[comun], help="registrar una decisión")
    d.add_argument("titulo")
    d.add_argument("--contexto")
    d.add_argument("--alternativas")
    d.add_argument("--justificacion")
    d.add_argument("--estado", default="Vigente", choices=ESTADOS_DECISION)
    d.add_argument("--por", help="quién decidió")
    d.set_defaults(fn=cmd_decision)

    t = sub.add_parser("tarea", parents=[comun], help="registrar una tarea")
    t.add_argument("titulo")
    t.add_argument("--responsable")
    t.add_argument("--estado", default="Pendiente", choices=ESTADOS_TAREA)
    t.add_argument("--notas")
    t.set_defaults(fn=cmd_tarea)

    e = sub.add_parser("estado", parents=[comun], help="cambiar estado de una tarea o decisión")
    e.add_argument("id")
    e.add_argument("estado")
    e.add_argument("--notas")
    e.set_defaults(fn=cmd_estado)

    p = sub.add_parser("prueba", parents=[comun], help="registrar resultado de una prueba")
    p.add_argument("id", help="T01 a T10")
    p.add_argument("estado", choices=ESTADOS_PRUEBA)
    p.add_argument("--entrada")
    p.add_argument("--observado")
    p.add_argument("--evidencia", help="ruta a captura o log")
    p.add_argument("--correccion")
    p.set_defaults(fn=cmd_prueba)

    r = sub.add_parser("resumen", help="ver el estado de la bitácora")
    r.set_defaults(fn=cmd_resumen)

    args = ap.parse_args()
    args.fn(args)

    if args.cmd != "resumen" and (getattr(args, "sync", False)
                                  or os.getenv("NOTION_AUTOSYNC") == "1"):
        subprocess.run([sys.executable, str(RAIZ / "notion_sync.py"), "--quiet"], check=False)


if __name__ == "__main__":
    main()
