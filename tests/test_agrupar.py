"""Tests de motor/agrupar.py.

Los tests rápidos NO descargan ningún modelo: usan el mismo `FakeEncoder` determinista
(hashing de palabras, sin red) que tests/test_clasificar.py. Las similitudes exactas
entre los titulares de tests/fixtures/grupos_mini.csv fueron medidas a mano contra ese
encoder antes de escribir las aserciones (ver comentarios por caso). Un test extra usa
el modelo real y se salta si `modelos/` no tiene nada cacheado.
"""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import duckdb
import numpy as np
import pytest

from motor import agrupar, embeddings as emb_mod

FIXTURE_CSV = Path(__file__).parent / "fixtures" / "grupos_mini.csv"
DIM_FAKE = 64


def leer_fixture() -> list[dict]:
    with FIXTURE_CSV.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def filas_por_caso(caso: str) -> list[dict]:
    return [f for f in leer_fixture() if f["caso"] == caso]


class FakeEncoder:
    """Mismo encoder determinista que tests/test_clasificar.py: hashing de palabras
    (bag-of-words), sin red ni modelo real."""

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


def _crear_db(ruta: Path, filas: list[dict]) -> None:
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
                "INSERT INTO noticias (id_noticia, titulo, url, medio, fecha_deteccion) "
                "VALUES (?, ?, ?, ?, ?)",
                [f["id_noticia"], f["titulo"], f["url"], f["medio"], f["fecha"]],
            )
    finally:
        con.close()


def _preparar(monkeypatch, tmp_path):
    """Monkeypatchea el encoder (FakeEncoder) y la cache de embeddings a tmp_path, para
    que ningún test real toque la red ni la cache compartida de data/embeddings/."""
    fake_encoder = FakeEncoder()
    monkeypatch.setattr(emb_mod, "cargar_modelo", lambda modelo, modelos_dir=None: fake_encoder)
    monkeypatch.setattr(emb_mod, "EMBEDDINGS_DIR", tmp_path / "embeddings")
    return fake_encoder


def _grupo_que_contiene(con: duckdb.DuckDBPyConnection, id_noticia: str) -> str:
    fila = con.execute(
        "SELECT grupo_id FROM grupo_noticias WHERE id_noticia = ?", [id_noticia]
    ).fetchone()
    assert fila is not None, f"{id_noticia} no quedó en ningún grupo"
    return fila[0]


# --------------------------------------------------------------------------- procedencia / agencias

def test_procedencia_usa_el_dominio_por_defecto():
    assert agrupar.procedencia("tvn-2.com", "Un titular cualquiera", "https://www.tvn-2.com/x") == "tvn-2.com"


def test_procedencia_colapsa_marca_de_agencia_en_el_titulo():
    assert agrupar.procedencia(
        "panamaamerica.com.pa", "Terremoto en Chile deja heridos, informa la EFE", "https://x.com/y"
    ) == "agencia:EFE"


def test_procedencia_colapsa_europa_press_y_su_sigla_al_mismo_nombre():
    assert agrupar.procedencia("a.com", "Fulano declara a Europa Press", "https://a.com/n") == "agencia:EUROPA_PRESS"
    assert agrupar.procedencia("b.com", "Fulano declara a la EP", "https://b.com/n") == "agencia:EUROPA_PRESS"


def test_procedencia_no_matchea_subcadenas_dentro_de_otras_palabras():
    # "jefe" contiene "efe" pero no es la agencia EFE; "Apostol" contiene "ap" pero no AP.
    assert agrupar.procedencia("tvn-2.com", "El jefe de la institucion renuncio", "https://x.com/jefe") == "tvn-2.com"
    assert agrupar.procedencia("tvn-2.com", "Fiesta de Santiago Apostol", "https://x.com/apostol") == "tvn-2.com"


# --------------------------------------------------------------------------- T02: mismo evento, 3 medios

def test_t02_tres_medios_mismo_evento_se_agrupan_y_mantienen_las_3_fuentes(monkeypatch, tmp_path):
    # Similitudes medidas con FakeEncoder: T02-1~T02-2=0.97, T02-1~T02-3=0.869,
    # T02-2~T02-3=0.843: las tres superan el umbral por defecto (0.80) entre sí.
    _preparar(monkeypatch, tmp_path)
    filas = filas_por_caso("t02")
    db_path = tmp_path / "senales.duckdb"
    out_path = tmp_path / "motor.duckdb"
    _crear_db(db_path, filas)

    codigo = agrupar.main(["--db", str(db_path), "--out", str(out_path)])
    assert codigo == 0

    con = duckdb.connect(str(out_path), read_only=True)
    try:
        grupo_id = _grupo_que_contiene(con, "N-T02-1")
        assert _grupo_que_contiene(con, "N-T02-2") == grupo_id
        assert _grupo_que_contiene(con, "N-T02-3") == grupo_id

        fila = con.execute(
            "SELECT n_noticias, n_procedencias, corroboracion, es_repeticion FROM grupos WHERE grupo_id = ?",
            [grupo_id],
        ).fetchone()
        n_noticias, n_procedencias, corroboracion, es_repeticion = fila
        assert n_noticias == 3
        assert n_procedencias == 3  # tvn-2.com, panamaamerica.com.pa, prensa.com: ninguna repetida
        assert corroboracion == n_procedencias  # corroboracion = n_procedencias, NUNCA n_noticias
        assert es_repeticion is False

        procedencias_guardadas = {
            r[0] for r in con.execute(
                "SELECT procedencia FROM grupo_noticias WHERE grupo_id = ?", [grupo_id]
            ).fetchall()
        }
        assert procedencias_guardadas == {"tvn-2.com", "panamaamerica.com.pa", "prensa.com"}
    finally:
        con.close()


