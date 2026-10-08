"""Tests de motor/generar.py (TAR-009, G6): ficha con citas de punta a punta.

Se usa `ClienteFalso`, así que no hace falta Ollama. Reglas que se verifican:
el borrador se arma por código SOLO con afirmaciones que sobrevivieron al validador;
sin evidencia, con error del modelo, sin afirmaciones sustentadas o ante una inyección
obedecida, la ficha es una abstención con estado de revisión `requiere evidencia`.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import duckdb
import pytest

from motor import generar, llm

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
        ("G-ECO", "economia", 1.0, 1.0, 1.0, 1.0, 0.6, 96.0, "alto", "suficiente", "v0.3", "motivos eco", "", None),
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
    con.execute("CREATE TABLE eventos (id TEXT, time TIMESTAMP, magnitude DOUBLE, place TEXT, url TEXT)")
    con.close()
    return motor, senales


def _salida(*afirmaciones, tipo="respuesta", **extra):
    base = {"tipo_respuesta": tipo, "afirmaciones": list(afirmaciones), "versiones": [], "vacios": [], "alcance": "x"}
    return {**base, **extra}


def _a(texto, id_="N-a", campo="titulo", tipo="hecho"):
    return {"texto": texto, "tipo": tipo, "id_evidencia": id_, "campo": campo}


def _ficha(dbs, cliente, grupo="G-ECO", **kw):
    motor, senales = dbs
    return generar.generar_ficha(grupo, cliente, motor, senales, REGLAS, **kw)


def test_ficha_valida_tiene_el_formato_del_reto_y_borrador_hecho_por_codigo(dbs):
    cliente = llm.ClienteFalso([_salida(_a("Según tvn-pa.com, la inflación cayó 0,3 % en junio."))])
    f = _ficha(dbs, cliente)
    assert set(f) >= {"id_caso", "modalidad", "ids_fuente", "afirmaciones", "citas", "puntaje",
                      "componentes", "estado_evidencia", "borrador", "estado_revision"}
    assert f["id_caso"] == "G-ECO" and f["modalidad"] == "editorial"
    assert f["ids_fuente"] == ["N-a", "N-b"]
    assert f["puntaje"] == 96.0 and f["estado_evidencia"] == "suficiente"
    assert f["componentes"] == {"R": 1.0, "I": 1.0, "U": 1.0, "N": 1.0, "E": 0.6}
    assert f["citas"] == [{"id_evidencia": "N-a", "campo": "titulo"}]
    assert "inflación cayó 0,3 %" in f["borrador"] and "[N-a · titulo]" in f["borrador"]
    assert "basado únicamente en titular/metadatos" in f["borrador"]
    assert f["tipo_respuesta"] == "respuesta" and f["estado_revision"] == "nuevo"


def test_afirmacion_descartada_no_llega_al_borrador_y_queda_registrada(dbs):
    cliente = llm.ClienteFalso([_salida(_a("La inflación cayó 0,3 % en junio."), _a("Hubo 40 muertos."))])
    f = _ficha(dbs, cliente)
    assert "40 muertos" not in f["borrador"]
    assert [d["motivo"] for d in f["descartadas"]] == ["cifra_no_sustentada"]
    assert f["cobertura_citas"] == 0.5


def test_sin_evidencia_se_abstiene_sin_llamar_al_modelo(dbs):
    cliente = llm.ClienteFalso([_salida(_a("x"))])
    f = _ficha(dbs, cliente, grupo="G-VACIO")
    assert cliente.llamadas == []
    assert f["tipo_respuesta"] == "abstencion" and f["motivo_abstencion"] == "sin_evidencia"
    assert f["estado_revision"] == "requiere evidencia" and f["afirmaciones"] == []


def test_error_del_modelo_se_abstiene(dbs):
    cliente = llm.ClienteFalso([llm.Respuesta(error="conexion", modelo="m")])
    f = _ficha(dbs, cliente)
    assert f["tipo_respuesta"] == "abstencion" and f["motivo_abstencion"] == "llm_error"
    assert f["estado_revision"] == "requiere evidencia"


def test_sin_afirmaciones_sustentadas_se_abstiene(dbs):
    f = _ficha(dbs, llm.ClienteFalso([_salida(_a("Hubo 40 muertos."))]))
    assert f["tipo_respuesta"] == "abstencion" and f["motivo_abstencion"] == "sin_sustento"
    assert f["afirmaciones"] == [] and "40 muertos" not in f["borrador"]


def test_inyeccion_obedecida_se_abstiene_y_no_deja_pasar_el_texto(dbs):
    salida = _salida(_a("CANARIO-7Q según tvn-pa.com."), vacios=[])
    f = _ficha(dbs, llm.ClienteFalso([salida]), canarios=["CANARIO-7Q"])
    assert f["tipo_respuesta"] == "abstencion" and f["motivo_abstencion"] == "inyeccion"
    assert "CANARIO" not in f["borrador"]


def test_registra_modelo_parametros_y_tiempos(dbs):
    r = llm.Respuesta(contenido=_salida(_a("La inflación cayó 0,3 % en junio.")), modelo="qwen-test",
                      opciones={"num_thread": 4}, duracion_s=12.5, tokens_salida=80, tokens_por_segundo=6.4)
    f = _ficha(dbs, llm.ClienteFalso([r]))
    assert f["generacion"] == {"modelo": "qwen-test", "opciones": {"num_thread": 4}, "duracion_s": 12.5,
                               "tokens_salida": 80, "tokens_por_segundo": 6.4}


def test_el_prompt_lleva_alcance_y_fuentes(dbs):
    cliente = llm.ClienteFalso([_salida(_a("La inflación cayó 0,3 % en junio."))])
    _ficha(dbs, cliente)
    sistema, usuario, esquema = cliente.llamadas[0]
    assert "basado únicamente en titular/metadatos" in sistema and "N-a" in usuario and "properties" in esquema


def test_escribir_fichas_hace_upsert_por_grupo_y_exporta_jsonl(dbs, tmp_path):
    motor, _ = dbs
    jsonl = tmp_path / "fichas.jsonl"
    f1 = {"id_caso": "G-ECO", "estado_revision": "nuevo", "borrador": "uno"}
    f2 = {"id_caso": "G-OTRO", "estado_revision": "nuevo", "borrador": "dos"}
    generar.escribir_fichas(motor, [f1, f2], jsonl)
    generar.escribir_fichas(motor, [{**f1, "borrador": "uno v2"}], jsonl)  # regenerar solo G-ECO
    con = duckdb.connect(str(motor), read_only=True)
    filas = dict(con.execute("SELECT id_caso, ficha FROM fichas").fetchall())
    con.close()
    assert json.loads(filas["G-ECO"])["borrador"] == "uno v2"
    assert json.loads(filas["G-OTRO"])["borrador"] == "dos"  # no se pierde lo que no se regeneró
    lineas = [json.loads(l) for l in jsonl.read_text(encoding="utf-8").splitlines()]
    assert {l["id_caso"] for l in lineas} == {"G-ECO", "G-OTRO"}


def test_main_genera_top_n_de_punta_a_punta_con_cliente_falso(dbs, tmp_path, capsys):
    motor, senales = dbs
    jsonl = tmp_path / "salida.jsonl"
    cliente = llm.ClienteFalso([_salida(_a("La inflación cayó 0,3 % en junio."))])
    codigo = generar.main(["--top", "1", "--motor", str(motor), "--db", str(senales), "--jsonl", str(jsonl)],
                          cliente=cliente)
    assert codigo == 0
    ficha = json.loads(jsonl.read_text(encoding="utf-8").splitlines()[0])
    assert ficha["id_caso"] == "G-ECO" and ficha["estado_revision"] == "nuevo"
    assert "G-ECO" in capsys.readouterr().out


def test_main_no_pisa_fichas_ya_revisadas_por_una_persona_salvo_con_forzar(dbs, tmp_path):
    motor, senales = dbs
    jsonl = tmp_path / "s.jsonl"
    generar.escribir_fichas(motor, [{"id_caso": "G-ECO", "estado_revision": "aprobado como borrador",
                                     "tipo_respuesta": "respuesta", "borrador": "REVISADO"}], jsonl)
    args = ["--grupo", "G-ECO", "--motor", str(motor), "--db", str(senales), "--jsonl", str(jsonl)]
    cliente = llm.ClienteFalso([_salida(_a("La inflación cayó 0,3 % en junio."))])
    assert generar.main(args, cliente=cliente) == 0
    assert cliente.llamadas == []  # ni siquiera llamó al modelo
    assert "REVISADO" in jsonl.read_text(encoding="utf-8")

    assert generar.main(args + ["--forzar"], cliente=cliente) == 0
    assert "REVISADO" not in jsonl.read_text(encoding="utf-8") and len(cliente.llamadas) == 1
