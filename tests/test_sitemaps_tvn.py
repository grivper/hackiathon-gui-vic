"""Pruebas de los sitemaps mensuales de TVN; no usan internet."""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ingesta"))
import descargar_snapshot as ds  # noqa: E402

FIXTURE = Path(__file__).parent / "fixtures" / "tvn_sitemap_sample.xml"


def escribir_raw(raw: Path, nombre: str = "tvn_sitemap_contents_2026_09.xml") -> Path:
    destino_dir = raw / "tvn_sitemap"
    destino_dir.mkdir(parents=True, exist_ok=True)
    destino = destino_dir / nombre
    destino.write_bytes(FIXTURE.read_bytes())
    return destino


# ---------------------------------------------------------------- parseo


def test_leer_sitemaps_parsea_titulo_url_y_lastmod(tmp_path):
    escribir_raw(tmp_path / "raw")
    candidatos = ds.leer_sitemaps_tvn(tmp_path / "raw")
    urls = {c["url"] for c in candidatos}

    principal = next(c for c in candidatos
                     if "canal-de-panama-anuncia" in c["url"] and "utm_source" not in c["url"])
    assert principal["titulo"] == "Canal de Panamá anuncia restricción de calado"
    assert principal["medio"] == "tvn-2.com"
    assert principal["idioma"] == "es"
    assert principal["origen"] == "tvn_sitemap"
    assert principal["alcance_texto"] == "titular/metadatos"
    assert principal["fecha_publicacion"] is None
    # -05:00 convertido a UTC
    assert principal["fecha_deteccion"] == "2026-09-15T07:11:34Z"

    # Secciones sin .html (p. ej. /opinion/) se descartan: no deben aparecer como candidatos.
    assert not any(u.rstrip("/").endswith("/opinion") for u in urls)


def test_leer_sitemaps_titulo_cae_al_slug_de_la_url(tmp_path):
    escribir_raw(tmp_path / "raw")
    candidatos = ds.leer_sitemaps_tvn(tmp_path / "raw")
    sin_imagen = next(c for c in candidatos if "inflacion-sube" in c["url"])
    assert sin_imagen["titulo"] == "Inflacion sube en septiembre"
    # lastmod con sufijo Z se normaliza igual
    assert sin_imagen["fecha_deteccion"] == "2026-09-20T10:00:00Z"


def test_leer_sitemaps_incluye_url_invalida_para_que_se_excluya_despues(tmp_path):
    escribir_raw(tmp_path / "raw")
    candidatos = ds.leer_sitemaps_tvn(tmp_path / "raw")
    invalida = next(c for c in candidatos if c["url"] == "no-es-una-url-valida")
    assert invalida["origen"] == "tvn_sitemap"
    assert not ds.url_valida(invalida["url"])


def test_titulo_desde_slug_quita_sufijo_y_extension():
    url = "https://www.tvn-2.com/deportes/seleccion-gana-partido-clave_3_999999.html"
    assert ds._titulo_desde_slug(url) == "Seleccion gana partido clave"


def test_lastmod_iso_normaliza_offset_y_z():
    assert ds._lastmod_iso("2026-09-15T02:11:34-05:00") == "2026-09-15T07:11:34Z"
    assert ds._lastmod_iso("2026-09-20T10:00:00Z") == "2026-09-20T10:00:00Z"
    assert ds._lastmod_iso(None) is None
    assert ds._lastmod_iso("no-es-una-fecha") is None


# ---------------------------------------------------------------- consolidacion / dedupe