# --------------------------------------------------------------------------- repetición TVN-only (CU-03)

def test_repeticion_de_un_solo_medio_no_infla_la_corroboracion(monkeypatch, tmp_path):
    # Las 3 variantes son tvn-2.com cubriendo su propio evento en 3 secciones: repetir no
    # es corroborar (CU-03). Similitudes >= 0.80 entre sí, forman un único grupo.
    _preparar(monkeypatch, tmp_path)
    filas = filas_por_caso("tvn_repeticion")
    db_path = tmp_path / "senales.duckdb"
    out_path = tmp_path / "motor.duckdb"
    _crear_db(db_path, filas)

    assert agrupar.main(["--db", str(db_path), "--out", str(out_path)]) == 0

    con = duckdb.connect(str(out_path), read_only=True)
    try:
        grupo_id = _grupo_que_contiene(con, "N-REP-1")
        assert _grupo_que_contiene(con, "N-REP-2") == grupo_id
        assert _grupo_que_contiene(con, "N-REP-3") == grupo_id

        n_noticias, n_procedencias, corroboracion, es_repeticion = con.execute(
            "SELECT n_noticias, n_procedencias, corroboracion, es_repeticion FROM grupos WHERE grupo_id = ?",
            [grupo_id],
        ).fetchone()
        assert n_noticias == 3
        assert n_procedencias == 1  # un solo medio: una sola procedencia honesta
        assert corroboracion == 1
        assert es_repeticion is True
    finally:
        con.close()


# --------------------------------------------------------------------------- ventana de tiempo

def test_mismo_texto_fuera_de_la_ventana_de_tiempo_no_se_agrupa(monkeypatch, tmp_path):
    # Texto idéntico (coseno = 1.0) pero publicado con ~2 años de diferencia: fuera de
    # ±3 días, la ventana de tiempo debe impedir que se enlacen.
    _preparar(monkeypatch, tmp_path)
    filas = filas_por_caso("texto_lejos")
    db_path = tmp_path / "senales.duckdb"
    out_path = tmp_path / "motor.duckdb"
    _crear_db(db_path, filas)

    assert agrupar.main(["--db", str(db_path), "--out", str(out_path)]) == 0

    con = duckdb.connect(str(out_path), read_only=True)
    try:
        grupo_1 = _grupo_que_contiene(con, "N-FAR-1")
        grupo_2 = _grupo_que_contiene(con, "N-FAR-2")
        assert grupo_1 != grupo_2
        for grupo_id in (grupo_1, grupo_2):
            n_noticias = con.execute(
                "SELECT n_noticias FROM grupos WHERE grupo_id = ?", [grupo_id]
            ).fetchone()[0]
            assert n_noticias == 1
    finally:
        con.close()


# --------------------------------------------------------------------------- colapso de agencia (CU-03)

def test_misma_nota_de_agencia_en_dos_medios_cuenta_como_una_sola_procedencia(monkeypatch, tmp_path):
    # Mismo cable de EFE publicado por dos medios distintos: debe agruparse (coseno
    # 0.869 >= 0.80) y contar como UNA procedencia (agencia:EFE), no dos.
    _preparar(monkeypatch, tmp_path)
    filas = filas_por_caso("efe")
    db_path = tmp_path / "senales.duckdb"
    out_path = tmp_path / "motor.duckdb"
    _crear_db(db_path, filas)

    assert agrupar.main(["--db", str(db_path), "--out", str(out_path)]) == 0

    con = duckdb.connect(str(out_path), read_only=True)
    try:
        grupo_id = _grupo_que_contiene(con, "N-EFE-1")
        assert _grupo_que_contiene(con, "N-EFE-2") == grupo_id

        n_noticias, n_procedencias, procedencias = con.execute(
            "SELECT n_noticias, n_procedencias, procedencias FROM grupos WHERE grupo_id = ?",
            [grupo_id],
        ).fetchone()
        assert n_noticias == 2
        assert n_procedencias == 1
        assert procedencias == "agencia:EFE"
    finally:
        con.close()


