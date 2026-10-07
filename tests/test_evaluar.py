"""Tests de motor/evaluar.py y motor/muestra_etiquetado.py."""
from __future__ import annotations

import csv
from pathlib import Path

import duckdb
import pytest

from motor import evaluar, muestra_etiquetado

FIXTURE_ETIQUETAS = Path(__file__).parent / "fixtures" / "etiquetas_mini.csv"


def leer_fixture_etiquetas() -> list[dict]:
    with FIXTURE_ETIQUETAS.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


# --------------------------------------------------------------------------- cargar_etiquetas

def test_cargar_etiquetas_lee_las_24_filas_validas():
    etiquetas = evaluar.cargar_etiquetas(FIXTURE_ETIQUETAS)
    assert len(etiquetas) == 24
    temas = {e["tema_humano"] for e in etiquetas}
    assert temas <= set(evaluar.TEMAS_VALIDOS)


def test_cargar_etiquetas_descarta_filas_sin_etiquetar(tmp_path):
    ruta = tmp_path / "etiquetas.csv"
    ruta.write_text(
        "id_noticia,titulo,medio,fecha,tema_humano,notas\n"
        "N-1,titulo uno,Medio,2026-01-01,economia,\n"
        "N-2,titulo dos,Medio,2026-01-02,,\n",  # sin etiquetar todavia
        encoding="utf-8",
    )
    etiquetas = evaluar.cargar_etiquetas(ruta)
    assert len(etiquetas) == 1
    assert etiquetas[0]["id_noticia"] == "N-1"


def test_cargar_etiquetas_rechaza_valor_desconocido(tmp_path):
    ruta = tmp_path / "etiquetas.csv"
    ruta.write_text(
        "id_noticia,titulo,medio,fecha,tema_humano,notas\n"
        "N-1,titulo uno,Medio,2026-01-01,deportes,\n",  # no es uno de los 7 validos
        encoding="utf-8",
    )
    with pytest.raises(evaluar.EtiquetaInvalidaError, match="deportes"):
        evaluar.cargar_etiquetas(ruta)


# --------------------------------------------------------------------------- metricas (a mano)

def test_calcular_metricas_macro_f1_contra_calculo_a_mano():
    # Dos clases, 4 ejemplos. a: 2 aciertos de 2 reales (recall=1.0), 1 falso positivo
    # (otro real predicho como a) -> precision = 2/3. b: 1 acierto de 2 reales
    # (recall=0.5), sin falsos positivos -> precision = 1.0.
    y_true = ["a", "a", "b", "b"]
    y_pred = ["a", "a", "a", "b"]

    metricas = evaluar.calcular_metricas(y_true, y_pred)

    precision_a, recall_a = 2 / 3, 1.0
    f1_a = 2 * precision_a * recall_a / (precision_a + recall_a)
    precision_b, recall_b = 1.0, 0.5
    f1_b = 2 * precision_b * recall_b / (precision_b + recall_b)
    macro_f1_esperado = (f1_a + f1_b) / 2

    assert metricas["macro_f1"] == pytest.approx(macro_f1_esperado)

    por_tema = {fila["tema"]: fila for fila in metricas["por_clase"]}
    assert por_tema["a"]["precision"] == pytest.approx(precision_a)
    assert por_tema["a"]["recall"] == pytest.approx(recall_a)
    assert por_tema["a"]["soporte"] == 2
    assert por_tema["b"]["precision"] == pytest.approx(precision_b)
    assert por_tema["b"]["recall"] == pytest.approx(recall_b)


def test_tasa_abstencion():
    assert evaluar.tasa_abstencion(["otros", "otros", "economia", "turismo"]) == pytest.approx(0.5)
    assert evaluar.tasa_abstencion([]) == 0.0


# --------------------------------------------------------------------------- main (CLI, DuckDB temporal)

def _crear_motor_fixture(ruta: Path, filas_etiquetas: list[dict]) -> None:
    """Tabla `clasificacion` chiquita en un DuckDB temporal: el metodo 'embeddings'
    acierta siempre (para que el reporte tenga una senal clara que verificar) y el
    metodo 'tfidf' siempre abstiene (otros), para ejercitar la tasa de abstencion."""
    con = duckdb.connect(str(ruta))
    try:
        con.execute("""
            CREATE TABLE clasificacion (
                id_noticia TEXT, metodo TEXT, tema TEXT, score DOUBLE,
                segundo_tema TEXT, margen DOUBLE, modelo TEXT, contraste TEXT
            )
        """)
        for fila in filas_etiquetas:
            con.execute(
                "INSERT INTO clasificacion VALUES (?, 'embeddings', ?, 0.5, NULL, 0.1, 'modelo-test', NULL)",
                [fila["id_noticia"], fila["tema_humano"]],
            )
            con.execute(
                "INSERT INTO clasificacion VALUES (?, 'tfidf', 'otros', 0.1, NULL, 0.0, 'tfidf', NULL)",
                [fila["id_noticia"]],
            )
    finally:
        con.close()


def test_main_escribe_reporte_con_macro_f1_perfecto_y_abstencion_total(tmp_path, capsys):
    motor_path = tmp_path / "motor.duckdb"
    out_path = tmp_path / "evaluacion.md"
    filas_etiquetas = leer_fixture_etiquetas()
    _crear_motor_fixture(motor_path, filas_etiquetas)

    codigo = evaluar.main([
        "--etiquetas", str(FIXTURE_ETIQUETAS), "--motor", str(motor_path), "--out", str(out_path),
    ])
    assert codigo == 0
    salida = capsys.readouterr().out
    assert "embeddings" in salida
    assert "tfidf" in salida

    assert out_path.exists()
    contenido = out_path.read_text(encoding="utf-8")
    assert "Macro-F1: 1.000" in contenido  # embeddings "acierta" siempre en el fixture
    assert "Tasa de abstencion" in contenido
    assert "100.0%" in contenido  # tfidf siempre dijo otros


