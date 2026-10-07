"""Tests de motor/evidencia.py (TAR-009, G1): reunir la evidencia citable de un grupo.

La evidencia se arma solo con código determinista: noticias del grupo (titular y
metadatos), indicadores del Banco Mundial sin valores nulos (último año por indicador)
solo para temas con contexto definido, y el evento USGS verificado si existe.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import duckdb
import pytest

from motor import evidencia

REGLAS = {"contexto_oficial": {"contexto_por_tema": {"economia": ["FP.CPI", "NY.GDP"]}}}


@pytest.fixture()
def dbs(tmp_path: Path):
    motor = tmp_path / "motor.duckdb"
    senales = tmp_path / "senales.duckdb"
    con = duckdb.connect(str(motor))
    con.execute("CREATE TABLE grupo_noticias (grupo_id TEXT, id_noticia TEXT, procedencia TEXT, similitud_al_centroide DOUBLE)")
    con.execute("CREATE TABLE puntaje (grupo_id TEXT, tema TEXT, evento_usgs_id TEXT)")
    filas = [
        ("G-ECO", "N-b", "tvn-pa.com", 0.90), ("G-ECO", "N-a", "critica.com.pa", 0.95),
        ("G-ECO", "N-c", "tvn-pa.com", 0.80),
        ("G-SIS", "N-s", "tvn-pa.com", 0.99), ("G-TUR", "N-t", "tvn-pa.com", 0.99),
    ]
    con.executemany("INSERT INTO grupo_noticias VALUES (?, ?, ?, ?)", filas)
    con.executemany("INSERT INTO puntaje VALUES (?, ?, ?)", [
        ("G-ECO", "economia", None), ("G-SIS", "eventos_naturales", "us1"), ("G-TUR", "turismo", None),
    ])
    con.close()

    con = duckdb.connect(str(senales))
    con.execute("""CREATE TABLE noticias (id_noticia TEXT, titulo TEXT, url TEXT, medio TEXT,
        fecha_publicacion TIMESTAMP, fecha_deteccion TIMESTAMP)""")
    con.executemany("INSERT INTO noticias VALUES (?, ?, ?, ?, ?, ?)", [
        ("N-a", "Inflación cae", "http://a", "critica.com.pa", None, datetime(2026, 7, 15, 20, 0)),
        ("N-b", "Precios bajan", "http://b", "tvn-pa.com", datetime(2026, 7, 15, 9, 0), datetime(2026, 7, 15, 21, 0)),
        ("N-c", "Inflación junio", "http://c", "tvn-pa.com", None, datetime(2026, 7, 16, 8, 0)),
        ("N-s", "Sismo de 5.9", "http://s", "tvn-pa.com", None, datetime(2025, 10, 22, 13, 0)),
        ("N-t", "Turismo crece", "http://t", "tvn-pa.com", None, datetime(2026, 7, 1, 8, 0)),
    ])
    con.execute("""CREATE TABLE indicadores (id_evidencia TEXT, pais_iso3 TEXT, indicador_id TEXT,
        indicador_nombre TEXT, anio INTEGER, valor DOUBLE, unidad TEXT, fuente_url TEXT)""")
    con.executemany("INSERT INTO indicadores VALUES (?, ?, ?, ?, ?, ?, ?, ?)", [
        ("IND-PAN-FP.CPI.TOTL.ZG-2022", "PAN", "FP.CPI.TOTL.ZG", "Inflación", 2022, 2.9, "% anual", "http://wb/cpi"),
        ("IND-PAN-FP.CPI.TOTL.ZG-2023", "PAN", "FP.CPI.TOTL.ZG", "Inflación", 2023, None, "% anual", "http://wb/cpi"),
        ("IND-PAN-NY.GDP.MKTP.KD.ZG-2023", "PAN", "NY.GDP.MKTP.KD.ZG", "PIB", 2023, 7.3, "% anual", "http://wb/gdp"),
        ("IND-CRI-FP.CPI.TOTL.ZG-2023", "CRI", "FP.CPI.TOTL.ZG", "Inflación", 2023, 0.5, "% anual", "http://wb/cpi"),
        ("IND-PAN-IT.NET.USER.ZS-2023", "PAN", "IT.NET.USER.ZS", "Internet", 2023, 80.0, "%", "http://wb/net"),
    ])
    con.execute("CREATE TABLE eventos (id TEXT, time TIMESTAMP, magnitude DOUBLE, place TEXT, url TEXT)")
    con.execute("INSERT INTO eventos VALUES ('us1', '2025-10-21 22:57:00', 5.9, '21 km SSW of Quepos, Costa Rica', 'http://usgs/us1')")
    con.close()
    return motor, senales


def _por_id(paquete: dict) -> dict:
    return {i["id_evidencia"]: i for i in paquete["items"]}


def test_noticias_del_grupo_con_campos_citables(dbs):
    motor, senales = dbs
    p = evidencia.reunir_evidencia("G-ECO", motor, senales, REGLAS)
    assert p["grupo_id"] == "G-ECO" and p["tema"] == "economia"
    noticias = [i for i in p["items"] if i["tipo"] == "noticia"]
    # orden determinista: mayor similitud al centroide, luego id
    assert [i["id_evidencia"] for i in noticias] == ["N-a", "N-b", "N-c"]
    b = _por_id(p)["N-b"]
    assert b["campos"] == {
        "titulo": "Precios bajan", "medio": "tvn-pa.com", "url": "http://b",
        "fecha_publicacion": "2026-07-15T09:00:00", "fecha_deteccion": "2026-07-15T21:00:00",
    }


def test_fechas_nulas_quedan_nulas_sin_rellenar(dbs):
    motor, senales = dbs
    a = _por_id(evidencia.reunir_evidencia("G-ECO", motor, senales, REGLAS))["N-a"]
    assert a["campos"]["fecha_publicacion"] is None


def test_limita_cantidad_de_noticias(dbs):
    motor, senales = dbs
    p = evidencia.reunir_evidencia("G-ECO", motor, senales, REGLAS, max_noticias=2)
    assert [i["id_evidencia"] for i in p["items"] if i["tipo"] == "noticia"] == ["N-a", "N-b"]


def test_indicadores_solo_pan_sin_nulos_ultimo_anio_y_solo_temas_con_contexto(dbs):
    motor, senales = dbs
    p = evidencia.reunir_evidencia("G-ECO", motor, senales, REGLAS)
    indicadores = _por_id(p)
    assert "IND-PAN-FP.CPI.TOTL.ZG-2022" in indicadores  # 2023 es nulo: se usa el último no nulo
    assert "IND-PAN-FP.CPI.TOTL.ZG-2023" not in indicadores
    assert "IND-PAN-NY.GDP.MKTP.KD.ZG-2023" in indicadores
    assert "IND-CRI-FP.CPI.TOTL.ZG-2023" not in indicadores  # otro país
    assert "IND-PAN-IT.NET.USER.ZS-2023" not in indicadores  # sin prefijo para economía
    ind = indicadores["IND-PAN-FP.CPI.TOTL.ZG-2022"]
    assert ind["tipo"] == "indicador"
    assert ind["campos"]["valor"] == 2.9 and ind["campos"]["anio"] == 2022
    assert ind["campos"]["unidad"] == "% anual"


def test_tema_sin_contexto_no_trae_indicadores(dbs):
    motor, senales = dbs
    p = evidencia.reunir_evidencia("G-TUR", motor, senales, REGLAS)
    assert {i["tipo"] for i in p["items"]} == {"noticia"}


def test_evento_usgs_verificado_se_incluye(dbs):
    motor, senales = dbs
    p = evidencia.reunir_evidencia("G-SIS", motor, senales, REGLAS)
    ev = _por_id(p)["us1"]
    assert ev["tipo"] == "evento"
    assert ev["campos"] == {
        "magnitude": 5.9, "time": "2025-10-21T22:57:00",
        "place": "21 km SSW of Quepos, Costa Rica", "url": "http://usgs/us1",
    }


def test_grupo_inexistente_falla_claro(dbs):
    motor, senales = dbs
    with pytest.raises(KeyError):
        evidencia.reunir_evidencia("G-NOPE", motor, senales, REGLAS)


def test_no_modifica_las_bases(dbs):
    motor, senales = dbs
    antes = (motor.stat().st_mtime_ns, senales.stat().st_mtime_ns)
    evidencia.reunir_evidencia("G-ECO", motor, senales, REGLAS)
    assert (motor.stat().st_mtime_ns, senales.stat().st_mtime_ns) == antes