# --------------------------------------------------------------------------- no encadenar A~B~C

def test_no_encadena_grupos_disimiles_a_traves_de_un_puente(monkeypatch, tmp_path):
    # A-B=0.526, B-C=0.585, A-C=0.286 (medido con FakeEncoder). Con umbral=0.50 el
    # union-find de la etapa 1 enlazaría A-B y B-C en un solo componente (A~B~C), pero
    # el average-linkage de la etapa 2 debe separar a A: fusiona primero B-C (mayor
    # promedio) y luego A vs {B,C} promedia (0.526+0.286)/2=0.406 < 0.50, no fusiona.
    _preparar(monkeypatch, tmp_path)
    filas = filas_por_caso("cadena")
    db_path = tmp_path / "senales.duckdb"
    out_path = tmp_path / "motor.duckdb"
    _crear_db(db_path, filas)

    assert agrupar.main(["--db", str(db_path), "--out", str(out_path), "--umbral", "0.50"]) == 0

    con = duckdb.connect(str(out_path), read_only=True)
    try:
        grupo_a = _grupo_que_contiene(con, "N-CAD-A")
        grupo_b = _grupo_que_contiene(con, "N-CAD-B")
        grupo_c = _grupo_que_contiene(con, "N-CAD-C")
        assert grupo_a != grupo_c  # el requisito central: A y C no deben terminar juntos
        assert grupo_b == grupo_c  # B y C sí se fusionan (su promedio supera el umbral)
    finally:
        con.close()


# --------------------------------------------------------------------------- tope de duraci\u00f3n (max-span-dias)


def test_segmento_diario_identico_se_parte_en_varios_grupos_sin_pasar_el_tope(monkeypatch, tmp_path):
    # 10 d\u00edas seguidos del mismo segmento fijo (\"Clima en Panam\u00e1\"), t\u00edtulo id\u00e9ntico
    # (coseno 1.0) y uno por d\u00eda: sin tope, la ventana de \u00b13 d\u00edas encadena los 10 en un
    # solo componente (d\u00eda0~d\u00eda1~...~d\u00eda9) y el average-linkage no los separa (todas
    # las similitudes son 1.0). Con --max-span-dias 3 (el default) el barrido de la
    # etapa 3 debe partirlo en subgrupos de a lo sumo 3 d\u00edas de span cada uno.
    _preparar(monkeypatch, tmp_path)
    filas = filas_por_caso("diario")
    db_path = tmp_path / "senales.duckdb"
    out_path = tmp_path / "motor.duckdb"
    _crear_db(db_path, filas)

    assert agrupar.main(["--db", str(db_path), "--out", str(out_path)]) == 0

    con = duckdb.connect(str(out_path), read_only=True)
    try:
        ids_diario = [f"N-DIA-{i:02d}" for i in range(1, 11)]
        grupos_vistos = {_grupo_que_contiene(con, id_) for id_ in ids_diario}
        # 10 d\u00edas repartidos en bloques de a lo sumo 4 d\u00edas de ancho (span <= 3) no caben
        # en un solo grupo: deben quedar varios grupos distintos.
        assert len(grupos_vistos) > 1

        for grupo_id in grupos_vistos:
            fecha_min, fecha_max, n_noticias = con.execute(
                "SELECT fecha_min, fecha_max, n_noticias FROM grupos WHERE grupo_id = ?", [grupo_id]
            ).fetchone()
            assert (fecha_max - fecha_min).total_seconds() <= 3 * 86400
            assert n_noticias >= 1

        total_en_estos_grupos = sum(
            con.execute(
                "SELECT count(*) FROM grupo_noticias WHERE grupo_id = ?", [grupo_id]
            ).fetchone()[0]
            for grupo_id in grupos_vistos
        )
        assert total_en_estos_grupos == 10
    finally:
        con.close()


def test_max_span_dias_mayor_permite_que_el_segmento_diario_quede_en_un_solo_grupo(monkeypatch, tmp_path):
    # Con un tope generoso (20 d\u00edas, mayor que el span real de 9 d\u00edas) el tope no corta
    # nada: el segmento diario queda en un \u00fanico grupo, como antes de este fix.
    _preparar(monkeypatch, tmp_path)
    filas = filas_por_caso("diario")
    db_path = tmp_path / "senales.duckdb"
    out_path = tmp_path / "motor.duckdb"
    _crear_db(db_path, filas)

    assert agrupar.main([
        "--db", str(db_path), "--out", str(out_path), "--max-span-dias", "20",
    ]) == 0

    con = duckdb.connect(str(out_path), read_only=True)
    try:
        ids_diario = [f"N-DIA-{i:02d}" for i in range(1, 11)]
        grupos_vistos = {_grupo_que_contiene(con, id_) for id_ in ids_diario}
        assert len(grupos_vistos) == 1
    finally:
        con.close()