def test_sitemaps_dedupe_por_url_normalizada(tmp_path):
    escribir_raw(tmp_path / "raw")
    candidatos = ds.leer_sitemaps_tvn(tmp_path / "raw")
    noticias, excluidos, stats = ds.consolidar_noticias(candidatos, {})

    # La entrada duplicada con ?utm_source=sitemap se fusiona con la original.
    principal = next(n for n in noticias if "canal-de-panama-anuncia" in n["url"])
    assert principal["origen"] == "tvn_sitemap"
    assert principal["fecha_deteccion"] == "2026-09-15T07:11:34Z"  # se conserva la mas temprana
    assert stats["duplicados_fusionados"] >= 1

    motivos = {e["motivo"] for e in excluidos}
    assert "url_invalida" in motivos


def test_rss_tiene_prioridad_sobre_sitemap_en_duplicados(tmp_path):
    escribir_raw(tmp_path / "raw")
    sitemap = ds.leer_sitemaps_tvn(tmp_path / "raw")
    url_sitemap = next(c["url"] for c in sitemap
                       if "canal-de-panama-anuncia" in c["url"] and "utm_source" not in c["url"])
    rss = [{
        "titulo": "Título verificado por la redacción de TVN", "url": url_sitemap,
        "medio": "tvn-2.com", "idioma": "es", "fecha_publicacion": "2026-09-15T12:00:00Z",
        "fecha_deteccion": None, "fecha_extraccion": "2026-09-15T12:05:00Z", "tema": None,
        "origen": "tvn_rss", "alcance_texto": "titular/metadatos", "_archivo": "rss_x.xml",
    }]

    # El orden de entrada no debe importar: sitemap antes de RSS...
    noticias, _, _ = ds.consolidar_noticias(sitemap + rss, {})
    fusionada = next(n for n in noticias if n["url"] == url_sitemap)
    assert fusionada["titulo"] == "Título verificado por la redacción de TVN"
    assert fusionada["origen"] == "tvn_sitemap|tvn_rss"

    # ...o RSS antes de sitemap: en ambos casos gana el título de la RSS.
    noticias2, _, _ = ds.consolidar_noticias(rss + sitemap, {})
    fusionada2 = next(n for n in noticias2 if n["url"] == url_sitemap)
    assert fusionada2["titulo"] == "Título verificado por la redacción de TVN"
    assert fusionada2["origen"] == "tvn_rss|tvn_sitemap"


def test_gdelt_no_gana_sobre_sitemap(tmp_path):
    escribir_raw(tmp_path / "raw")
    sitemap = ds.leer_sitemaps_tvn(tmp_path / "raw")
    url_sitemap = next(c["url"] for c in sitemap
                       if "canal-de-panama-anuncia" in c["url"] and "utm_source" not in c["url"])
    gdelt = [{
        "titulo": "Panama Canal limits draft", "url": url_sitemap, "medio": "tvn-2.com",
        "idioma": "en", "fecha_publicacion": None, "fecha_deteccion": "2026-09-16T00:00:00Z",
        "fecha_extraccion": "2026-09-16T00:05:00Z", "tema": "logistica_canal", "origen": "gdelt",
        "alcance_texto": "titular/metadatos", "_archivo": "gdelt_x.json",
    }]
    noticias, _, _ = ds.consolidar_noticias(sitemap + gdelt, {})
    fusionada = next(n for n in noticias if n["url"] == url_sitemap)
    assert fusionada["titulo"] == "Canal de Panamá anuncia restricción de calado"
    assert fusionada["origen"] == "tvn_sitemap|gdelt"


# ---------------------------------------------------------------- seleccion de meses


def test_meses_sitemap_con_hasta_explicito():
    meses = ds._meses_sitemap("2025-11", "2026-02", datetime(2099, 1, 1, tzinfo=timezone.utc))
    assert meses == ["2025-11", "2025-12", "2026-01", "2026-02"]


def test_meses_sitemap_hasta_none_usa_mes_actual():
    referencia = datetime(2025, 12, 5, tzinfo=timezone.utc)
    meses = ds._meses_sitemap("2025-10", None, referencia)
    assert meses == ["2025-10", "2025-11", "2025-12"]


