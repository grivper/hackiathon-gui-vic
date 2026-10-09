from motor.calcular_revision import precision5, validez


def test_validez_counts_ambiguous_as_not_supported():
    filas = [
        {"n": "1", "veredicto": "respaldada"},
        {"n": "2", "veredicto": "Respaldada"},
        {"n": "3", "veredicto": "no respaldada"},
        {"n": "4", "veredicto": "ambigua"},
        {"n": "5", "veredicto": ""},
    ]
    r = validez(filas)
    assert r["revisadas"] == 4
    assert r["validez"] == 0.5
    assert r["validez_sin_ambiguas"] == 2 / 3
    assert r["no_respaldadas"] == ["3"]


def test_validez_without_reviews_is_undefined():
    assert validez([{"n": "1", "veredicto": ""}])["validez"] is None


def test_precision5_uses_system_top5_and_reviewer_relevance():
    clave = [{"rango_sistema": str(i), "grupo_id": f"G{i}"} for i in range(1, 7)]
    cands = [
        {"grupo_id": "G1", "relevante_para_editor (si/no)": "si", "seleccion_top5 (si/no)": "si"},
        {"grupo_id": "G2", "relevante_para_editor (si/no)": "no", "seleccion_top5 (si/no)": ""},
        {"grupo_id": "G3", "relevante_para_editor (si/no)": "sí", "seleccion_top5 (si/no)": "si"},
        {"grupo_id": "G6", "relevante_para_editor (si/no)": "si", "seleccion_top5 (si/no)": "si"},
    ]
    r = precision5(cands, clave)
    assert r["top5_sistema"] == ["G1", "G2", "G3", "G4", "G5"]
    assert r["precision_at_5"] == 2 / 5
    assert r["coincidencias_con_seleccion"] == 2
