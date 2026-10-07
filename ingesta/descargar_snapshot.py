#!/usr/bin/env python3
"""
Descarga las fuentes públicas del reto y genera un snapshot con el contrato de la sección 7.

Dos fases separadas:
  1. Descarga: guarda las respuestas originales en data/raw/ sin modificarlas.
  2. Procesamiento: lee TODO lo que hay en data/raw/ y genera data/processed/ y el manifest.
     Es determinista y no necesita internet (--solo-procesar).

Salida en data/:
  raw/tvn/rss_<fecha>.xml          cada captura del RSS (se acumulan; el RSS no guarda histórico)
  raw/gdelt/<consulta>_<ventana>.json
  raw/worldbank/<indicador>.json
  raw/usgs/eventos.json
  processed/noticias.csv           TVN + GDELT, deduplicado por URL
  processed/fuentes.json           medios presentes y condiciones de uso
  processed/indicadores.csv        cuadrícula completa país × indicador × año, con nulos
  processed/eventos.geojson        sismos USGS normalizados
  processed/excluidos.csv          registros descartados y motivo
  diccionario.md                   significado de cada campo
  manifest.json                    versión, consultas, conteos, SHA-256 y transformaciones

Uso:
  python ingesta/descargar_snapshot.py                          # todas las fuentes
  python ingesta/descargar_snapshot.py --solo tvn gdelt
  python ingesta/descargar_snapshot.py --desde 2026-09-06 --hasta 2026-10-06
  python ingesta/descargar_snapshot.py --solo-procesar          # sin internet
"""
from __future__ import annotations

import argparse
import calendar
import csv
import hashlib
import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import feedparser
import requests
import yaml

RAIZ = Path(__file__).resolve().parent.parent
CONFIG = Path(__file__).resolve().parent / "config.yaml"
UTC = timezone.utc
UA = "hackiathon-tvn-snapshot/0.1 (prototipo academico)"
PAUSA_EXTRA = True  # las pruebas lo desactivan

COLUMNAS_NOTICIAS = ["id_noticia", "titulo", "url", "medio", "idioma", "fecha_publicacion",
                     "fecha_deteccion", "fecha_extraccion", "tema", "origen", "alcance_texto"]
# Prioridad de origen al fusionar duplicados por URL: el valor mas bajo gana (titulo, idioma, medio).
ORDEN_ORIGEN = {"tvn_rss": 0, "tvn_sitemap": 1, "gdelt": 2}
NS_SITEMAP = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
NS_IMAGE = "{http://www.google.com/schemas/sitemap-image/1.1}"
PATRON_SLUG_SUFIJO = re.compile(r"_\d+_\d+$")
COLUMNAS_INDICADORES = ["id_evidencia", "pais_iso3", "indicador_id", "indicador_nombre", "anio",
                        "valor", "unidad", "observacion", "fuente_url", "fecha_extraccion",
                        "licencia"]
IDIOMAS = {"spanish": "es", "english": "en", "portuguese": "pt", "french": "fr",
           "german": "de", "italian": "it", "chinese": "zh", "japanese": "ja"}


# ---------------------------------------------------------------- utilidades

def log(msg: str) -> None:
    print(msg, flush=True)


def ahora() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def iso(dt: datetime | None) -> str | None:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ") if dt else None


def sello(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(65536), b""):
            h.update(bloque)
    return h.hexdigest()


def guardar_json(ruta: Path, obj) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def leer_json(ruta: Path):
    return json.loads(ruta.read_text(encoding="utf-8"))


def obtener(url: str, params: dict | None = None) -> requests.Response:
    """GET con reintentos ante 429, errores 5xx o fallas de red."""
    ultimo = None
    for intento in range(3):
        try:
            r = requests.get(url, params=params, headers={"User-Agent": UA}, timeout=60)
            if r.status_code == 429 or r.status_code >= 500:
                ultimo = r
                time.sleep(10 * (intento + 1))
                continue
            return r
        except requests.RequestException as e:
            if intento == 2:
                raise
            log(f"    reintento por error de red: {e}")
            time.sleep(5 * (intento + 1))
    return ultimo


def normalizar_url(url: str) -> str:
    """Clave de deduplicación: sin esquema, sin www, sin parámetros de rastreo ni barra final."""
    p = urlsplit(url.strip())
    q = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
         if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid", "outputtype"}]
    host = p.netloc.lower().removeprefix("www.")
    ruta = p.path.rstrip("/") or "/"
    return urlunsplit(("", host, ruta, urlencode(q), "")).lstrip("/")


def url_valida(url: str | None) -> bool:
    if not url:
        return False
    p = urlsplit(url.strip())
    return p.scheme in ("http", "https") and bool(p.netloc)


