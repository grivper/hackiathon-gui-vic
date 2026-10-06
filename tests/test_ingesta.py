"""Pruebas de la ingesta con respuestas de ejemplo; no usan internet."""
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ingesta"))
import descargar_snapshot as ds  # noqa: E402

CFG = yaml.safe_load((Path(ds.__file__).parent / "config.yaml").read_text(encoding="utf-8"))

RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>TVN</title>
<item><title>Canal de Panam\xc3\xa1 anuncia restricci\xc3\xb3n de calado</title>
<link>https://www.tvn-2.com/nacionales/canal-calado_1/?utm_source=rss</link>
<pubDate>Mon, 05 Oct 2026 14:30:00 -0500</pubDate></item>
<item><title></title><link>https://www.tvn-2.com/sin-titulo/</link></item>
</channel></rss>"""


def escribir_raw(raw: Path) -> None:
    (raw / "tvn").mkdir(parents=True)
    (raw / "tvn" / "rss_20261006T170000Z.xml").write_bytes(RSS)
    ds.guardar_json(raw / "gdelt" / "canal_20260906_20261006.json", {
        "fuente": "gdelt", "consulta_id": "canal", "tema": "logistica_canal",
        "params": {"query": '"Panama Canal"', "startdatetime": "20260906000000",
                   "enddatetime": "20261006000000"},
        "fecha_extraccion": "2026-10-06T17:05:00Z", "http_status": 200, "error": None,
        "truncado": False,
        "articulos": [
            # Mismo artículo que el RSS de TVN, con otra forma de URL.
            {"url": "http://tvn-2.com/nacionales/canal-calado_1", "title": "Canal de Panamá anuncia",
             "seendate": "20261006T010000Z", "domain": "tvn-2.com", "language": "Spanish"},
            {"url": "https://example.com/panama-canal-draft", "title": "Panama Canal limits draft",
             "seendate": "20261005T220000Z", "domain": "example.com", "language": "English"},
            {"url": "no-es-una-url", "title": "Roto", "seendate": "malo", "language": "English"},
        ],
    })
    ds.guardar_json(raw / "worldbank" / "FP.CPI.TOTL.ZG.json", {
        "fuente": "banco_mundial", "indicador_id": "FP.CPI.TOTL.ZG", "url": "https://api.example",
        "params": {}, "fecha_extraccion": "2026-10-06T17:01:00Z", "http_status": 200, "error": None,
        "meta": {"lastupdated": "2026-07-01", "pages": 1},
        "filas": [
            {"indicator": {"id": "FP.CPI.TOTL.ZG", "value": "Inflation, consumer prices (annual %)"},
             "countryiso3code": "PAN", "date": "2022", "value": 2.86},
            {"indicator": {"id": "FP.CPI.TOTL.ZG", "value": "Inflation, consumer prices (annual %)"},
             "countryiso3code": "PAN", "date": "2024", "value": None},
        ],
    })
    ds.guardar_json(raw / "usgs" / "eventos.json", {
        "fuente": "usgs", "url": "https://usgs.example", "params": {},
        "fecha_extraccion": "2026-10-06T17:02:00Z",
        "respuesta": {"features": [{
            "id": "us7000abcd", "geometry": {"type": "Point", "coordinates": [-82.5, 7.9, 10.0]},
            "properties": {"mag": 4.5, "place": "30 km S of Example", "time": 1704067200000,
                           "updated": 1704153600000, "status": "reviewed", "url": "https://usgs/ev"}}]},
    })


def leer_csv(ruta: Path) -> list[dict]:
    with open(ruta, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_procesamiento_completo(tmp_path):
    escribir_raw(tmp_path / "raw")
    manifest = ds.procesar(CFG, tmp_path)
    proc = tmp_path / "processed"

    noticias = leer_csv(proc / "noticias.csv")
    assert len(noticias) == 2  # TVN y GDELT del mismo artículo quedan fusionados
    tvn = next(n for n in noticias if "tvn-2.com" in n["url"])
    assert tvn["origen"] == "tvn_rss|gdelt"
    assert tvn["fecha_publicacion"] == "2026-10-05T19:30:00Z"   # -05:00 convertido a UTC
    assert tvn["fecha_deteccion"] == "2026-10-06T01:00:00Z"     # tomado de GDELT
    assert tvn["tema"] == "logistica_canal"
    assert tvn["id_noticia"] == ds.id_noticia("https://tvn-2.com/nacionales/canal-calado_1")

    externa = next(n for n in noticias if "example.com" in n["url"])
    assert externa["fecha_publicacion"] == ""   # GDELT no la informa: nula, no se inventa
    assert externa["idioma"] == "en"

    excluidos = leer_csv(proc / "excluidos.csv")
    assert {e["motivo"] for e in excluidos} == {"sin_titulo", "url_invalida"}

    indicadores = leer_csv(proc / "indicadores.csv")
    assert len(indicadores) == 6 * 6 * 15        # cuadrícula completa
    fila_2022 = next(i for i in indicadores if i["id_evidencia"] == "IND-PAN-FP.CPI.TOTL.ZG-2022")
    assert fila_2022["valor"] == "2.86" and fila_2022["unidad"] == "% anual"
    fila_2024 = next(i for i in indicadores if i["id_evidencia"] == "IND-PAN-FP.CPI.TOTL.ZG-2024")
    assert fila_2024["valor"] == "" and fila_2024["observacion"] == "sin dato en la fuente"
    otra = next(i for i in indicadores if i["indicador_id"] == "SP.POP.TOTL")
    assert otra["observacion"] == "indicador no descargado"

    eventos = json.loads((proc / "eventos.geojson").read_text(encoding="utf-8"))
    p = eventos["features"][0]["properties"]
    assert p["time"] == "2024-01-01T00:00:00Z" and p["latitude"] == 7.9

    assert manifest["archivos"]["processed/noticias.csv"]["sha256"] == ds.sha256(proc / "noticias.csv")
    assert [f["id"] for f in manifest["fuentes"]] == ["SRC-TVN", "SRC-GDELT", "SRC-WB", "SRC-USGS"]


def test_procesamiento_es_determinista(tmp_path):
    escribir_raw(tmp_path / "raw")
    ds.procesar(CFG, tmp_path)
    primero = ds.sha256(tmp_path / "processed" / "noticias.csv")
    ds.procesar(CFG, tmp_path)
    assert ds.sha256(tmp_path / "processed" / "noticias.csv") == primero


def test_filtro_intervalo_mueve_a_excluidos(tmp_path):
    escribir_raw(tmp_path / "raw")
    cfg = {**CFG, "filtro_intervalo": {**CFG["filtro_intervalo"], "activo": True}}
    ds.procesar(cfg, tmp_path)
    assert leer_csv(tmp_path / "processed" / "noticias.csv") == []
    motivos = [e["motivo"] for e in leer_csv(tmp_path / "processed" / "excluidos.csv")]
    assert motivos.count("fuera_de_intervalo") == 2


def test_gdelt_divide_ventana_al_llegar_a_250(tmp_path, monkeypatch):
    ds.PAUSA_EXTRA = False
    llamadas = []

    class Resp:
        status_code, text = 200, ""

        def __init__(self, n):
            self.n = n

        def json(self):
            return {"articles": [{"url": f"https://x.com/{i}", "title": "t"} for i in range(self.n)]}

    def falso(url, params=None):
        llamadas.append(params["startdatetime"])
        return Resp(250 if len(llamadas) == 1 else 10)

    monkeypatch.setattr(ds, "obtener", falso)
    consulta = {"id": "eco", "tema": "economia", "query": "Panama economy"}
    ini = datetime(2026, 9, 1, tzinfo=timezone.utc)
    fin = datetime(2026, 9, 8, tzinfo=timezone.utc)
    ds._gdelt_ventana(CFG["gdelt"], tmp_path / "raw", consulta, ini, fin)
    assert len(llamadas) == 3                      # la primera se dividió en dos mitades
    assert len(list((tmp_path / "raw" / "gdelt").glob("*.json"))) == 2


def test_normalizar_url():
    a = ds.normalizar_url("https://www.TVN-2.com/nota/?utm_source=x&id=5#arriba")
    b = ds.normalizar_url("http://tvn-2.com/nota?id=5")
    assert a == b == "tvn-2.com/nota?id=5"
