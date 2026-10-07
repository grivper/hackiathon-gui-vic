"""Tests de motor/clasificar.py y motor/embeddings.py.

Los tests rápidos NO descargan ningún modelo: el encoder de sentence-transformers se
reemplaza por un `FakeEncoder` determinista (hashing de palabras). El baseline TF-IDF
corre de verdad (sklearn, sin red). Un test extra usa el modelo real y se salta si
`modelos/` no tiene nada cacheado (`make modelos` aún no se corrió).
"""
from __future__ import annotations

import csv
import hashlib
import os
from pathlib import Path

import duckdb
import numpy as np
import pytest

from motor import clasificar, embeddings as emb_mod

FIXTURE_CSV = Path(__file__).parent / "fixtures" / "noticias_temas_mini.csv"
RUTA_TEMAS = Path(__file__).parent.parent / "motor" / "temas.yaml"
DIM_FAKE = 64


def leer_fixture() -> list[dict]:
    with FIXTURE_CSV.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


class FakeEncoder:
    """Encoder determinista basado en hashing de palabras (bag-of-words), sin red."""

    def __init__(self, dim: int = DIM_FAKE):
        self.dim = dim
        self.llamadas = 0

    def encode(self, textos, batch_size=64, show_progress_bar=False, convert_to_numpy=True):
        self.llamadas += 1
        matriz = np.zeros((len(textos), self.dim), dtype=np.float32)
        for i, texto in enumerate(textos):
            for palabra in texto.lower().split():
                idx = int(hashlib.sha1(palabra.encode()).hexdigest(), 16) % self.dim
                matriz[i, idx] += 1.0
        return matriz


# --------------------------------------------------------------------------- temas.yaml

def test_cargar_temas_lee_los_6_temas_y_parametros():
    parametros, temas, contraste = clasificar.cargar_temas(RUTA_TEMAS)
    nombres = {t["nombre"] for t in temas}
    assert nombres == {
        "economia", "logistica_canal", "turismo",
        "servicios_publicos", "eventos_naturales", "regulacion",
    }
    assert "modelo" in parametros
    assert "umbral_score" in parametros
    assert "umbral_margen" in parametros
    for tema in temas:
        assert tema["descripcion"]
        assert len(tema["semillas"]) >= 5
        assert tema["descripcion"] in tema["texto"]


def test_cargar_temas_lee_grupos_de_contraste():
    _, _, contraste = clasificar.cargar_temas(RUTA_TEMAS)
    nombres = {c["nombre"] for c in contraste}
    assert {"deportes", "sucesos_policiales", "politica_general", "salud", "educacion"} <= nombres
    for grupo in contraste:
        assert grupo["descripcion"]
        assert len(grupo["semillas"]) >= 8
        assert grupo["descripcion"] in grupo["texto"]


# --------------------------------------------------------------------------- abstención

def test_clasificar_matriz_abstiene_por_score_bajo():
    nombres_combinados = ["a", "b"]
    matriz = np.array([[0.05, 0.02]])  # ambos scores bajos
    resultado = clasificar.clasificar_matriz(
        matriz, nombres_combinados, nombres_temas=["a", "b"], umbral_score=0.3, umbral_margen=0.03
    )
    assert resultado[0][0] == "otros"
    assert resultado[0][4] is None  # no gan\u00f3 ning\u00fan grupo de contraste, es ambig\u00fcedad entre temas


def test_clasificar_matriz_abstiene_por_margen_bajo():
    nombres_combinados = ["a", "b"]
    matriz = np.array([[0.50, 0.49]])  # score alto pero casi empatado
    resultado = clasificar.clasificar_matriz(
        matriz, nombres_combinados, nombres_temas=["a", "b"], umbral_score=0.3, umbral_margen=0.05
    )
    assert resultado[0][0] == "otros"
    assert resultado[0][4] is None


def test_clasificar_matriz_asigna_tema_claro():
    nombres_combinados = ["a", "b"]
    matriz = np.array([[0.80, 0.10]])
    resultado = clasificar.clasificar_matriz(
        matriz, nombres_combinados, nombres_temas=["a", "b"], umbral_score=0.3, umbral_margen=0.03
    )
    tema, score, segundo, margen, contraste = resultado[0]
    assert tema == "a"
    assert segundo == "b"
    assert margen == pytest.approx(0.70)
    assert contraste is None