def test_meses_sitemap_un_solo_mes():
    referencia = datetime(2025, 10, 20, tzinfo=timezone.utc)
    assert ds._meses_sitemap("2025-10", None, referencia) == ["2025-10"]


# ---------------------------------------------------------------- descarga (sin red)


def test_descargar_sitemaps_salta_meses_existentes_salvo_el_actual(tmp_path, monkeypatch):
    ds.PAUSA_EXTRA = False
    cfg = {"tvn": {"sitemaps": {
        "indice": "https://tvn-2.com/tvn_sitemap_index.xml",
        "desde": "2025-10", "hasta": None, "pausa_segundos": 0,
    }}}
    raw = tmp_path / "raw"
    (raw / "tvn_sitemap").mkdir(parents=True)
    # Octubre ya existe; se debe saltar. Noviembre (mes "actual" simulado) no existe: se descarga.
    (raw / "tvn_sitemap" / "tvn_sitemap_contents_2025_10.xml").write_text("viejo", encoding="utf-8")

    class Resp:
        status_code = 200
        content = b"<urlset></urlset>"

        def raise_for_status(self):
            pass

    pedidos = []

    def falso_ahora():
        return datetime(2025, 11, 1, tzinfo=timezone.utc)

    def falso_obtener(url, params=None):
        pedidos.append(url)
        return Resp()

    monkeypatch.setattr(ds, "ahora", falso_ahora)
    monkeypatch.setattr(ds, "obtener", falso_obtener)
    cfg["tvn"]["sitemaps"]["hasta"] = "2025-11"

    ds.descargar_sitemaps_tvn(cfg, raw)

    assert pedidos == ["https://tvn-2.com/tvn_sitemap_contents_2025_11.xml"]
    assert (raw / "tvn_sitemap" / "tvn_sitemap_contents_2025_10.xml").read_text(
        encoding="utf-8") == "viejo"


def test_descargar_sitemaps_refrescar_vuelve_a_pedir_todo(tmp_path, monkeypatch):
    ds.PAUSA_EXTRA = False
    cfg = {"tvn": {"sitemaps": {
        "indice": "https://tvn-2.com/tvn_sitemap_index.xml",
        "desde": "2025-10", "hasta": "2025-10", "pausa_segundos": 0,
    }}}
    raw = tmp_path / "raw"
    (raw / "tvn_sitemap").mkdir(parents=True)
    (raw / "tvn_sitemap" / "tvn_sitemap_contents_2025_10.xml").write_text("viejo", encoding="utf-8")

    class Resp:
        status_code = 200
        content = b"<urlset></urlset>"

        def raise_for_status(self):
            pass

    pedidos = []
    monkeypatch.setattr(ds, "ahora", lambda: datetime(2025, 12, 1, tzinfo=timezone.utc))
    monkeypatch.setattr(ds, "obtener", lambda url, params=None: (pedidos.append(url), Resp())[1])

    ds.descargar_sitemaps_tvn(cfg, raw, refrescar=True)
    assert pedidos == ["https://tvn-2.com/tvn_sitemap_contents_2025_10.xml"]


def test_descargar_sitemaps_404_continua(tmp_path, monkeypatch):
    ds.PAUSA_EXTRA = False
    cfg = {"tvn": {"sitemaps": {
        "indice": "https://tvn-2.com/tvn_sitemap_index.xml",
        "desde": "2025-10", "hasta": "2025-10", "pausa_segundos": 0,
    }}}
    raw = tmp_path / "raw"

    class Resp404:
        status_code = 404
        content = b""

    monkeypatch.setattr(ds, "ahora", lambda: datetime(2025, 12, 1, tzinfo=timezone.utc))
    monkeypatch.setattr(ds, "obtener", lambda url, params=None: Resp404())

    ds.descargar_sitemaps_tvn(cfg, raw)  # no debe lanzar excepción
    assert not (raw / "tvn_sitemap" / "tvn_sitemap_contents_2025_10.xml").exists()