def test_main_reporta_faltan_etiquetas_si_menos_de_10(tmp_path, capsys):
    ruta_etiquetas = tmp_path / "pocas.csv"
    ruta_etiquetas.write_text(
        "id_noticia,titulo,medio,fecha,tema_humano,notas\n"
        "N-1,t1,M,2026-01-01,economia,\n"
        "N-2,t2,M,2026-01-01,turismo,\n",
        encoding="utf-8",
    )
    motor_path = tmp_path / "motor.duckdb"
    con = duckdb.connect(str(motor_path))
    con.execute("""
        CREATE TABLE clasificacion (
            id_noticia TEXT, metodo TEXT, tema TEXT, score DOUBLE,
            segundo_tema TEXT, margen DOUBLE, modelo TEXT, contraste TEXT
        )
    """)
    con.close()
    out_path = tmp_path / "evaluacion.md"

    codigo = evaluar.main([
        "--etiquetas", str(ruta_etiquetas), "--motor", str(motor_path), "--out", str(out_path),
    ])
    assert codigo == 0
    salida = capsys.readouterr().out
    assert "faltan etiquetas" in salida.lower()
    assert not out_path.exists()  # no reporte enganoso con 2 filas


# --------------------------------------------------------------------------- muestra_etiquetado

def _crear_db_noticias(ruta: Path, n_por_mes: int, meses: list[str]) -> None:
    con = duckdb.connect(str(ruta))
    try:
        con.execute("""
            CREATE TABLE noticias (
                id_noticia TEXT, titulo TEXT, url TEXT, medio TEXT, idioma TEXT,
                fecha_publicacion TIMESTAMP, fecha_deteccion TIMESTAMP, fecha_extraccion TIMESTAMP,
                tema TEXT, origen TEXT, alcance_texto TEXT
            )
        """)
        for mes in meses:
            for i in range(n_por_mes):
                id_ = f"N-{mes}-{i:03d}"
                con.execute(
                    "INSERT INTO noticias (id_noticia, titulo, medio, fecha_deteccion, origen) "
                    "VALUES (?, ?, 'Medio Test', CAST(? AS TIMESTAMP), 'tvn_rss')",
                    [id_, f"Titular {id_}", f"{mes}-15 00:00:00"],
                )
    finally:
        con.close()


def test_muestreo_estratificado_reparte_por_mes_y_es_reproducible(tmp_path):
    db_path = tmp_path / "senales.duckdb"
    meses = ["2026-01", "2026-02", "2026-03", "2026-04"]
    _crear_db_noticias(db_path, n_por_mes=20, meses=meses)

    filas = muestra_etiquetado.cargar_noticias(db_path, desde=None)
    seleccion1 = muestra_etiquetado.muestrear_estratificado_por_mes(filas, n=20, semilla=7)
    seleccion2 = muestra_etiquetado.muestrear_estratificado_por_mes(filas, n=20, semilla=7)

    assert len(seleccion1) == 20
    assert [f[0] for f in seleccion1] == [f[0] for f in seleccion2]  # mismo seed -> mismos ids

    meses_en_seleccion = sorted({str(f[3])[:7] for f in seleccion1})
    assert meses_en_seleccion == meses
    conteo_por_mes = {}
    for f in seleccion1:
        mes = str(f[3])[:7]
        conteo_por_mes[mes] = conteo_por_mes.get(mes, 0) + 1
    assert set(conteo_por_mes.values()) == {5}  # 20 / 4 meses, reparto exacto


def test_muestreo_con_semilla_distinta_da_otra_seleccion(tmp_path):
    db_path = tmp_path / "senales.duckdb"
    _crear_db_noticias(db_path, n_por_mes=20, meses=["2026-01", "2026-02"])
    filas = muestra_etiquetado.cargar_noticias(db_path, desde=None)

    seleccion_a = muestra_etiquetado.muestrear_estratificado_por_mes(filas, n=10, semilla=1)
    seleccion_b = muestra_etiquetado.muestrear_estratificado_por_mes(filas, n=10, semilla=2)
    assert [f[0] for f in seleccion_a] != [f[0] for f in seleccion_b]


def test_main_muestra_etiquetado_no_incluye_columnas_del_modelo(tmp_path):
    db_path = tmp_path / "senales.duckdb"
    out_path = tmp_path / "muestra.csv"
    _crear_db_noticias(db_path, n_por_mes=10, meses=["2026-01", "2026-02"])

    codigo = muestra_etiquetado.main([
        "--db", str(db_path), "--out", str(out_path), "--n", "10", "--semilla", "3",
    ])
    assert codigo == 0
    assert out_path.exists()

    with out_path.open(encoding="utf-8", newline="") as f:
        filas = list(csv.DictReader(f))
    assert len(filas) == 10
    columnas = set(filas[0].keys())
    assert columnas == {"id_noticia", "titulo", "medio", "fecha", "tema_humano", "notas"}
    for col in ("tema", "score", "contraste", "segundo_tema", "margen"):
        assert col not in columnas
    for fila in filas:
        assert fila["tema_humano"] == ""  # nadie etiqueto todavia

    assert (out_path.parent / "LEEME_etiquetado.md").exists()