def test_clasificar_matriz_otros_por_grupo_de_contraste_guarda_el_nombre():
    # "a" es un tema valido, "ruido" es un grupo de contraste: gana "ruido" -> otros,
    # y se guarda cual grupo gano para poder explicarlo.
    nombres_combinados = ["a", "ruido"]
    matriz = np.array([[0.20, 0.70]])
    resultado = clasificar.clasificar_matriz(
        matriz, nombres_combinados, nombres_temas=["a"], umbral_score=0.3, umbral_margen=0.03
    )
    tema, score, segundo, margen, contraste = resultado[0]
    assert tema == "otros"
    assert contraste == "ruido"
    assert segundo == "a"


def test_clasificar_matriz_tema_claro_aunque_haya_contraste_de_fondo():
    nombres_combinados = ["a", "ruido"]
    matriz = np.array([[0.70, 0.10]])
    resultado = clasificar.clasificar_matriz(
        matriz, nombres_combinados, nombres_temas=["a"], umbral_score=0.3, umbral_margen=0.03
    )
    tema, score, segundo, margen, contraste = resultado[0]
    assert tema == "a"
    assert contraste is None
    assert segundo == "ruido"


# --------------------------------------------------------------------------- cache de embeddings incremental

def test_embeddings_incrementales_cachea_y_no_recalcula(tmp_path):
    encoder = FakeEncoder()
    ids = ["N-1", "N-2", "N-3"]
    textos = ["hola mundo", "canal de panama", "turismo playa"]

    vectores1 = emb_mod.embeddings_incrementales(encoder, "modelo-test", ids, textos, cache_dir=tmp_path)
    assert encoder.llamadas == 1
    assert set(vectores1.keys()) == set(ids)

    # Segunda corrida con los mismos ids: no debe volver a codificar nada.
    vectores2 = emb_mod.embeddings_incrementales(encoder, "modelo-test", ids, textos, cache_dir=tmp_path)
    assert encoder.llamadas == 1
    for id_ in ids:
        assert np.array_equal(vectores1[id_], vectores2[id_])

    # Tercera corrida agregando un id nuevo: solo codifica el nuevo.
    ids_mas = ids + ["N-4"]
    textos_mas = textos + ["nueva noticia distinta"]
    vectores3 = emb_mod.embeddings_incrementales(encoder, "modelo-test", ids_mas, textos_mas, cache_dir=tmp_path)
    assert encoder.llamadas == 2
    assert set(vectores3.keys()) == set(ids_mas)
    for id_ in ids:
        assert np.array_equal(vectores1[id_], vectores3[id_])


def test_codificar_normaliza_l2():
    encoder = FakeEncoder()
    vectores = emb_mod.codificar(encoder, ["canal de panama", "turismo"])
    normas = np.linalg.norm(vectores, axis=1)
    np.testing.assert_allclose(normas, 1.0, atol=1e-5)


# --------------------------------------------------------------------------- modo offline

def test_activa_offline_si_hay_cache_local(tmp_path, monkeypatch):
    modelos_dir = tmp_path / "modelos"
    modelos_dir.mkdir()
    (modelos_dir / "algo.bin").write_bytes(b"x")  # simula que ya hay algo descargado
    monkeypatch.delenv("HF_HUB_OFFLINE", raising=False)
    monkeypatch.delenv("TRANSFORMERS_OFFLINE", raising=False)

    activo = emb_mod.activar_modo_offline_si_hay_cache(modelos_dir)

    assert activo is True
    assert os.environ["HF_HUB_OFFLINE"] == "1"
    assert os.environ["TRANSFORMERS_OFFLINE"] == "1"


def test_no_activa_offline_si_no_hay_cache_local(tmp_path, monkeypatch):
    modelos_dir = tmp_path / "modelos_vacio"  # ni siquiera existe
    monkeypatch.delenv("HF_HUB_OFFLINE", raising=False)
    monkeypatch.delenv("TRANSFORMERS_OFFLINE", raising=False)

    activo = emb_mod.activar_modo_offline_si_hay_cache(modelos_dir)

    assert activo is False
    assert "HF_HUB_OFFLINE" not in os.environ
    assert "TRANSFORMERS_OFFLINE" not in os.environ


