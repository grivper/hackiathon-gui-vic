#!/usr/bin/env python3
"""
Sincroniza la bitácora del proyecto con Notion.

La fuente de verdad son los archivos del repositorio:
  bitacora/tareas.yaml, decisiones.yaml, pruebas.yaml, catalogo.yaml
  bitacora/paginas/*.md
  data/manifest.json  (catálogo de datos, si existe; reemplaza a catalogo.yaml)
  data/fichas.jsonl   (casos y evidencias, si existe)

Notion es un espejo: el script crea la estructura de las 8 páginas si no existe
y actualiza solo lo que cambió. Para migrar a otro espacio basta con cambiar
NOTION_TOKEN y NOTION_ROOT_PAGE_ID en .env y volver a ejecutarlo.

Uso:
  python notion_sync.py             # crea la estructura si falta y sincroniza
  python notion_sync.py --dry-run   # valida los archivos locales sin llamar a Notion
  python notion_sync.py --quiet     # sin salida (lo usa el hook de git)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent
BITACORA = RAIZ / "bitacora"
PAGINAS_MD = BITACORA / "paginas"
ESTADO = RAIZ / ".notion_state.json"
API = "https://api.notion.com/v1"
NOTION_VERSION = "2025-09-03"
MAX_TEXTO = 2000    # límite de Notion por objeto de texto
MAX_BLOQUES = 100   # límite de Notion por solicitud de bloques
SILENCIO = False


def log(msg: str) -> None:
    if not SILENCIO:
        print(msg)


def _sel(*opciones):
    return {"select": {"options": [{"name": o} for o in opciones]}}


_TXT = {"rich_text": {}}
_FECHA = {"date": {}}
_NUM = {"number": {"format": "number"}}

# Páginas en orden de creación (el padre siempre antes que el hijo).
PAGINAS = [
    {"clave": "inicio", "titulo": "1 · Inicio del reto", "md": "inicio.md"},
    {"clave": "plan", "titulo": "2 · Plan y decisiones"},
    {"clave": "catalogo", "titulo": "3 · Catálogo de datos"},
    {"clave": "diseno", "titulo": "4 · Diseño de solución", "md": "diseno.md"},
    {"clave": "casos", "titulo": "5 · Casos y evidencias"},
    {"clave": "pruebas", "titulo": "6 · Pruebas y métricas"},
    {"clave": "metricas", "titulo": "Métricas de la ejecución", "md": "metricas.md", "padre": "pruebas"},
    {"clave": "riesgos", "titulo": "7 · Riesgos y ética", "md": "riesgos.md"},
    {"clave": "presentacion", "titulo": "8 · Presentación al jurado", "md": "presentacion.md"},
]

# Bases de datos: página donde viven, esquema y mapeo de campos locales -> propiedades.
BASES = {
    "tareas": {
        "pagina": "plan", "titulo": "Tareas", "archivo": "tareas.yaml",
        "esquema": {
            "Tarea": {"title": {}}, "ID": _TXT, "Responsable": _TXT,
            "Estado": _sel("Pendiente", "En curso", "Hecho", "Bloqueada"),
            "Fecha": _FECHA, "Notas": _TXT,
            "Tipo": _sel("\u00c9pica", "Tarea"), "\u00c9pica": _TXT, "Progreso": _TXT,
        },
        "campos": {"id": "ID", "tarea": "Tarea", "responsable": "Responsable",
                   "estado": "Estado", "fecha": "Fecha", "notas": "Notas",
                   "tipo": "Tipo", "epica": "\u00c9pica", "progreso": "Progreso"},
    },
    "decisiones": {
        "pagina": "plan", "titulo": "Decisiones", "archivo": "decisiones.yaml",
        "esquema": {
            "Decisión": {"title": {}}, "ID": _TXT, "Fecha": _FECHA,
            "Estado": _sel("Propuesta", "Vigente", "Reemplazada"),
            "Contexto": _TXT, "Alternativas": _TXT, "Justificación": _TXT, "Decidió": _TXT,
        },
        "campos": {"id": "ID", "decision": "Decisión", "fecha": "Fecha", "estado": "Estado",
                   "contexto": "Contexto", "alternativas": "Alternativas",
                   "justificacion": "Justificación", "decidio": "Decidió"},
    },
    "catalogo": {
        "pagina": "catalogo", "titulo": "Fuentes", "archivo": "catalogo.yaml",
        "esquema": {
            "Fuente": {"title": {}}, "ID": _TXT, "URL": {"url": {}},
            "Fecha extracción": _FECHA, "Cobertura": _TXT, "Campos": _TXT,
            "Licencia": _TXT, "Transformaciones": _TXT, "SHA-256": _TXT, "Registros": _NUM,
        },
        "campos": {"id": "ID", "fuente": "Fuente", "url": "URL",
                   "fecha_extraccion": "Fecha extracción", "cobertura": "Cobertura",
                   "campos": "Campos", "licencia": "Licencia",
                   "transformaciones": "Transformaciones", "sha256": "SHA-256",
                   "registros": "Registros"},
    },
    "casos": {
        "pagina": "casos", "titulo": "Fichas",
        "esquema": {
            "Caso": {"title": {}}, "ID": _TXT,
            "Modalidad": _sel("TVN · principal", "TVN · digital", "Banca"),
            "Fuentes": _TXT, "Puntaje": _NUM, "Componentes": _TXT,
            "Prioridad": _sel("Alta", "Media", "Baja"),
            "Estado evidencia": _sel("Insuficiente", "Parcial", "Suficiente para el borrador"),
            "Estado revisión": _sel("Nuevo", "En revisión", "Requiere evidencia",
                                    "Aprobado como borrador", "Descartado"),
            "Revisor": _TXT,
        },
    },
    "pruebas": {
        "pagina": "pruebas", "titulo": "Matriz de pruebas", "archivo": "pruebas.yaml",
        "esquema": {
            "Prueba": {"title": {}}, "ID": _TXT,
            "Estado": _sel("Pendiente", "Pasó", "Falló", "Corregida"),
            "Entrada": _TXT, "Resultado esperado": _TXT, "Resultado observado": _TXT,
            "Evidencia": _TXT, "Corrección": _TXT, "Historial": _TXT, "Fecha": _FECHA,
        },
        "campos": {"id": "ID", "prueba": "Prueba", "estado": "Estado", "entrada": "Entrada",
                   "esperado": "Resultado esperado", "observado": "Resultado observado",
                   "evidencia": "Evidencia", "correccion": "Corrección",
                   "historial": "Historial", "fecha": "Fecha"},
    },
}


# ---------------------------------------------------------------- utilidades

def sha(obj) -> str:
    texto = obj if isinstance(obj, str) else json.dumps(obj, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def plano(valor):
    """Convierte listas, dicts y fechas de YAML/JSON en texto para Notion."""
    if valor is None:
        return None
    if hasattr(valor, "isoformat"):
        return valor.isoformat()
    if isinstance(valor, list):
        return ", ".join(str(plano(v)) for v in valor)
    if isinstance(valor, dict):
        return " · ".join(f"{k}={plano(v)}" for k, v in valor.items())
    return valor


def rt(texto) -> list:
    texto = "" if texto is None else str(texto)
    texto = texto[: MAX_TEXTO * 100]
    return [{"type": "text", "text": {"content": texto[i:i + MAX_TEXTO]}}
            for i in range(0, len(texto), MAX_TEXTO)]


def rt_md(texto: str) -> list:
    """Texto con **negritas** de Markdown."""
    salida = []
    for i, parte in enumerate(re.split(r"\*\*(.+?)\*\*", texto)):
        for obj in rt(parte):
            if i % 2 == 1:
                obj["annotations"] = {"bold": True}
            salida.append(obj)
    return salida


def valor_propiedad(tipo: str, valor):
    valor = plano(valor)
    if tipo == "title":
        return {"title": rt(valor)}
    if tipo == "rich_text":
        return {"rich_text": rt(valor)}
    if tipo == "select":
        if valor in (None, ""):
            return {"select": None}
        nombre = str(valor).replace(",", " ")
        return {"select": {"name": nombre[:1].upper() + nombre[1:]}}
    if tipo == "number":
        return {"number": None if valor in (None, "") else float(valor)}
    if tipo == "url":
        return {"url": valor or None}
    if tipo == "date":
        return {"date": {"start": str(valor)} if valor else None}
    raise ValueError(f"Tipo de propiedad no soportado: {tipo}")


def md_a_bloques(md: str) -> list:
    """Markdown simple -> bloques de Notion (títulos, listas, citas, código, separadores)."""
    bloques, codigo, en_codigo = [], [], False

    def cerrar_codigo():
        bloques.append({"object": "block", "type": "code",
                        "code": {"rich_text": rt("\n".join(codigo)), "language": "plain text"}})

    for linea in md.splitlines():
        if linea.strip().startswith("```"):
            if en_codigo:
                cerrar_codigo()
                codigo = []
            en_codigo = not en_codigo
            continue
        if en_codigo:
            codigo.append(linea)
            continue
        l = linea.strip()
        if not l:
            continue
        if l in ("---", "***"):
            bloques.append({"object": "block", "type": "divider", "divider": {}})
            continue
        m = re.match(r"^(#{1,3}) (.*)", l)
        if m:
            tipo, texto = f"heading_{len(m.group(1))}", m.group(2)
        elif re.match(r"^[-*] ", l):
            tipo, texto = "bulleted_list_item", l[2:]
        elif re.match(r"^\d+[.)] ", l):
            tipo, texto = "numbered_list_item", l.split(" ", 1)[1]
        elif l.startswith("> "):
            tipo, texto = "quote", l[2:]
        else:
            tipo, texto = "paragraph", l
        bloques.append({"object": "block", "type": tipo, tipo: {"rich_text": rt_md(texto)}})
    if en_codigo and codigo:
        cerrar_codigo()
    return bloques


def normalizar_id(valor: str) -> str:
    """Acepta un ID con o sin guiones, o la URL completa de la página."""
    hexa = re.findall(r"[0-9a-fA-F]{32}", valor.replace("-", ""))
    if not hexa:
        sys.exit(f"NOTION_ROOT_PAGE_ID no parece un ID de Notion: {valor}")
    h = hexa[-1].lower()
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


# ---------------------------------------------------------------- cliente Notion

class Notion:
    def __init__(self, token: str):
        self.s = requests.Session()
        self.s.headers.update({
            "Authorization": f"Bearer {token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        })

    def req(self, metodo: str, ruta: str, cuerpo: dict | None = None) -> dict:
        for intento in range(5):
            time.sleep(0.35)  # Notion permite ~3 solicitudes por segundo
            r = self.s.request(metodo, API + ruta, json=cuerpo, timeout=30)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(float(r.headers.get("Retry-After", 2 ** intento)))
                continue
            if r.status_code == 401:
                raise RuntimeError("Token inválido (401). Revisa NOTION_TOKEN en .env.")
            if r.status_code == 404:
                raise RuntimeError(
                    f"No se encontró {ruta} (404). ¿La página raíz está conectada a la "
                    "integración? Si borraste páginas en Notion, elimina .notion_state.json.")
            if not r.ok:
                raise RuntimeError(f"{metodo} {ruta} -> {r.status_code}: {r.text[:500]}")
            return r.json() if r.content else {}
        raise RuntimeError(f"{metodo} {ruta}: demasiados reintentos")

    def hijos(self, bloque_id: str) -> list[str]:
        ids, cursor = [], None
        while True:
            q = "?page_size=100" + (f"&start_cursor={cursor}" if cursor else "")
            res = self.req("GET", f"/blocks/{bloque_id}/children{q}")
            ids += [b["id"] for b in res["results"]]
            if not res.get("has_more"):
                return ids
            cursor = res["next_cursor"]

    def agregar_bloques(self, bloque_id: str, bloques: list) -> None:
        for i in range(0, len(bloques), MAX_BLOQUES):
            self.req("PATCH", f"/blocks/{bloque_id}/children",
                     {"children": bloques[i:i + MAX_BLOQUES]})

    def reemplazar_contenido(self, pagina_id: str, bloques: list) -> None:
        for b in self.hijos(pagina_id):
            self.req("DELETE", f"/blocks/{b}")
        self.agregar_bloques(pagina_id, bloques)


# ---------------------------------------------------------------- estado local

def cargar_estado(raiz: str) -> dict:
    if ESTADO.exists():
        est = json.loads(ESTADO.read_text(encoding="utf-8"))
        if est.get("raiz") == raiz:
            return est
        respaldo = ESTADO.with_name(f".notion_state.{est.get('raiz', 'anterior')[:8]}.json")
        ESTADO.rename(respaldo)
        log(f"Página raíz distinta: el estado anterior quedó en {respaldo.name}. "
            "Se creará la estructura en el nuevo destino.")
    return {"raiz": raiz, "paginas": {}, "bases": {}, "hashes": {}}


def guardar_estado(est: dict) -> None:
    ESTADO.write_text(json.dumps(est, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------- carga de archivos locales

def datos_dir() -> Path:
    return RAIZ / os.getenv("DATA_DIR", "data")


def leer_yaml(nombre: str) -> list:
    ruta = BITACORA / nombre
    if not ruta.exists():
        return []
    return yaml.safe_load(ruta.read_text(encoding="utf-8")) or []


def mapear(items: list, campos: dict) -> list:
    return [{prop: it.get(k) for k, prop in campos.items() if k in it} for it in items]


def prioridad(puntaje):
    if puntaje in (None, ""):
        return None
    p = float(puntaje)
    return "Baja" if p < 40 else "Media" if p < 70 else "Alta"


def cuerpo_ficha(f: dict) -> str:
    partes = []
    if f.get("alcance"):
        partes.append(f"> {f['alcance']}")
    if f.get("borrador"):
        partes += ["## Borrador", str(f["borrador"])]
    if f.get("afirmaciones"):
        partes.append("## Afirmaciones y citas")
        for a in f["afirmaciones"]:
            if isinstance(a, dict):
                cita = a.get("id_evidencia") or a.get("cita") or "SIN CITA"
                campo = f" · {a['campo']}" if a.get("campo") else ""
                partes.append(f"- [{a.get('tipo', '?')}] {a.get('texto', '')} ({cita}{campo})")
            else:
                partes.append(f"- {a}")
    if f.get("vacios"):
        partes.append("## Pendiente de verificar")
        partes += [f"- {v}" for v in f["vacios"]]
    return "\n".join(partes)


def cargar_casos() -> list:
    ruta = datos_dir() / "fichas.jsonl"
    if not ruta.exists():
        return []
    casos = []
    for n, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
        if not linea.strip():
            continue
        try:
            f = json.loads(linea)
        except json.JSONDecodeError as e:
            log(f"  ! fichas.jsonl línea {n} inválida, se omite: {e}")
            continue
        casos.append({
            "ID": f.get("id_caso"), "Caso": f.get("titulo") or f.get("id_caso"),
            "Modalidad": f.get("modalidad"), "Fuentes": f.get("ids_fuente"),
            "Puntaje": f.get("puntaje"), "Componentes": f.get("componentes"),
            "Prioridad": f.get("prioridad") or prioridad(f.get("puntaje")),
            "Estado evidencia": f.get("estado_evidencia"),
            "Estado revisión": f.get("estado_revision"), "Revisor": f.get("revisor"),
            "_cuerpo": cuerpo_ficha(f),
        })
    return casos


def cargar_catalogo() -> list:
    manifest = datos_dir() / "manifest.json"
    if manifest.exists():
        fuentes = json.loads(manifest.read_text(encoding="utf-8")).get("fuentes")
        if fuentes:
            return mapear(fuentes, BASES["catalogo"]["campos"])
    return mapear(leer_yaml("catalogo.yaml"), BASES["catalogo"]["campos"])


def progreso_epicas(items: list) -> list:
    """Deriva Progreso y Estado de cada \u00c9pica a partir de sus tareas hijas.

    No muta la lista de entrada: devuelve copias con los campos a\u00f1adidos.
    """
    items = [dict(it) for it in items]
    hijos_por_epica: dict[str, list] = {}
    for it in items:
        if it.get("tipo") == "Tarea" and it.get("epica"):
            hijos_por_epica.setdefault(it["epica"], []).append(it)

    for it in items:
        if it.get("tipo") != "\u00c9pica":
            continue
        hijos = hijos_por_epica.get(it.get("id"), [])
        total = len(hijos)
        hechas = sum(1 for h in hijos if h.get("estado") == "Hecho")
        pct = round(100 * hechas / total) if total else 0
        llenas = round(pct / 10)
        barra = "\u2588" * llenas + "\u2591" * (10 - llenas)
        it["progreso"] = f"{barra} {pct}% ({hechas}/{total})"

        if total == 0:
            it["estado"] = "Pendiente"
        elif all(h.get("estado") == "Hecho" for h in hijos):
            it["estado"] = "Hecho"
        elif any(h.get("estado") in ("En curso", "Hecho") for h in hijos):
            it["estado"] = "En curso"
        elif any(h.get("estado") == "Bloqueada" for h in hijos):
            it["estado"] = "Bloqueada"
        else:
            it["estado"] = "Pendiente"
    return items


def cargar_todo() -> dict:
    datos = {}
    for clave in ("tareas", "decisiones", "pruebas"):
        crudos = leer_yaml(BASES[clave]["archivo"])
        if clave == "tareas":
            crudos = progreso_epicas(crudos)
        datos[clave] = mapear(crudos, BASES[clave]["campos"])
    datos["catalogo"] = cargar_catalogo()
    datos["casos"] = cargar_casos()
    return datos


def validar(datos: dict) -> int:
    errores = 0
    for clave, regs in datos.items():
        vistos = set()
        for r in regs:
            ident = r.get("ID")
            if not ident:
                log(f"  ! {clave}: registro sin ID, se omitirá: {r}")
                errores += 1
            elif ident in vistos:
                log(f"  ! {clave}: ID duplicado {ident}")
                errores += 1
            vistos.add(ident)

    ids_tareas = {r.get("ID") for r in datos.get("tareas", [])}
    for r in datos.get("tareas", []):
        epica = r.get("Épica")
        if epica and epica not in ids_tareas:
            log(f"  ! tareas: {r.get('ID')} referencia la épica inexistente {epica}")
            errores += 1
    return errores


# ---------------------------------------------------------------- sincronización

def pagina_padre_base(est: dict, clave: str, base: dict) -> str:
    """P\u00e1gina donde debe vivir una base. "tareas" se mueve a
    NOTION_TAREAS_PAGE_ID si est\u00e1 configurada; el resto sigue bajo su
    p\u00e1gina habitual."""
    if clave == "tareas" and "tareas_pagina" in est["paginas"]:
        return est["paginas"]["tareas_pagina"]
    return est["paginas"][base["pagina"]]


def asegurar_estructura(n: Notion, est: dict) -> None:
    for p in PAGINAS:
        if p["clave"] in est["paginas"]:
            continue
        padre = est["raiz"] if "padre" not in p else est["paginas"][p["padre"]]
        res = n.req("POST", "/pages", {
            "parent": {"page_id": padre},
            "properties": {"title": {"title": rt(p["titulo"])}},
        })
        est["paginas"][p["clave"]] = res["id"]
        guardar_estado(est)
        log(f"  + página {p['titulo']}")

    for clave, base in BASES.items():
        # La base "tareas" puede vivir en una p\u00e1gina distinta de "plan" si se
        # configur\u00f3 NOTION_TAREAS_PAGE_ID (ver pagina_padre_base). Si ya exist\u00eda
        # con otro padre, se archiva y se recrea en el destino nuevo (migraci\u00f3n).
        padre_pagina = pagina_padre_base(est, clave, base)
        if clave in est["bases"]:
            if est["bases"][clave].get("pagina_padre") != padre_pagina:
                viejo_id = est["bases"][clave]["database_id"]
                n.req("PATCH", f"/databases/{viejo_id}", {"in_trash": True})
                del est["bases"][clave]
                guardar_estado(est)
                log(f"  ~ base {base['titulo']} archivada (cambio de p\u00e1gina), se recrea")
            else:
                continue
        res = n.req("POST", "/databases", {
            "parent": {"type": "page_id", "page_id": padre_pagina},
            "title": rt(base["titulo"]),
            "is_inline": True,
            "initial_data_source": {"properties": base["esquema"]},
        })
        fuentes = res.get("data_sources") or n.req("GET", f"/databases/{res['id']}").get("data_sources")
        est["bases"][clave] = {"database_id": res["id"], "data_source_id": fuentes[0]["id"],
                               "pagina_padre": padre_pagina}
        guardar_estado(est)
        log(f"  + base {base['titulo']}")


def filas_existentes(n: Notion, data_source_id: str) -> dict:
    mapa, cursor = {}, None
    while True:
        cuerpo = {"page_size": 100}
        if cursor:
            cuerpo["start_cursor"] = cursor
        res = n.req("POST", f"/data_sources/{data_source_id}/query", cuerpo)
        for pg in res["results"]:
            ident = "".join(t.get("plain_text", "")
                            for t in pg["properties"].get("ID", {}).get("rich_text", []))
            if ident:
                mapa[ident] = pg["id"]
        if not res.get("has_more"):
            return mapa
        cursor = res["next_cursor"]


def sync_base(n: Notion, est: dict, clave: str, registros: list) -> tuple[int, int]:
    base = BASES[clave]
    ds = est["bases"][clave]["data_source_id"]
    hashes = est["hashes"].setdefault(clave, {})
    existentes = filas_existentes(n, ds)
    creados = actualizados = 0

    for reg in registros:
        ident = str(reg.get("ID") or "")
        if not ident:
            continue
        cuerpo_md = reg.get("_cuerpo")
        props = {nombre: valor_propiedad(next(iter(defin)), reg[nombre])
                 for nombre, defin in base["esquema"].items() if nombre in reg}
        h = sha([props, cuerpo_md])
        if ident in existentes and hashes.get(ident) == h:
            continue

        if ident in existentes:
            pid = existentes[ident]
            n.req("PATCH", f"/pages/{pid}", {"properties": props})
            if cuerpo_md is not None:
                n.reemplazar_contenido(pid, md_a_bloques(cuerpo_md))
            actualizados += 1
        else:
            bloques = md_a_bloques(cuerpo_md) if cuerpo_md else []
            cuerpo = {"parent": {"type": "data_source_id", "data_source_id": ds},
                      "properties": props}
            if bloques:
                cuerpo["children"] = bloques[:MAX_BLOQUES]
            res = n.req("POST", "/pages", cuerpo)
            if len(bloques) > MAX_BLOQUES:
                n.agregar_bloques(res["id"], bloques[MAX_BLOQUES:])
            creados += 1
        hashes[ident] = h
        guardar_estado(est)
    return creados, actualizados


def sync_paginas(n: Notion, est: dict) -> int:
    hashes = est["hashes"].setdefault("_paginas", {})
    cambios = 0
    for p in PAGINAS:
        ruta = PAGINAS_MD / p.get("md", "")
        if "md" not in p or not ruta.exists():
            continue
        md = ruta.read_text(encoding="utf-8")
        h = sha(md)
        if hashes.get(p["clave"]) == h:
            continue
        n.reemplazar_contenido(est["paginas"][p["clave"]], md_a_bloques(md))
        hashes[p["clave"]] = h
        guardar_estado(est)
        cambios += 1
        log(f"  ~ página {p['titulo']}")
    return cambios


def main() -> None:
    global SILENCIO
    ap = argparse.ArgumentParser(description="Sincroniza la bitácora con Notion.")
    ap.add_argument("--dry-run", action="store_true", help="validar sin llamar a Notion")
    ap.add_argument("--quiet", action="store_true", help="sin salida")
    args = ap.parse_args()
    SILENCIO = args.quiet
    load_dotenv(RAIZ / ".env", override=True)

    datos = cargar_todo()
    errores = validar(datos)
    if args.dry_run:
        for clave, regs in datos.items():
            print(f"{clave:<11} {len(regs):>3} registros")
        print("Sin errores." if not errores else f"{errores} advertencias.")
        return

    token, raiz = os.getenv("NOTION_TOKEN"), os.getenv("NOTION_ROOT_PAGE_ID")
    if not token or not raiz:
        sys.exit("Falta NOTION_TOKEN o NOTION_ROOT_PAGE_ID en .env")

    n = Notion(token)
    est = cargar_estado(normalizar_id(raiz))
    tareas_pagina = os.getenv("NOTION_TAREAS_PAGE_ID")
    if tareas_pagina:
        est["paginas"]["tareas_pagina"] = normalizar_id(tareas_pagina)
        guardar_estado(est)
    try:
        asegurar_estructura(n, est)
        sync_paginas(n, est)
        for clave, regs in datos.items():
            c, a = sync_base(n, est, clave, regs)
            if c or a:
                log(f"  {clave}: {c} nuevos, {a} actualizados")
    except RuntimeError as e:
        sys.exit(f"Error: {e}")
    log("Notion sincronizado.")


if __name__ == "__main__":
    main()
