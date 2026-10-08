"""Tests de motor/abstencion.py (TAR-009, G3): abstención decidida por código, antes del LLM.

Si no hay evidencia sustentada, el sistema se abstiene sin llamar al modelo (CU-04, T06).
Tres abstenciones al consultar un indicador: no está en el corpus, existe pero el valor
es nulo, o el año está fuera de rango. El alcance del borrador es explícito (T09).
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from motor import abstencion

TITULARES = "basado únicamente en titular/metadatos"


def _paquete(*tipos: str) -> dict:
    return {"grupo_id": "G-1", "tema": "economia", "items": [
        {"id_evidencia": f"X-{i}", "tipo": t, "campos": {}} for i, t in enumerate(tipos)
    ]}


def test_paquete_vacio_se_abstiene_sin_llamar_al_modelo():
    res = abstencion.decidir_abstencion_grupo(_paquete())
    assert res["tipo_respuesta"] == "abstencion"
    assert res["motivo"] == "sin_evidencia"
    assert res["afirmaciones"] == [] and res["vacios"]
    assert res["alcance"] == TITULARES


def test_paquete_con_evidencia_no_se_abstiene():
    assert abstencion.decidir_abstencion_grupo(_paquete("noticia")) is None


def test_alcance_solo_noticias_es_titular_y_metadatos():
    assert abstencion.alcance_de(_paquete("noticia", "noticia")) == TITULARES


def test_alcance_con_datos_oficiales_lo_declara():
    alcance = abstencion.alcance_de(_paquete("noticia", "indicador"))
    assert "titular/metadatos" in alcance and "datos oficiales" in alcance
    assert abstencion.alcance_de(_paquete("noticia", "evento")) == alcance


@pytest.fixture()
def senales(tmp_path: Path) -> Path:
    ruta = tmp_path / "senales.duckdb"
    con = duckdb.connect(str(ruta))
    con.execute("""CREATE TABLE indicadores (id_evidencia TEXT, pais_iso3 TEXT, indicador_id TEXT,
        indicador_nombre TEXT, anio INTEGER, valor DOUBLE, unidad TEXT, fuente_url TEXT)""")
    filas = [(f"IND-PAN-SL.UEM.TOTL.ZS-{a}", "PAN", "SL.UEM.TOTL.ZS", "Desempleo", a, v, "%", "http://wb")
             for a, v in [(2020, 7.1), (2021, None), (2022, 7.4)]]
    con.executemany("INSERT INTO indicadores VALUES (?, ?, ?, ?, ?, ?, ?, ?)", filas)
    con.close()
    return ruta


def test_consulta_con_dato_devuelve_item_citable_con_nota_de_dato_anual(senales):
    res = abstencion.consultar_indicador("SL.UEM.TOTL.ZS", 2022, senales)
    assert res["tipo_respuesta"] == "respuesta"
    item = res["items"][0]
    assert item["id_evidencia"] == "IND-PAN-SL.UEM.TOTL.ZS-2022" and item["tipo"] == "indicador"
    assert item["campos"]["valor"] == 7.4 and item["campos"]["anio"] == 2022
    assert "anual" in res["nota"]  # CU-02: no es una medición actual


def test_indicador_fuera_del_corpus_se_abstiene(senales):
    res = abstencion.consultar_indicador("XX.NO.EXISTE", 2022, senales)
    assert res["tipo_respuesta"] == "abstencion" and res["motivo"] == "indicador_ausente"


def test_valor_nulo_se_abstiene_sin_inventar_cero(senales):
    res = abstencion.consultar_indicador("SL.UEM.TOTL.ZS", 2021, senales)
    assert res["tipo_respuesta"] == "abstencion" and res["motivo"] == "valor_nulo"
    assert "items" not in res or res["items"] == []


@pytest.mark.parametrize("anio", [1999, 2030])
def test_anio_fuera_de_rango_se_abstiene(senales, anio):
    res = abstencion.consultar_indicador("SL.UEM.TOTL.ZS", anio, senales)
    assert res["tipo_respuesta"] == "abstencion" and res["motivo"] == "anio_fuera_de_rango"


def test_toda_abstencion_explica_el_vacio_y_no_tiene_afirmaciones(senales):
    for res in (
        abstencion.consultar_indicador("XX", 2022, senales),
        abstencion.consultar_indicador("SL.UEM.TOTL.ZS", 2021, senales),
        abstencion.consultar_indicador("SL.UEM.TOTL.ZS", 1999, senales),
    ):
        assert res["afirmaciones"] == [] and res["vacios"] and res["alcance"]
