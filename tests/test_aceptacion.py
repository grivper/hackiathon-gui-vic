"""Pruebas de aceptación del reto (TAR-011): T03, T04, T05, T06 y T08.

Corren la tubería real (evidencia -> abstención -> prompt -> validador -> ficha) con bases
DuckDB pequeñas y `ClienteFalso`, así que no necesitan Ollama. Cada prueba lleva el
identificador del reto (T0x) y su resultado esperado, tal como figura en `bitacora/pruebas.yaml`.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import duckdb
import pytest

from motor import abstencion, generar, llm

REGLAS = {"contexto_oficial": {"contexto_por_tema": {"economia": ["FP.CPI"]}}}


@pytest.fixture()
def dbs(tmp_path: Path):
    motor, senales = tmp_path / "motor.duckdb", tmp_path / "senales.duckdb"
    con = duckdb.connect(str(motor))
    con.execute("CREATE TABLE grupo_noticias (grupo_id TEXT, id_noticia TEXT, procedencia TEXT, similitud_al_centroide DOUBLE)")
    con.execute("""CREATE TABLE puntaje (grupo_id TEXT, tema TEXT, R DOUBLE, I DOUBLE, U DOUBLE, N DOUBLE, E DOUBLE,
        puntaje DOUBLE, prioridad TEXT, estado_evidencia TEXT, version_reglas TEXT, motivos TEXT,
        contexto_oficial TEXT, evento_usgs_id TEXT)""")
    con.execute("CREATE TABLE grupos (grupo_id TEXT, n_noticias INTEGER)")
    con.executemany("INSERT INTO grupo_noticias VALUES (?, ?, ?, ?)", [
        ("G-ECO", "N-a", "tvn-pa.com", 0.9), ("G-ECO", "N-b", "critica.com.pa", 0.8)])
    con.executemany("INSERT INTO puntaje VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [
        ("G-ECO", "economia", 1.0, 1.0, 1.0, 1.0, 0.6, 96.0, "alto", "suficiente", "v0.3",
         "R=1.0 (tema=economia); I=1.0; U=1.0; N=1.0; E=0.6", "", None),
        ("G-VACIO", "turismo", 0.5, 0.3, 0.4, 1.0, 0.0, 50.0, "medio", "insuficiente", "v0.3", "motivos vacio", "", None)])
    con.executemany("INSERT INTO grupos VALUES (?, ?)", [("G-ECO", 2), ("G-VACIO", 0)])
    con.close()
    con = duckdb.connect(str(senales))
    con.execute("""CREATE TABLE noticias (id_noticia TEXT, titulo TEXT, url TEXT, medio TEXT,
        fecha_publicacion TIMESTAMP, fecha_deteccion TIMESTAMP)""")
    con.executemany("INSERT INTO noticias VALUES (?, ?, ?, ?, ?, ?)", [
        ("N-a", "Inflación cae 0,3 % en junio", "http://a", "tvn-pa.com", None, datetime(2026, 7, 15, 20, 0)),
        ("N-b", "Precios bajan en Panamá", "http://b", "critica.com.pa", None, datetime(2026, 7, 15, 21, 0))])
    con.execute("""CREATE TABLE indicadores (id_evidencia TEXT, pais_iso3 TEXT, indicador_id TEXT,
        indicador_nombre TEXT, anio INTEGER, valor DOUBLE, unidad TEXT, fuente_url TEXT)""")
    con.executemany("INSERT INTO indicadores VALUES (?, ?, ?, ?, ?, ?, ?, ?)", [
        ("IND-PAN-FP.CPI.TOTL.ZG-2023", "PAN", "FP.CPI.TOTL.ZG", "Inflación, precios al consumidor", 2023, 1.5, "%", "http://wb"),
        ("IND-PAN-FP.CPI.TOTL.ZG-2024", "PAN", "FP.CPI.TOTL.ZG", "Inflación, precios al consumidor", 2024, 0.7, "%", "http://wb")])
    con.execute("CREATE TABLE eventos (id TEXT, time TIMESTAMP, magnitude DOUBLE, place TEXT, url TEXT)")
    con.close()
    return motor, senales


def _salida(*afirmaciones, tipo="respuesta", **extra):
    base = {"tipo_respuesta": tipo, "afirmaciones": list(afirmaciones), "versiones": [], "vacios": [], "alcance": "x"}
    return {**base, **extra}


def _a(texto, id_="N-a", campo="titulo", tipo="hecho"):
    return {"texto": texto, "tipo": tipo, "id_evidencia": id_, "campo": campo}


def _ficha(dbs, cliente, grupo="G-ECO"):
    motor, senales = dbs
    return generar.generar_ficha(grupo, cliente, motor, senales, REGLAS)


# --------------------------------------------------------------------------- T06

def test_T06_consulta_sin_respuesta_en_el_corpus_se_abstiene_sin_inventar(dbs):
    """T06: abstención explícita; ninguna cifra o cita inventada, y el modelo ni se consulta."""
    cliente = llm.ClienteFalso([_salida(_a("El turismo creció 12 % en junio.", id_="N-inventada"))])
    ficha = _ficha(dbs, cliente, grupo="G-VACIO")
    assert cliente.llamadas == []
    assert ficha["tipo_respuesta"] == "abstencion" and ficha["motivo_abstencion"] == "sin_evidencia"
    assert ficha["afirmaciones"] == [] and ficha["citas"] == [] and ficha["vacios"]
    assert "12" not in ficha["borrador"]
    assert ficha["estado_revision"] != "aprobado como borrador"


def test_T06_indicador_que_no_existe_se_abstiene_con_el_vacio_explicado(dbs):
    _, senales = dbs
    res = abstencion.consultar_indicador("XX.NO.EXISTE", 2024, senales)
    assert res["tipo_respuesta"] == "abstencion" and res["afirmaciones"] == []
    assert "no está en el corpus" in res["vacios"][0]


def test_T06_si_el_modelo_inventa_una_cita_la_ficha_se_abstiene(dbs):
    """Aun con evidencia, una cita a un id que no existe nunca llega al borrador."""
    cliente = llm.ClienteFalso([_salida(_a("La inflación fue de 9,9 %.", id_="N-no-existe"))])
    ficha = _ficha(dbs, cliente)
    assert ficha["tipo_respuesta"] == "abstencion" and ficha["afirmaciones"] == []
    assert "9,9" not in ficha["borrador"]
    assert ficha["descartadas"][0]["motivo"] == "evidencia_inexistente"


# --------------------------------------------------------------------------- T04

def test_T04_cifra_anual_del_banco_mundial_mantiene_pais_anio_y_unidad(dbs):
    """T04: citar el dato con país, año y unidad; no describirlo como cifra de hoy."""
    cliente = llm.ClienteFalso([_salida(
        _a("La inflación fue 0,7 % en 2024.", id_="IND-PAN-FP.CPI.TOTL.ZG-2024", campo="valor", tipo="hecho"))])
    ficha = _ficha(dbs, cliente)
    assert ficha["tipo_respuesta"] == "respuesta"
    assert {"id_evidencia": "IND-PAN-FP.CPI.TOTL.ZG-2024", "campo": "valor"} in ficha["citas"]
    b = ficha["borrador"]
    assert "PAN" in b or "Panamá" in b, "el borrador debe nombrar el país del dato"
    assert "2024" in b, "el borrador debe nombrar el año del dato"
    assert "%" in b, "el borrador debe conservar la unidad"
    assert "anual" in b.lower(), "debe decir que es un dato anual, no una medición de hoy"


def test_T04_el_prompt_pide_mantener_anio_y_trata_el_dato_como_anual(dbs):
    cliente = llm.ClienteFalso([_salida(_a("La inflación fue 0,7 % en 2024.", id_="IND-PAN-FP.CPI.TOTL.ZG-2024", campo="valor", tipo="hecho"))])
    _ficha(dbs, cliente)
    sistema, usuario, _ = cliente.llamadas[0]
    assert "anual" in sistema.lower()
    assert "IND-PAN-FP.CPI.TOTL.ZG-2024" in usuario and "2024" in usuario


def test_T04_cifra_de_otro_anio_o_inventada_no_pasa_el_validador(dbs):
    cliente = llm.ClienteFalso([_salida(
        _a("La inflación hoy es 5,5 %.", id_="IND-PAN-FP.CPI.TOTL.ZG-2024", campo="valor", tipo="hecho"))])
    ficha = _ficha(dbs, cliente)
    assert ficha["tipo_respuesta"] == "abstencion"
    assert ficha["descartadas"][0]["motivo"] == "cifra_no_sustentada"


def test_T04_el_codigo_agrega_pais_anio_y_unidad_aunque_el_modelo_los_omita(dbs):
    """El borrador no depende de que el modelo escriba el año o la unidad: los pone el código."""
    cliente = llm.ClienteFalso([_salida(
        _a("La inflación fue 0,7.", id_="IND-PAN-FP.CPI.TOTL.ZG-2024", campo="valor", tipo="hecho"))])
    ficha = _ficha(dbs, cliente)
    assert ficha["tipo_respuesta"] == "respuesta"
    linea = next(l for l in ficha["borrador"].splitlines() if "IND-PAN-FP.CPI.TOTL.ZG-2024" in l)
    assert "Panamá" in linea and "2024" in linea and "%" in linea
    assert "dato anual" in linea
