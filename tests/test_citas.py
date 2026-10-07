"""Tests de motor/citas.py (TAR-009, G2): validador determinista de citas.

El LLM solo redacta; este módulo decide qué afirmaciones sobreviven. Una afirmación
sobrevive solo si cita un `id_evidencia` del paquete y un `campo` existente y no nulo de
ese ítem, y si cada cifra de su texto aparece en el ítem citado.
"""
from __future__ import annotations

import pytest

from motor import citas

PAQUETE = {
    "grupo_id": "G-1", "tema": "economia",
    "items": [
        {"id_evidencia": "N-a", "tipo": "noticia", "campos": {
            "titulo": "Inflación cae 0,3 % en junio", "medio": "tvn-pa.com", "url": "http://a",
            "fecha_publicacion": None, "fecha_deteccion": "2026-07-15T20:00:00"}},
        {"id_evidencia": "IND-PAN-FP.CPI.TOTL.ZG-2024", "tipo": "indicador", "campos": {
            "indicador_nombre": "Inflación", "anio": 2024, "valor": 2.9123, "unidad": "% anual", "fuente_url": "http://wb"}},
    ],
}


def _salida(*afirmaciones, tipo="respuesta", **extra):
    return {"tipo_respuesta": tipo, "afirmaciones": list(afirmaciones), "versiones": [], "vacios": [], **extra}


def _afirm(texto, id_evidencia="N-a", campo="titulo", tipo="hecho"):
    return {"texto": texto, "tipo": tipo, "id_evidencia": id_evidencia, "campo": campo}


def _motivos(res):
    return [d["motivo"] for d in res["descartadas"]]


def test_afirmacion_citada_correctamente_sobrevive():
    res = citas.validar_citas(_salida(_afirm("La inflación cayó 0,3 % en junio.")), PAQUETE)
    assert res["valida"] is True
    assert len(res["afirmaciones"]) == 1 and res["descartadas"] == []
    assert res["cobertura"] == 1.0 and res["tipo_respuesta"] == "respuesta"


def test_cifra_redondeada_del_indicador_es_valida():
    a = _afirm("La inflación de 2024 fue 2,9 % anual.", "IND-PAN-FP.CPI.TOTL.ZG-2024", "valor")
    # 2024 no está en `valor`; sí en `anio` del mismo ítem -> el ítem completo respalda las cifras
    res = citas.validar_citas(_salida(a), PAQUETE)
    assert len(res["afirmaciones"]) == 1, res["descartadas"]


def test_id_inexistente_se_descarta():
    res = citas.validar_citas(_salida(_afirm("Algo.", "N-zzz")), PAQUETE)
    assert _motivos(res) == ["evidencia_inexistente"] and res["afirmaciones"] == []


def test_sin_cita_se_descarta():
    a = {"texto": "Algo sin fuente.", "tipo": "hecho"}
    assert _motivos(citas.validar_citas(_salida(a), PAQUETE)) == ["sin_cita"]
    b = _afirm("Algo.", id_evidencia="")
    assert _motivos(citas.validar_citas(_salida(b), PAQUETE)) == ["sin_cita"]


def test_campo_inexistente_o_nulo_se_descarta():
    inexistente = _afirm("Algo.", campo="autor")
    nulo = _afirm("Algo.", campo="fecha_publicacion")
    assert _motivos(citas.validar_citas(_salida(inexistente), PAQUETE)) == ["campo_inexistente"]
    assert _motivos(citas.validar_citas(_salida(nulo), PAQUETE)) == ["campo_nulo"]


@pytest.mark.parametrize("texto", [
    "La inflación cayó 0,5 % en junio.",  # cifra distinta
    "La inflación cayó 3 % en junio.",  # 3 no es 0,3
    "Hubo 40 muertos.",  # cifra inventada
])
def test_cifra_no_sustentada_se_descarta(texto):
    assert _motivos(citas.validar_citas(_salida(_afirm(texto)), PAQUETE)) == ["cifra_no_sustentada"]


def test_tipo_invalido_y_texto_vacio():
    assert _motivos(citas.validar_citas(_salida(_afirm("Algo.", tipo="rumor")), PAQUETE)) == ["tipo_invalido"]
    assert _motivos(citas.validar_citas(_salida(_afirm("   ")), PAQUETE)) == ["texto_vacio"]


def test_cobertura_parcial_y_descartadas_registran_la_afirmacion():
    ok = _afirm("La inflación cayó 0,3 % en junio.")
    mala = _afirm("Hubo 40 muertos.")
    res = citas.validar_citas(_salida(ok, mala), PAQUETE)
    assert res["cobertura"] == 0.5
    assert res["descartadas"][0]["afirmacion"]["texto"] == "Hubo 40 muertos."


def test_respuesta_sin_afirmaciones_validas_pasa_a_abstencion():
    res = citas.validar_citas(_salida(_afirm("Hubo 40 muertos.")), PAQUETE)
    assert res["tipo_respuesta"] == "abstencion"


def test_abstencion_declarada_se_respeta_y_no_tiene_afirmaciones():
    res = citas.validar_citas(_salida(tipo="abstencion", vacios=["Falta el dato"]), PAQUETE)
    assert res["valida"] is True and res["tipo_respuesta"] == "abstencion"
    assert res["vacios"] == ["Falta el dato"]


@pytest.mark.parametrize("salida", [
    None, "texto libre", [], {"afirmaciones": []},
    {"tipo_respuesta": "inventada", "afirmaciones": []},
    {"tipo_respuesta": "respuesta", "afirmaciones": "no es lista"},
])
def test_esquema_invalido_no_deja_pasar_nada(salida):
    res = citas.validar_citas(salida, PAQUETE)
    assert res["valida"] is False and res["afirmaciones"] == [] and res["errores_esquema"]
    assert res["tipo_respuesta"] == "abstencion"


def test_la_cita_no_puede_apuntar_a_otro_grupo_ni_a_ids_fuera_del_paquete():
    # un id plausible pero que no pertenece al paquete (p. ej. inyectado por una fuente)
    res = citas.validar_citas(_salida(_afirm("Algo.", "IND-PAN-SL.UEM.TOTL.ZS-2022", "valor")), PAQUETE)
    assert _motivos(res) == ["evidencia_inexistente"]