# --------------------------------------------------------------------------- idempotencia

def test_main_es_idempotente(monkeypatch, tmp_path, capsys):
    _preparar(monkeypatch, tmp_path)
    filas = filas_por_caso("idempotencia")
    db_path = tmp_path / "senales.duckdb"
    out_path = tmp_path / "motor.duckdb"
    _crear_db(db_path, filas)

    codigo1 = agrupar.main(["--db", str(db_path), "--out", str(out_path)])
    assert codigo1 == 0
    salida1 = capsys.readouterr().out
    assert "Agrupación completa" in salida1

    con = duckdb.connect(str(out_path), read_only=True)
    try:
        n_grupos_1 = con.execute("SELECT count(*) FROM grupos").fetchone()[0]
    finally:
        con.close()

    codigo2 = agrupar.main(["--db", str(db_path), "--out", str(out_path)])
    assert codigo2 == 0
    salida2 = capsys.readouterr().out
    assert "sin cambios" in salida2

    codigo3 = agrupar.main(["--db", str(db_path), "--out", str(out_path), "--forzar"])
    assert codigo3 == 0
    salida3 = capsys.readouterr().out
    assert "Agrupación completa" in salida3

    con = duckdb.connect(str(out_path), read_only=True)
    try:
        n_grupos_3 = con.execute("SELECT count(*) FROM grupos").fetchone()[0]
    finally:
        con.close()
    assert n_grupos_1 == n_grupos_3


def test_no_pisa_las_tablas_de_clasificar(monkeypatch, tmp_path):
    """agrupar.py escribe en la misma base que clasificar.py (data/motor.duckdb): no
    debe borrar ni tocar `clasificacion` / `meta_clasificacion` si ya existen."""
    _preparar(monkeypatch, tmp_path)
    filas = filas_por_caso("idempotencia")
    db_path = tmp_path / "senales.duckdb"
    out_path = tmp_path / "motor.duckdb"
    _crear_db(db_path, filas)

    con = duckdb.connect(str(out_path))
    try:
        con.execute("CREATE TABLE clasificacion (id_noticia TEXT, tema TEXT)")
        con.execute("INSERT INTO clasificacion VALUES ('N-IDEM-1', 'economia')")
        con.execute("CREATE TABLE meta_clasificacion (esquema_version INTEGER)")
        con.execute("INSERT INTO meta_clasificacion VALUES (2)")
    finally:
        con.close()

    assert agrupar.main(["--db", str(db_path), "--out", str(out_path)]) == 0

    con = duckdb.connect(str(out_path), read_only=True)
    try:
        fila = con.execute("SELECT id_noticia, tema FROM clasificacion").fetchone()
        assert fila == ("N-IDEM-1", "economia")
        assert con.execute("SELECT count(*) FROM meta_clasificacion").fetchone()[0] == 1
        assert con.execute("SELECT count(*) FROM grupos").fetchone()[0] > 0
    finally:
        con.close()


# --------------------------------------------------------------------------- modelo real (opcional)

def _modelo_cacheado() -> bool:
    modelos_dir = Path(__file__).parent.parent / "modelos"
    return modelos_dir.exists() and any(modelos_dir.rglob("*.safetensors"))


@pytest.mark.skipif(not _modelo_cacheado(), reason="modelo no cacheado: correr 'make modelos' primero")
def test_agrupar_con_modelo_real_agrupa_titulares_del_mismo_evento(tmp_path):
    pares_evento = [
        ("N-R1", "El Banco Mundial proyecta un crecimiento economico de 4% para Panama en 2026"),
        ("N-R2", "Panama crecera 4% en 2026 segun proyecciones del Banco Mundial"),
        ("N-R3", "Turistas disfrutan del festival de playa en Bocas del Toro este fin de semana"),
    ]
    filas = [
        {"id_noticia": id_, "titulo": titulo, "url": f"https://www.tvn-2.com/n/{id_}", "medio": "tvn-2.com", "fecha": "2026-06-01T08:00:00"}
        for id_, titulo in pares_evento
    ]
    db_path = tmp_path / "senales.duckdb"
    out_path = tmp_path / "motor.duckdb"
    _crear_db(db_path, filas)

    assert agrupar.main(["--db", str(db_path), "--out", str(out_path)]) == 0

    con = duckdb.connect(str(out_path), read_only=True)
    try:
        grupo_r1 = _grupo_que_contiene(con, "N-R1")
        grupo_r2 = _grupo_que_contiene(con, "N-R2")
        grupo_r3 = _grupo_que_contiene(con, "N-R3")
        assert grupo_r1 == grupo_r2
        assert grupo_r3 != grupo_r1
    finally:
        con.close()