def dominio(url: str) -> str:
    return urlsplit(url.strip()).netloc.lower().removeprefix("www.")


def id_noticia(url: str) -> str:
    return "N-" + hashlib.sha1(normalizar_url(url).encode("utf-8")).hexdigest()[:12]


def fecha_gdelt(texto: str | None) -> datetime | None:
    try:
        return datetime.strptime(texto, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
    except (TypeError, ValueError):
        return None


def fecha_iso_entrada(texto: str) -> datetime:
    dt = datetime.fromisoformat(texto)
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _prioridad_origen(origen: str) -> int:
    """La prioridad del mejor origen presente (tvn_rss < tvn_sitemap < gdelt < otros)."""
    return min((ORDEN_ORIGEN.get(o, len(ORDEN_ORIGEN)) for o in origen.split("|")),
               default=len(ORDEN_ORIGEN))


def _lastmod_iso(texto: str | None) -> str | None:
    """Normaliza un lastmod de sitemap (con offset o 'Z') a ISO 8601 UTC."""
    if not texto:
        return None
    try:
        dt = datetime.fromisoformat(texto.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=UTC)
    return iso(dt)


def _titulo_desde_slug(url: str) -> str:
    """Titulo legible a partir del slug de la URL cuando falta image:title."""
    slug = urlsplit(url).path.rsplit("/", 1)[-1]
    slug = re.sub(r"\.html?$", "", slug)
    slug = PATRON_SLUG_SUFIJO.sub("", slug)
    texto = slug.replace("-", " ").replace("_", " ").strip()
    return texto[:1].upper() + texto[1:] if texto else texto


def _meses_sitemap(desde: str, hasta: str | None, referencia: datetime) -> list[str]:
    """Lista 'YYYY-MM' entre desde y hasta (hasta=None => mes de referencia), inclusive."""
    anio_d, mes_d = (int(x) for x in desde.split("-"))
    if hasta:
        anio_h, mes_h = (int(x) for x in hasta.split("-"))
    else:
        anio_h, mes_h = referencia.year, referencia.month
    meses, a, m = [], anio_d, mes_d
    while (a, m) <= (anio_h, mes_h):
        meses.append(f"{a:04d}-{m:02d}")
        m += 1
        if m > 12:
            m, a = 1, a + 1
    return meses


# ---------------------------------------------------------------- fase 1: descarga

def descargar_tvn(cfg: dict, raw: Path) -> None:
    url = (cfg.get("tvn") or {}).get("url")
    if not url:
        log("  ! TVN: falta tvn.url en ingesta/config.yaml (enlace [2] del PDF). Se omite.")
        return
    t = ahora()
    r = obtener(url)
    r.raise_for_status()
    destino = raw / "tvn" / f"rss_{sello(t)}.xml"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(r.content)
    log(f"  TVN: captura guardada en {destino.relative_to(raw.parent)}")


def descargar_sitemaps_tvn(cfg: dict, raw: Path, refrescar: bool = False) -> None:
    s = (cfg.get("tvn") or {}).get("sitemaps")
    if not s:
        log("  ! TVN sitemaps: falta tvn.sitemaps en ingesta/config.yaml. Se omite.")
        return
    t = ahora()
    mes_actual = f"{t.year:04d}-{t.month:02d}"
    base = s["indice"].rsplit("/", 1)[0]  # tvn-2.com redirige a www.tvn-2.com
    destino_dir = raw / "tvn_sitemap"
    destino_dir.mkdir(parents=True, exist_ok=True)
    for mes in _meses_sitemap(s["desde"], s.get("hasta"), t):
        anio, m = mes.split("-")
        nombre = f"tvn_sitemap_contents_{anio}_{m}.xml"
        destino = destino_dir / nombre
        if destino.exists() and not refrescar and mes != mes_actual:
            continue
        if PAUSA_EXTRA:
            time.sleep(s.get("pausa_segundos", 2))
        r = obtener(f"{base}/{nombre}")
        if r.status_code == 404:
            log(f"  TVN sitemap {mes}: no existe (404), se omite")
            continue
        r.raise_for_status()
        destino.write_bytes(r.content)
        log(f"  TVN sitemap {mes}: guardado en {destino.relative_to(raw.parent)}")


def _gdelt_ventana(g: dict, raw: Path, consulta: dict, ini: datetime, fin: datetime,
                   profundidad: int = 0) -> None:
    params = {
        "query": consulta["query"], "mode": "artlist", "format": "json",
        "maxrecords": 250, "sort": "datedesc",
        "startdatetime": ini.strftime("%Y%m%d%H%M%S"),
        "enddatetime": fin.strftime("%Y%m%d%H%M%S"),
    }
    if PAUSA_EXTRA:
        time.sleep(g.get("pausa_segundos", 6))
    t = ahora()
    r = obtener(g["url"], params)
    articulos, error = [], None
    try:
        articulos = (r.json() or {}).get("articles") or []
    except ValueError:
        error = (r.text or "").strip()[:300] or f"HTTP {r.status_code}"

    # Si se alcanzó el máximo, la ventana tiene más artículos: se divide en dos.
    if len(articulos) >= 250 and (fin - ini) > timedelta(hours=2) and profundidad < 6:
        medio = ini + (fin - ini) / 2
        _gdelt_ventana(g, raw, consulta, ini, medio, profundidad + 1)
        _gdelt_ventana(g, raw, consulta, medio, fin, profundidad + 1)
        return

    nombre = f"{consulta['id']}_{params['startdatetime']}_{params['enddatetime']}.json"
    guardar_json(raw / "gdelt" / nombre, {
        "fuente": "gdelt", "consulta_id": consulta["id"], "tema": consulta["tema"],
        "params": params, "fecha_extraccion": iso(t), "http_status": r.status_code,
        "error": error, "truncado": len(articulos) >= 250, "articulos": articulos,
    })
    estado = f"error: {error[:80]}" if error else f"{len(articulos)} artículos"
    log(f"  GDELT {consulta['id']} {ini:%Y-%m-%d %H:%M} → {fin:%Y-%m-%d %H:%M}: {estado}")


def descargar_gdelt(cfg: dict, raw: Path, desde: datetime, hasta: datetime) -> None:
    g = cfg["gdelt"]
    paso = timedelta(days=g.get("ventana_dias", 7))
    for consulta in g["consultas"]:
        inicio = desde
        while inicio < hasta:
            fin = min(inicio + paso, hasta)
            _gdelt_ventana(g, raw, consulta, inicio, fin)
            inicio = fin


def descargar_banco_mundial(cfg: dict, raw: Path) -> None:
    w = cfg["banco_mundial"]
    paises = ";".join(w["paises"].keys())
    for ind in w["indicadores"]:
        url = f"{w['url']}/country/{paises}/indicator/{ind['id']}"
        params = {"format": "json", "date": f"{w['desde']}:{w['hasta']}", "per_page": 1000}
        t = ahora()
        r = obtener(url, params)
        meta, filas, error = {}, [], None
        try:
            datos = r.json()
        except ValueError:
            datos = None
        if isinstance(datos, list) and len(datos) >= 2 and isinstance(datos[1], list):
            meta, filas = datos[0], datos[1]
            if meta.get("pages", 1) > 1:
                error = "La respuesta tiene más de una página; aumentar per_page."
        else:
            error = json.dumps(datos, ensure_ascii=False)[:300] if datos else (r.text or "")[:300]
        guardar_json(raw / "worldbank" / f"{ind['id']}.json", {
            "fuente": "banco_mundial", "indicador_id": ind["id"], "url": r.url,
            "params": params, "fecha_extraccion": iso(t), "http_status": r.status_code,
            "error": error, "meta": meta, "filas": filas,
        })
        log(f"  Banco Mundial {ind['id']}: {len(filas)} filas" + (f" · {error[:80]}" if error else ""))
        if PAUSA_EXTRA:
            time.sleep(1)


def descargar_usgs(cfg: dict, raw: Path) -> None:
    u = cfg["usgs"]
    params = {"format": "geojson", "starttime": u["desde"], "endtime": u["hasta"],
              "minlatitude": u["minlatitude"], "maxlatitude": u["maxlatitude"],
              "minlongitude": u["minlongitude"], "maxlongitude": u["maxlongitude"],
              "minmagnitude": u["minmagnitude"], "orderby": "time-asc"}
    t = ahora()
    r = obtener(u["url"], params)
    r.raise_for_status()
    datos = r.json()
    guardar_json(raw / "usgs" / "eventos.json", {
        "fuente": "usgs", "url": r.url, "params": params, "fecha_extraccion": iso(t),
        "respuesta": datos,
    })
    log(f"  USGS: {len(datos.get('features', []))} sismos")


# ---------------------------------------------------------------- fase 2: procesamiento

def leer_tvn(raw: Path) -> list[dict]:
    candidatos = []
    for xml in sorted((raw / "tvn").glob("rss_*.xml")):
        extraccion = datetime.strptime(xml.stem[4:], "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
        feed = feedparser.parse(xml.read_bytes())
        for e in feed.entries:
            pub = e.get("published_parsed") or e.get("updated_parsed")
            fpub = datetime.fromtimestamp(calendar.timegm(pub), UTC) if pub else None
            link = (e.get("link") or "").strip()
            candidatos.append({
                "titulo": (e.get("title") or "").strip(), "url": link,
                "medio": dominio(link) if link else None, "idioma": "es",
                "fecha_publicacion": iso(fpub), "fecha_deteccion": None,
                "fecha_extraccion": iso(extraccion), "tema": None, "origen": "tvn_rss",
                "alcance_texto": "titular/metadatos", "_archivo": xml.name,
            })
    return candidatos


def leer_sitemaps_tvn(raw: Path) -> list[dict]:
    candidatos = []
    carpeta = raw / "tvn_sitemap"
    if not carpeta.exists():
        return candidatos
    for xml in sorted(carpeta.glob("tvn_sitemap_contents_*.xml")):
        try:
            root = ET.fromstring(xml.read_bytes())
        except ET.ParseError as e:
            log(f"  ! TVN sitemap {xml.name}: XML inv\u00e1lido ({e}), se omite")
            continue
        extraccion = iso(datetime.fromtimestamp(xml.stat().st_mtime, UTC))
        for u in root.findall(f"{NS_SITEMAP}url"):
            loc_el = u.find(f"{NS_SITEMAP}loc")
            url = (loc_el.text or "").strip() if loc_el is not None and loc_el.text else ""
            # Secciones (no articulos) no suelen terminar en .html: se descartan aqui
            # (se compara la ruta, no la URL completa, para ignorar parametros de rastreo).
            if url_valida(url) and not urlsplit(url).path.rstrip("/").endswith(".html"):
                continue
            titulo_el = u.find(f"{NS_IMAGE}image/{NS_IMAGE}title")
            titulo = (titulo_el.text or "").strip() if titulo_el is not None and titulo_el.text else ""
            if not titulo:
                titulo = _titulo_desde_slug(url) if url else ""
            lastmod_el = u.find(f"{NS_SITEMAP}lastmod")
            lastmod = _lastmod_iso(lastmod_el.text if lastmod_el is not None else None)
            candidatos.append({
                "titulo": titulo, "url": url, "medio": "tvn-2.com", "idioma": "es",
                "fecha_publicacion": None, "fecha_deteccion": lastmod,
                "fecha_extraccion": extraccion, "tema": None, "origen": "tvn_sitemap",
                "alcance_texto": "titular/metadatos", "_archivo": xml.name,
            })
    return candidatos


def leer_gdelt(raw: Path) -> tuple[list[dict], list[dict]]:
    candidatos, consultas = [], []
    for arch in sorted((raw / "gdelt").glob("*.json")):
        w = leer_json(arch)
        consultas.append({
            "fuente": "gdelt", "consulta_id": w["consulta_id"], "tema": w["tema"],
            "query": w["params"]["query"], "desde": w["params"]["startdatetime"],
            "hasta": w["params"]["enddatetime"], "registros": len(w["articulos"]),
            "truncado": w["truncado"], "error": w["error"],
        })
        for a in w["articulos"]:
            url = (a.get("url") or "").strip()
            idioma = (a.get("language") or "").strip()
            candidatos.append({
                "titulo": (a.get("title") or "").strip(), "url": url,
                "medio": a.get("domain") or (dominio(url) if url else None),
                "idioma": IDIOMAS.get(idioma.lower(), idioma.lower() or None),
                # GDELT no informa la fecha de publicación: se deja nula, nunca se copia seendate.
                "fecha_publicacion": None,
                "fecha_deteccion": iso(fecha_gdelt(a.get("seendate"))),
                "fecha_extraccion": w["fecha_extraccion"], "tema": w["tema"],
                "origen": "gdelt", "alcance_texto": "titular/metadatos", "_archivo": arch.name,
            })
    return candidatos, consultas


def consolidar_noticias(candidatos: list[dict], filtro: dict) -> tuple[list[dict], list[dict], dict]:
    por_clave, excluidos = {}, []
    stats = {"candidatos": len(candidatos), "duplicados_fusionados": 0}

    for c in candidatos:
        if not c["titulo"]:
            excluidos.append({**c, "motivo": "sin_titulo"})
            continue
        if not url_valida(c["url"]):
            excluidos.append({**c, "motivo": "url_invalida"})
            continue
        clave = normalizar_url(c["url"])
        if clave not in por_clave:
            por_clave[clave] = {"id_noticia": id_noticia(c["url"]), **c}
            continue
        ex = por_clave[clave]
        stats["duplicados_fusionados"] += 1
        prioridad_actual = _prioridad_origen(ex["origen"])
        temas = set(filter(None, (ex["tema"] or "").split("|")))
        if c["tema"]:
            temas.add(c["tema"])
        ex["tema"] = "|".join(sorted(temas)) or None
        if c["origen"] not in ex["origen"].split("|"):
            ex["origen"] += "|" + c["origen"]
        for campo in ("fecha_publicacion", "idioma", "medio"):
            if not ex.get(campo) and c.get(campo):
                ex[campo] = c[campo]
        if c["fecha_deteccion"] and (not ex["fecha_deteccion"]
                                     or c["fecha_deteccion"] < ex["fecha_deteccion"]):
            ex["fecha_deteccion"] = c["fecha_deteccion"]
        # Si el nuevo candidato viene de un origen de mayor prioridad (tvn_rss > tvn_sitemap
        # > gdelt), su titulo/idioma/medio/alcance_texto reemplazan a los ya guardados.
        if _prioridad_origen(c["origen"]) < prioridad_actual:
            ex["titulo"] = c["titulo"]
            ex["idioma"] = c["idioma"] or ex["idioma"]
            ex["medio"] = c["medio"] or ex["medio"]
            ex["alcance_texto"] = c["alcance_texto"] or ex["alcance_texto"]

    noticias = []
    for n in por_clave.values():
        referencia = n["fecha_publicacion"] or n["fecha_deteccion"]
        if filtro.get("activo") and (not referencia
                                     or not filtro["desde"] <= referencia < filtro["hasta"]):
            excluidos.append({**n, "motivo": "fuera_de_intervalo"})
            continue
        noticias.append(n)

    noticias.sort(key=lambda n: (n["fecha_publicacion"] or n["fecha_deteccion"] or "", n["id_noticia"]),
                  reverse=True)
    stats["fechas_publicacion_nulas"] = sum(1 for n in noticias if not n["fecha_publicacion"])
    stats["excluidos"] = len(excluidos)
    return noticias, excluidos, stats


def construir_fuentes(noticias: list[dict]) -> list[dict]:
    medios: dict[str, dict] = {}
    for n in noticias:
        m = medios.setdefault(n["medio"], {"medio": n["medio"], "origen": set(), "idiomas": set(),
                                           "registros": 0})
        m["registros"] += 1
        m["origen"].update(n["origen"].split("|"))
        if n["idioma"]:
            m["idiomas"].add(n["idioma"])
    salida = []
    for m in sorted(medios.values(), key=lambda x: (-x["registros"], x["medio"])):
        salida.append({
            "medio": m["medio"], "origen": sorted(m["origen"]), "idiomas": sorted(m["idiomas"]),
            "registros": m["registros"],
            "condiciones": "Solo metadatos (titular, URL, fechas). Los derechos del contenido "
                           "pertenecen al medio; no se redistribuyen artículos, imágenes ni videos.",
        })
    return salida


def procesar_indicadores(cfg: dict, raw: Path) -> tuple[list[dict], list[dict]]:
    w = cfg["banco_mundial"]
    valores, nombres, extraccion, consultas, descargados = {}, {}, {}, [], set()
    for arch in sorted((raw / "worldbank").glob("*.json")):
        d = leer_json(arch)
        ind = d["indicador_id"]
        descargados.add(ind)
        extraccion[ind] = d["fecha_extraccion"]
        consultas.append({"fuente": "banco_mundial", "indicador_id": ind, "url": d["url"],
                          "registros": len(d["filas"]), "error": d["error"],
                          "ultima_actualizacion": (d.get("meta") or {}).get("lastupdated")})
        for f in d["filas"]:
            try:
                anio = int(f["date"])
            except (KeyError, TypeError, ValueError):
                continue
            valores[(f.get("countryiso3code"), ind, anio)] = f.get("value")
            nombres[ind] = (f.get("indicator") or {}).get("value")

    filas = []
    for iso3, iso2 in w["paises"].items():
        for ind in w["indicadores"]:
            for anio in range(int(w["desde"]), int(w["hasta"]) + 1):
                clave = (iso3, ind["id"], anio)
                valor = valores.get(clave)
                if ind["id"] not in descargados:
                    obs = "indicador no descargado"
                elif valor is None:
                    obs = "sin dato en la fuente"
                else:
                    obs = ""
                filas.append({
                    "id_evidencia": f"IND-{iso3}-{ind['id']}-{anio}", "pais_iso3": iso3,
                    "indicador_id": ind["id"], "indicador_nombre": nombres.get(ind["id"]),
                    "anio": anio, "valor": valor, "unidad": ind["unidad"], "observacion": obs,
                    "fuente_url": f"https://data.worldbank.org/indicator/{ind['id']}?locations={iso2}",
                    "fecha_extraccion": extraccion.get(ind["id"]), "licencia": w["licencia"],
                })
    return filas, consultas


def procesar_eventos(raw: Path) -> tuple[dict, list[dict]]:
    arch = raw / "usgs" / "eventos.json"
    if not arch.exists():
        return {"type": "FeatureCollection", "features": []}, []
    d = leer_json(arch)
    features = []
    for f in d["respuesta"].get("features", []):
        p, coords = f.get("properties", {}), (f.get("geometry") or {}).get("coordinates") or [None] * 3
        ms = lambda v: iso(datetime.fromtimestamp(v / 1000, UTC)) if v is not None else None
        features.append({
            "type": "Feature", "id": f.get("id"), "geometry": f.get("geometry"),
            "properties": {
                "id": f.get("id"), "magnitude": p.get("mag"), "time": ms(p.get("time")),
                "updated": ms(p.get("updated")), "longitude": coords[0], "latitude": coords[1],
                "depth": coords[2] if len(coords) > 2 else None, "place": p.get("place"),
                "status": p.get("status"), "url": p.get("url"),
            },
        })
    coleccion = {
        "type": "FeatureCollection",
        "metadata": {"fuente": "USGS", "consulta": d["url"], "fecha_extraccion": d["fecha_extraccion"],
                     "aviso": "La caja geográfica no equivale al territorio de Panamá. "
                              "Usar solo para hechos sísmicos."},
        "features": features,
    }
    return coleccion, [{"fuente": "usgs", "url": d["url"], "registros": len(features)}]


def escribir_csv(ruta: Path, filas: list[dict], columnas: list[str]) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columnas, extrasaction="ignore")
        w.writeheader()
        for fila in filas:
            w.writerow({k: ("" if fila.get(k) is None else fila.get(k)) for k in columnas})


DICCIONARIO = """# Diccionario de datos

Fechas en ISO 8601 UTC (sufijo Z). Celda vacía = valor nulo; nunca se rellena con cero.

## processed/noticias.csv
- **id_noticia**: `N-` + SHA-1 de la URL normalizada (estable entre ejecuciones).
- **titulo, url, medio, idioma**: metadatos de la noticia; idioma en código ISO cuando se conoce.
- **fecha_publicacion**: publicación según el medio. Nula en GDELT, que no la informa.
- **fecha_deteccion**: `seendate` de GDELT (cuándo GDELT la detectó). No es la publicación.
- **fecha_extraccion**: cuándo se descargó.
- **tema**: tema de la CONSULTA que la encontró (varios separados por `|`). No es una etiqueta verificada.
- **origen**: `tvn_rss`, `tvn_sitemap`, `gdelt` o varios separados por `|`. Si un duplicado existe
  en varios orígenes, titulo/idioma/medio se quedan con el de mayor prioridad (tvn_rss > tvn_sitemap > gdelt).
- **alcance_texto**: texto disponible. `titular/metadatos` = no se tiene el artículo.

## processed/indicadores.csv
- **id_evidencia**: `IND-<país>-<indicador>-<año>`, para citar.
- **valor**: nulo si la fuente no tiene dato.
- **observacion**: `sin dato en la fuente`, `indicador no descargado` o vacío.
- **fuente_url**: página pública del indicador para ese país.

## processed/eventos.geojson
- **id**: ID de USGS; también es el ID de evidencia.
- **time, updated**: hora del sismo y de la última revisión, en UTC.
- **status**: `reviewed` (revisado) o `automatic`.

## processed/excluidos.csv
Registros descartados con su **motivo**: `sin_titulo`, `url_invalida`, `fuera_de_intervalo`.
"""


def procesar(cfg: dict, data: Path) -> dict:
    raw, proc = data / "raw", data / "processed"
    proc.mkdir(parents=True, exist_ok=True)
    corte = ahora()

    tvn = leer_tvn(raw)
    sitemap = leer_sitemaps_tvn(raw)
    gdelt, consultas_gdelt = leer_gdelt(raw)
    noticias, excluidos, stats = consolidar_noticias(tvn + sitemap + gdelt,
                                                      cfg.get("filtro_intervalo") or {})
    indicadores, consultas_wb = procesar_indicadores(cfg, raw)
    eventos, consultas_usgs = procesar_eventos(raw)

    escribir_csv(proc / "noticias.csv", noticias, COLUMNAS_NOTICIAS)
    escribir_csv(proc / "excluidos.csv", excluidos,
                 ["origen", "_archivo", "titulo", "url", "fecha_publicacion", "fecha_deteccion", "motivo"])
    guardar_json(proc / "fuentes.json", construir_fuentes(noticias))
    escribir_csv(proc / "indicadores.csv", indicadores, COLUMNAS_INDICADORES)
    guardar_json(proc / "eventos.geojson", eventos)
    (data / "diccionario.md").write_text(DICCIONARIO, encoding="utf-8")

    archivos = {}
    conteos = {"noticias.csv": len(noticias), "excluidos.csv": len(excluidos),
               "fuentes.json": len(construir_fuentes(noticias)),
               "indicadores.csv": len(indicadores), "eventos.geojson": len(eventos["features"])}
    for nombre, n in conteos.items():
        archivos[f"processed/{nombre}"] = {"registros": n, "sha256": sha256(proc / nombre)}

    def rango(campo, filas):
        vals = sorted(f[campo] for f in filas if f.get(campo))
        return f"{vals[0][:10]} a {vals[-1][:10]}" if vals else "sin fechas"

    de_tvn = [n for n in noticias if "tvn_rss" in n["origen"]]
    de_sitemap = [n for n in noticias if "tvn_sitemap" in n["origen"]]
    de_gdelt = [n for n in noticias if "gdelt" in n["origen"]]
    validos = sum(1 for f in indicadores if f["valor"] is not None)
    sha_noticias = archivos["processed/noticias.csv"]["sha256"]
    ultima = lambda filas: max((f["fecha_extraccion"] for f in filas if f.get("fecha_extraccion")),
                               default=None)

    fuentes_catalogo = [
        {"id": "SRC-TVN", "fuente": "TVN · feed RSS", "url": (cfg.get("tvn") or {}).get("url") or None,
         "fecha_extraccion": ultima(de_tvn), "registros": len(de_tvn),
         "cobertura": f"{len(de_tvn)} noticias · publicación {rango('fecha_publicacion', de_tvn)}",
         "campos": "titulo, url, fecha_publicacion",
         "licencia": "Solo metadatos; el RSS no implica licencia sobre artículos, videos o imágenes",
         "transformaciones": "Deduplicación por URL normalizada; fechas a UTC", "sha256": sha_noticias},
        {"id": "SRC-TVN-SITEMAP", "fuente": "TVN · sitemaps mensuales",
         "url": ((cfg.get("tvn") or {}).get("sitemaps") or {}).get("indice"),
         "fecha_extraccion": ultima(de_sitemap), "registros": len(de_sitemap),
         "cobertura": f"{len(de_sitemap)} noticias · lastmod {rango('fecha_deteccion', de_sitemap)} "
                      f"· {len(list((raw / 'tvn_sitemap').glob('tvn_sitemap_contents_*.xml')))} meses",
         "campos": "titulo, url, fecha_deteccion (lastmod)",
         "licencia": "Solo metadatos (titular, URL, fecha); no se redistribuyen artículos ni imágenes",
         "transformaciones": "fecha_deteccion = lastmod del sitemap, NO es la fecha de publicación; "
                             "titulo cae al slug de la URL si falta image:title; deduplicación por URL",
         "sha256": sha_noticias},
        {"id": "SRC-GDELT", "fuente": "GDELT DOC 2.0", "url": cfg["gdelt"]["url"],
         "fecha_extraccion": ultima(de_gdelt), "registros": len(de_gdelt),
         "cobertura": f"{len(de_gdelt)} noticias · detección {rango('fecha_deteccion', de_gdelt)}",
         "campos": "titulo, url, dominio, idioma, seendate",
         "licencia": "La API no transfiere derechos de los medios enlazados",
         "transformaciones": "seendate → fecha_deteccion (fecha_publicacion nula); ventanas "
                             "divididas al llegar a 250; deduplicación por URL", "sha256": sha_noticias},
        {"id": "SRC-WB", "fuente": "Banco Mundial · Indicators API v2", "url": cfg["banco_mundial"]["url"],
         "fecha_extraccion": ultima(indicadores), "registros": len(indicadores),
         "cobertura": f"{len(cfg['banco_mundial']['paises'])} países · {cfg['banco_mundial']['desde']}–"
                      f"{cfg['banco_mundial']['hasta']} · {len(cfg['banco_mundial']['indicadores'])} "
                      f"indicadores · {validos} valores no nulos",
         "campos": "pais_iso3, indicador_id, anio, valor, unidad",
         "licencia": cfg["banco_mundial"]["licencia"],
         "transformaciones": "Cuadrícula completa; nulos conservados con observación",
         "sha256": archivos["processed/indicadores.csv"]["sha256"]},
        {"id": "SRC-USGS", "fuente": "USGS · catálogo sísmico", "url": cfg["usgs"]["url"],
         "fecha_extraccion": (eventos.get("metadata") or {}).get("fecha_extraccion"),
         "registros": len(eventos["features"]),
         "cobertura": f"{cfg['usgs']['desde'][:10]} a {cfg['usgs']['hasta'][:10]} · lat "
                      f"{cfg['usgs']['minlatitude']} a {cfg['usgs']['maxlatitude']} · lon "
                      f"{cfg['usgs']['minlongitude']} a {cfg['usgs']['maxlongitude']} · "
                      f"magnitud ≥ {cfg['usgs']['minmagnitude']}",
         "campos": "id, magnitude, time, updated, longitude, latitude, depth, place, status, url",
         "licencia": "Verificar condiciones de datos de terceros",
         "transformaciones": "Tiempos de milisegundos a ISO UTC; solo para hechos sísmicos",
         "sha256": archivos["processed/eventos.geojson"]["sha256"]},
    ]

    manifest = {
        "version": cfg.get("version", "v0-dev"),
        "nota": "Snapshot de desarrollo propio, no es el paquete oficial de la organización.",
        "fecha_corte_utc": iso(corte),
        "consultas": consultas_gdelt + consultas_wb + consultas_usgs
                     + [{"fuente": "tvn_rss", "capturas": len(list((raw / "tvn").glob("rss_*.xml")))},
                        {"fuente": "tvn_sitemap",
                         "capturas": len(list((raw / "tvn_sitemap").glob("tvn_sitemap_contents_*.xml")))}],
        "archivos": archivos,
        "estadisticas_noticias": stats,
        "filtro_intervalo": cfg.get("filtro_intervalo"),
        "transformaciones": [
            "Deduplicación de noticias por URL normalizada (sin esquema, www, utm_*, fbclid, barra final)",
            "Duplicados fusionados: se conservan todos los temas y orígenes; fecha_deteccion más temprana",
            "fecha_publicacion de GDELT queda nula; seendate se guarda como fecha_deteccion",
            "Fechas convertidas a ISO 8601 UTC",
            "Indicadores: cuadrícula país × indicador × año completa; nulos conservados",
            "Registros inválidos o fuera de intervalo movidos a excluidos.csv con su motivo",
        ],
        "fuentes": fuentes_catalogo,
    }
    guardar_json(data / "manifest.json", manifest)
    return manifest


# ---------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser(description="Descarga y procesa el snapshot de datos del reto.")
    ap.add_argument("--solo", nargs="+", choices=["tvn", "sitemaps", "gdelt", "wb", "usgs"],
                    help="descargar solo estas fuentes")
    ap.add_argument("--desde", help="inicio de la ventana de GDELT (YYYY-MM-DD)")
    ap.add_argument("--hasta", help="fin de la ventana de GDELT (YYYY-MM-DD)")
    ap.add_argument("--solo-procesar", action="store_true",
                    help="no descargar; regenerar processed/ desde raw/")
    ap.add_argument("--refrescar", action="store_true",
                    help="TVN sitemaps: re-descargar meses ya guardados (el mes actual siempre se refresca)")
    args = ap.parse_args()

    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    data = RAIZ / cfg.get("data_dir", "data")
    raw = data / "raw"

    if not args.solo_procesar:
        fuentes = set(args.solo or ["tvn", "sitemaps", "gdelt", "wb", "usgs"])
        hasta = fecha_iso_entrada(args.hasta) if args.hasta else ahora()
        desde = (fecha_iso_entrada(args.desde) if args.desde
                 else hasta - timedelta(days=cfg["gdelt"].get("dias_atras", 30)))
        log(f"Descargando {', '.join(sorted(fuentes))}…")
        pasos = [("tvn", lambda: descargar_tvn(cfg, raw)),
                 ("sitemaps", lambda: descargar_sitemaps_tvn(cfg, raw, args.refrescar)),
                 ("wb", lambda: descargar_banco_mundial(cfg, raw)),
                 ("usgs", lambda: descargar_usgs(cfg, raw)),
                 ("gdelt", lambda: descargar_gdelt(cfg, raw, desde, hasta))]
        for clave, paso in pasos:
            if clave in fuentes:
                try:
                    paso()
                except Exception as e:  # una fuente caída no detiene a las demás
                    log(f"  ! {clave}: {e}")

    log("Procesando…")
    m = procesar(cfg, data)
    for nombre, info in m["archivos"].items():
        log(f"  {nombre:<28} {info['registros']:>6} registros")
    s = m["estadisticas_noticias"]
    log(f"  duplicados fusionados: {s['duplicados_fusionados']} · excluidos: {s['excluidos']}")
    if m["archivos"]["processed/noticias.csv"]["registros"] < 100:
        log("  ! Menos de 100 noticias: el mínimo operativo del reto es 100 (al menos 20 de TVN).")
    log(f"Manifest: {data / 'manifest.json'}")


if __name__ == "__main__":
    sys.exit(main())