def test_no_pisa_un_valor_offline_ya_puesto_por_el_entorno(tmp_path, monkeypatch):
    modelos_dir = tmp_path / "modelos_vacio"
    monkeypatch.setenv("HF_HUB_OFFLINE", "0")  # el entorno ya decidio algo: no pisarlo

    emb_mod.activar_modo_offline_si_hay_cache(modelos_dir)

    assert os.environ["HF_HUB_OFFLINE"] == "0"


# --------------------------------------------------------------------------- baseline TF-IDF (real, sin red)

def test_tfidf_clasifica_fixture_razonablemente_bien():
    filas = leer_fixture()
    titulos = [f["titulo"] for f in filas]
    esperados = [f["tema_esperado"] for f in filas]

    _, temas, contraste = clasificar.cargar_temas(RUTA_TEMAS)
    vectorizador = clasificar.construir_vectorizador_tfidf(titulos)
    resultado = clasificar.clasificar_tfidf(
        vectorizador, temas, contraste, titulos, umbral_score=0.05, umbral_margen=0.0
    )
    predichos = [r[0] for r in resultado]

    aciertos_tema = sum(
        1 for pred, esp in zip(predichos, esperados) if esp != "otros" and pred == esp
    )
    total_tema = sum(1 for esp in esperados if esp != "otros")
    assert aciertos_tema / total_tema >= 0.6  # baseline simple, tolerante


def test_tfidf_abstiene_en_titulares_no_relacionados():
    filas = leer_fixture()
    titulos = [f["titulo"] for f in filas]
    esperados = [f["tema_esperado"] for f in filas]

    _, temas, contraste = clasificar.cargar_temas(RUTA_TEMAS)
    vectorizador = clasificar.construir_vectorizador_tfidf(titulos)
    # Umbral de score alto para forzar abstención en los titulares ambiguos ("otros").
    resultado = clasificar.clasificar_tfidf(
        vectorizador, temas, contraste, titulos, umbral_score=0.15, umbral_margen=0.02
    )
    predichos = {f["id_noticia"]: r[0] for f, r in zip(filas, resultado)}
    otros_ids = [f["id_noticia"] for f in filas if f["tema_esperado"] == "otros"]
    abstenidos = sum(1 for id_ in otros_ids if predichos[id_] == "otros")
    assert abstenidos >= 2  # al menos la mayoría de los claramente ajenos abstienen


# --------------------------------------------------------------------------- idempotencia del CLI (main)

def _crear_db_fixture(ruta: Path) -> None:
    filas = leer_fixture()
    con = duckdb.connect(str(ruta))
    try:
        con.execute("""
            CREATE TABLE noticias (
                id_noticia TEXT, titulo TEXT, url TEXT, medio TEXT, idioma TEXT,
                fecha_publicacion TIMESTAMP, fecha_deteccion TIMESTAMP, fecha_extraccion TIMESTAMP,
                tema TEXT, origen TEXT, alcance_texto TEXT
            )
        """)
        for f in filas:
            con.execute(
                "INSERT INTO noticias (id_noticia, titulo, url, fecha_deteccion, origen) "
                "VALUES (?, ?, ?, TIMESTAMP '2026-01-01 00:00:00', 'tvn_rss')",
                [f["id_noticia"], f["titulo"], f"https://example.com/{f['id_noticia']}"],
            )
    finally:
        con.close()


