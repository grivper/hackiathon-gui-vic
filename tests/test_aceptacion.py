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


# --------------------------------------------------------------------------- T08

def test_T08_caso_de_prioridad_alta_expone_componentes_y_regla(dbs):
    """T08: exponer componentes y regla; la prioridad no habilita publicación."""
    cliente = llm.ClienteFalso([_salida(_a("Según tvn-pa.com, la inflación cayó 0,3 % en junio."))])
    ficha = _ficha(dbs, cliente)
    assert ficha["prioridad"] == "alto" and ficha["puntaje"] == 96.0
    assert ficha["componentes"] == {"R": 1.0, "I": 1.0, "U": 1.0, "N": 1.0, "E": 0.6}
    assert ficha["version_reglas"] == "v0.3"
    assert "R=1.0" in ficha["motivos_puntaje"] and "E=0.6" in ficha["motivos_puntaje"]


def test_T08_la_prioridad_alta_no_publica_ni_aprueba_sola(dbs):
    from app import data  # noqa: PLC0415

    cliente = llm.ClienteFalso([_salida(_a("Según tvn-pa.com, la inflación cayó 0,3 % en junio."))])
    ficha = _ficha(dbs, cliente)
    assert ficha["estado_revision"] == "nuevo"
    assert not any("public" in e.lower() for e in data.VALID_REVIEW_STATES), "no existe un estado de publicación"


def test_T08_la_prioridad_alta_no_evita_la_abstencion_sin_evidencia(dbs):
    motor, _ = dbs
    con = duckdb.connect(str(motor))
    con.execute("UPDATE puntaje SET prioridad = 'alto', puntaje = 99 WHERE grupo_id = 'G-VACIO'")
    con.close()
    ficha = _ficha(dbs, llm.ClienteFalso([]), grupo="G-VACIO")
    assert ficha["prioridad"] == "alto" and ficha["tipo_respuesta"] == "abstencion"
    assert ficha["estado_revision"] == "requiere evidencia"


# --------------------------------------------------------------------------- T05

def _contradiccion():
    return _salida(
        _a("Según tvn-pa.com, la inflación cayó 0,3 % en junio.", id_="N-a"),
        _a("Según critica.com.pa, los precios bajan en Panamá.", id_="N-b"),
        tipo="contradiccion",
        versiones=["tvn-pa.com: la inflación cae 0,3 % en junio", "critica.com.pa: los precios bajan sin cifra"],
    )


def test_T05_afirmaciones_incompatibles_muestran_ambas_versiones_alcance_y_revision(dbs):
    """T05: mostrar ambas, su alcance y la revisión pendiente; no escoger arbitrariamente."""
    ficha = _ficha(dbs, llm.ClienteFalso([_contradiccion()]))
    assert ficha["tipo_respuesta"] == "contradiccion"
    b = ficha["borrador"]
    assert "tvn-pa.com" in b and "critica.com.pa" in b
    assert len(ficha["versiones"]) == 2
    assert "Alcance:" in b and "titular/metadatos" in b
    assert "revisión pendiente" in b.lower(), "la ficha debe decir que la contradicción espera revisión humana"
    assert ficha["estado_revision"] == "nuevo"
    assert {c["id_evidencia"] for c in ficha["citas"]} == {"N-a", "N-b"}


def test_T05_no_califica_ninguna_version_como_verdadera_o_falsa(dbs):
    ficha = _ficha(dbs, llm.ClienteFalso([_contradiccion()]))
    texto = ficha["borrador"].lower()
    assert "verdader" not in texto and "falso" not in texto


# --------------------------------------------------------------------------- T03

@pytest.fixture()
def dbs_recirculada(dbs):
    """N-old se publicó en 2024 y el sitemap la detectó otra vez en 2026; N-a solo tiene fecha de detección."""
    motor, senales = dbs
    con = duckdb.connect(str(senales))
    con.execute("DELETE FROM noticias WHERE id_noticia = 'N-b'")
    con.execute("INSERT INTO noticias VALUES ('N-old', 'Inflación cae 0,3 % en junio', 'http://old', 'tvn-pa.com', ?, ?)",
                [datetime(2024, 6, 12, 8, 0), datetime(2026, 7, 15, 22, 0)])
    con.close()
    con = duckdb.connect(str(motor))
    con.execute("INSERT INTO grupo_noticias VALUES ('G-ECO', 'N-old', 'tvn-pa.com', 0.95)")
    con.close()
    return dbs


