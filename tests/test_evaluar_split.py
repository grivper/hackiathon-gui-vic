"""Tests de motor/evaluar.py: particion ajuste/validacion por paridad de indice
(TAR-015, T1) y la seccion de macro-F1 por mitad en el reporte."""
from __future__ import annotations

from motor import evaluar


def _etiqueta(i: int) -> dict:
    return {"id_noticia": f"N-{i}", "titulo": f"titulo {i}", "tema_humano": "economia"}


# --------------------------------------------------------------------------- partir_muestra

def test_partir_muestra_separa_por_paridad_de_indice():
    etiquetas = [_etiqueta(i) for i in range(6)]  # indices 0..5

    partes = evaluar.partir_muestra(etiquetas)

    assert [e["id_noticia"] for e in partes["ajuste"]] == ["N-0", "N-2", "N-4"]
    assert [e["id_noticia"] for e in partes["validacion"]] == ["N-1", "N-3", "N-5"]
    assert partes["completa"] == etiquetas


def test_partir_muestra_preserva_el_orden_de_entrada():
    etiquetas = [_etiqueta(i) for i in [9, 1, 3, 2]]  # orden arbitrario, no ordenado

    partes = evaluar.partir_muestra(etiquetas)

    # paridad de INDICE (posicion en la lista), no del id_noticia
    assert [e["id_noticia"] for e in partes["ajuste"]] == ["N-9", "N-3"]
    assert [e["id_noticia"] for e in partes["validacion"]] == ["N-1", "N-2"]


def test_partir_muestra_con_cantidad_impar():
    etiquetas = [_etiqueta(i) for i in range(5)]  # 0,1,2,3,4 -> 3 pares, 2 impares

    partes = evaluar.partir_muestra(etiquetas)

    assert len(partes["ajuste"]) == 3
    assert len(partes["validacion"]) == 2
    assert len(partes["completa"]) == 5


def test_partir_muestra_vacia():
    partes = evaluar.partir_muestra([])
    assert partes == {"ajuste": [], "validacion": [], "completa": []}


def test_partir_muestra_mitades_disjuntas_y_union_es_la_completa():
    etiquetas = [_etiqueta(i) for i in range(11)]

    partes = evaluar.partir_muestra(etiquetas)

    ids_ajuste = {e["id_noticia"] for e in partes["ajuste"]}
    ids_validacion = {e["id_noticia"] for e in partes["validacion"]}
    assert ids_ajuste.isdisjoint(ids_validacion)
    assert ids_ajuste | ids_validacion == {e["id_noticia"] for e in partes["completa"]}
    assert len(partes["ajuste"]) + len(partes["validacion"]) == len(partes["completa"])

    # es deterministico: repetir la particion da exactamente lo mismo
    otra_vez = evaluar.partir_muestra(etiquetas)
    assert otra_vez == partes


# --------------------------------------------------------------------------- reporte: seccion por mitad

def test_formatear_reporte_incluye_seccion_de_macro_f1_por_mitad():
    etiquetas = [
        {"id_noticia": "N-0", "titulo": "t0", "tema_humano": "economia"},
        {"id_noticia": "N-1", "titulo": "t1", "tema_humano": "turismo"},
        {"id_noticia": "N-2", "titulo": "t2", "tema_humano": "economia"},
        {"id_noticia": "N-3", "titulo": "t3", "tema_humano": "turismo"},
    ]
    predicciones_embeddings = {e["id_noticia"]: e["tema_humano"] for e in etiquetas}  # acierta siempre
    resultados_por_metodo = {"embeddings": evaluar.evaluar_metodo(etiquetas, predicciones_embeddings)}

    reporte = evaluar.formatear_reporte(etiquetas, resultados_por_metodo)

    assert "## Macro-F1 por mitad (ajuste / validacion)" in reporte
    assert "paridad" in reporte.lower()
    assert "ambas" in reporte.lower()  # explica que el cambio debe mejorar ambas mitades
    assert "mitad | n | macro-F1 | abstencion" in reporte
    assert "| ajuste |" in reporte
    assert "| validacion |" in reporte
    assert "| completa |" in reporte


def test_formatear_reporte_mitad_sin_cobertura_no_rompe():
    # un metodo sin cobertura (None) no debe romper la seccion nueva
    etiquetas = [
        {"id_noticia": "N-0", "titulo": "t0", "tema_humano": "economia"},
        {"id_noticia": "N-1", "titulo": "t1", "tema_humano": "turismo"},
    ]
    resultados_por_metodo = {"tfidf": None}

    reporte = evaluar.formatear_reporte(etiquetas, resultados_por_metodo)

    assert "## Macro-F1 por mitad (ajuste / validacion)" in reporte