def test_main_es_idempotente(tmp_path, monkeypatch, capsys):
    db_path = tmp_path / "senales.duckdb"
    out_path = tmp_path / "motor.duckdb"
    _crear_db_fixture(db_path)

    fake_encoder = FakeEncoder()
    monkeypatch.setattr(emb_mod, "cargar_modelo", lambda modelo, modelos_dir=None: fake_encoder)
    monkeypatch.setattr(emb_mod, "EMBEDDINGS_DIR", tmp_path / "embeddings")

    codigo1 = clasificar.main([
        "--db", str(db_path), "--out", str(out_path), "--temas", str(RUTA_TEMAS),
    ])
    assert codigo1 == 0
    salida1 = capsys.readouterr().out
    assert "Clasificación completa" in salida1

    con = duckdb.connect(str(out_path), read_only=True)
    try:
        n_filas = con.execute("SELECT count(*) FROM clasificacion").fetchone()[0]
    finally:
        con.close()
    assert n_filas == len(leer_fixture()) * 2  # embeddings + tfidf

    # Segunda corrida sin --forzar: nada cambió, debe saltarse.
    codigo2 = clasificar.main([
        "--db", str(db_path), "--out", str(out_path), "--temas", str(RUTA_TEMAS),
    ])
    assert codigo2 == 0
    salida2 = capsys.readouterr().out
    assert "sin cambios" in salida2

    # Con --forzar sí reconstruye.
    codigo3 = clasificar.main([
        "--db", str(db_path), "--out", str(out_path), "--temas", str(RUTA_TEMAS), "--forzar",
    ])
    assert codigo3 == 0
    salida3 = capsys.readouterr().out
    assert "Clasificación completa" in salida3


# --------------------------------------------------------------------------- modelo real (opcional)

def _modelo_cacheado() -> bool:
    modelos_dir = Path(__file__).parent.parent / "modelos"
    return modelos_dir.exists() and any(modelos_dir.rglob("*.safetensors"))


@pytest.mark.skipif(not _modelo_cacheado(), reason="modelo no cacheado: correr 'make modelos' primero")
def test_embeddings_reales_clasifican_fixture_razonablemente_bien():
    filas = leer_fixture()
    titulos = [f["titulo"] for f in filas]
    esperados = [f["tema_esperado"] for f in filas]

    parametros, temas, contraste = clasificar.cargar_temas(RUTA_TEMAS)
    encoder = emb_mod.cargar_modelo(parametros["modelo"])
    resultado = clasificar.clasificar_embeddings(
        encoder, parametros["modelo"], temas, contraste,
        [f["id_noticia"] for f in filas], titulos,
        umbral_score=parametros["umbral_score"], umbral_margen=parametros["umbral_margen"],
        cache_dir=Path("data/embeddings"),
    )
    predichos = [r[0] for r in resultado]
    aciertos = sum(1 for pred, esp in zip(predichos, esperados) if pred == esp)
    assert aciertos / len(esperados) >= 0.6


# ------------------------------------------------- set de regresi\u00f3n (etiquetas_mini.csv)

ETIQUETAS_MINI_CSV = Path(__file__).parent / "fixtures" / "etiquetas_mini.csv"


def leer_etiquetas_mini() -> list[dict]:
    with ETIQUETAS_MINI_CSV.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


@pytest.mark.skipif(not _modelo_cacheado(), reason="modelo no cacheado: correr 'make modelos' primero")
def test_embeddings_reales_acuerdan_80pct_con_etiquetas_dev_mini():
    """Set de regresi\u00f3n chico (24 titulares) escrito a ojo por el desarrollador, NO son
    las etiquetas humanas ciegas de evaluaci\u00f3n (esas las produce muestra_etiquetado.py /
    evaluar.py). Sirve para detectar regresiones obvias al tocar temas.yaml/umbrales."""
    filas = leer_etiquetas_mini()
    titulos = [f["titulo"] for f in filas]
    esperados = [f["tema_humano"] for f in filas]

    parametros, temas, contraste = clasificar.cargar_temas(RUTA_TEMAS)
    encoder = emb_mod.cargar_modelo(parametros["modelo"])
    resultado = clasificar.clasificar_embeddings(
        encoder, parametros["modelo"], temas, contraste,
        [f["id_noticia"] for f in filas], titulos,
        umbral_score=parametros["umbral_score"], umbral_margen=parametros["umbral_margen"],
        cache_dir=Path("data/embeddings"),
    )
    predichos = [r[0] for r in resultado]
    aciertos = sum(1 for pred, esp in zip(predichos, esperados) if pred == esp)
    acuerdo = aciertos / len(esperados)
    print(f"\nAcuerdo con etiquetas_mini.csv (desarrollador, no evaluaci\u00f3n): {aciertos}/{len(esperados)} ({100*acuerdo:.1f}%)")
    assert acuerdo >= 0.8