def test_T03_noticia_antigua_recirculada_muestra_su_fecha_original_y_no_es_un_evento_nuevo(dbs_recirculada):
    """T03: mostrar la fecha original; no presentarla como un evento nuevo."""
    cliente = llm.ClienteFalso([_salida(_a("Según tvn-pa.com, la inflación cayó 0,3 % en junio.", id_="N-old"))])
    ficha = _ficha(dbs_recirculada, cliente)
    linea = next(l for l in ficha["borrador"].splitlines() if "[N-old" in l)
    assert "2024-06-12" in linea, "debe mostrar la fecha de publicación original"
    assert "no es un evento nuevo" in linea.lower()


def test_T03_noticia_sin_fecha_de_publicacion_dice_que_solo_se_conoce_la_deteccion(dbs_recirculada):
    cliente = llm.ClienteFalso([_salida(_a("Según tvn-pa.com, la inflación cayó 0,3 % en junio.", id_="N-a"))])
    ficha = _ficha(dbs_recirculada, cliente)
    linea = next(l for l in ficha["borrador"].splitlines() if "[N-a" in l)
    assert "2026-07-15" in linea and "detectada" in linea.lower()
    assert "no es un evento nuevo" not in linea.lower()


def test_T03_la_fecha_del_evento_es_la_de_publicacion_y_el_puntaje_de_urgencia_baja():
    """La urgencia (U) se calcula con la fecha original, no con la del rastreo."""
    from datetime import timedelta  # noqa: PLC0415

    import yaml  # noqa: PLC0415

    from motor import puntuar  # noqa: PLC0415

    reglas = yaml.safe_load(Path("motor/reglas_puntaje.yaml").read_text(encoding="utf-8"))
    ref = datetime(2026, 10, 8)
    assert puntuar.componente_U(ref - timedelta(days=850), ref, reglas) < puntuar.componente_U(ref - timedelta(hours=2), ref, reglas)
    assert puntuar.componente_U(ref - timedelta(days=850), ref, reglas) == reglas["u_tramos"][-1]["score"]


def test_T05_el_prompt_trae_un_ejemplo_de_contradiccion_con_versiones(dbs):
    """Un modelo chico imita los ejemplos: el prompt debe mostrar también cómo declarar una contradicción."""
    cliente = llm.ClienteFalso([_contradiccion()])
    _ficha(dbs, cliente)
    sistema = cliente.llamadas[0][0]
    assert '"tipo_respuesta": "contradiccion"' in sistema
    assert '"versiones": ["' in sistema
    assert "opuest" in sistema.lower()


def test_T05_dos_versiones_declaradas_por_el_modelo_cuentan_como_contradiccion(dbs):
    """Con el modelo real llenó `versiones` pero dijo `respuesta`: el código no se fía de la etiqueta."""
    salida = _contradiccion()
    salida["tipo_respuesta"] = "respuesta"
    ficha = _ficha(dbs, llm.ClienteFalso([salida]))
    assert ficha["tipo_respuesta"] == "contradiccion"
    assert "revisión pendiente" in ficha["borrador"].lower()


def test_T05_una_sola_version_o_ninguna_no_inventa_contradicciones(dbs):
    salida = _salida(_a("Según tvn-pa.com, la inflación cayó 0,3 % en junio."), versiones=["tvn-pa.com: cayó 0,3 %"])
    assert _ficha(dbs, llm.ClienteFalso([salida]))["tipo_respuesta"] == "respuesta"


def test_el_prompt_cabe_en_la_ventana_de_2048_tokens_con_margen(dbs):
    """El modelo real se cortó a mitad del JSON cuando el prompt creció: con este fixture el sistema mide ~2.730 caracteres (antes de T05 ~2.325); tope 2.800."""
    cliente = llm.ClienteFalso([_contradiccion()])
    _ficha(dbs, cliente)
    sistema, usuario, _ = cliente.llamadas[0]
    assert len(sistema) <= 2800, len(sistema)
