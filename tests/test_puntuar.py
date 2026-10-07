"""Tests de motor/puntuar.py (TAR-008): puntaje de atención y estado de evidencia.

Sin red, sin modelos: todo el componente es determinista a partir de `grupos`,
`clasificacion` (embeddings) y el contexto oficial (`indicadores` / `eventos`). Los
fixtures CSV (`tests/fixtures/puntaje_*.csv`) describen un escenario chico a mano, con
las cuentas de cada componente documentadas en los comentarios de cada test.
"""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

import duckdb
import pytest
import yaml

from motor import puntuar

FIXTURES = Path(__file__).parent / "fixtures"
RUTA_REGLAS = Path(__file__).parent.parent / "motor" / "reglas_puntaje.yaml"


def _leer_csv(nombre: str) -> list[dict]:
    with (FIXTURES / nombre).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def reglas() -> dict:
    return puntuar.cargar_reglas(RUTA_REGLAS)


# --------------------------------------------------------------------------- reglas_puntaje.yaml

def test_reglas_puntaje_reales_cargan_y_los_pesos_suman_100(reglas):
    assert reglas["version"] == "v0.1"
    assert sum(reglas["pesos"].values()) == 100


def test_cargar_reglas_rechaza_pesos_que_no_suman_100(tmp_path):
    datos = {
        "version": "vx", "pesos": {"R": 30, "I": 25, "U": 20, "N": 15, "E": 5},
        "rangos": {"bajo": {"lo": 0, "hi": 40}, "medio": {"lo": 40, "hi": 70}, "alto": {"lo": 70, "hi": 100}},
        "temas_reto": [], "medios_nacionales": [], "fuentes_primarias": {},
        "u_tramos": [{"horas_max": None, "score": 1.0}],
        "impacto_alcance": {"nacional": {"score": 1.0, "palabras_clave": []},
                             "sectorial": {"score": 0.6, "palabras_clave": []},
                             "local": {"score": 0.3}},
        "novedad": {"nuevo": 1.0, "repeticion": 0.2}, "evidencia": {},
    }
    ruta = tmp_path / "reglas_invalidas.yaml"
    ruta.write_text(yaml.safe_dump(datos), encoding="utf-8")
    with pytest.raises(ValueError, match="suman"):
        puntuar.cargar_reglas(ruta)


def test_cargar_reglas_rechaza_rangos_solapados_o_con_huecos(tmp_path):
    datos = {
        "version": "vx", "pesos": {"R": 30, "I": 25, "U": 20, "N": 15, "E": 10},
        "rangos": {"bajo": {"lo": 0, "hi": 40}, "medio": {"lo": 35, "hi": 70}, "alto": {"lo": 70, "hi": 100}},
        "temas_reto": [], "medios_nacionales": [], "fuentes_primarias": {},
        "u_tramos": [{"horas_max": None, "score": 1.0}],
        "impacto_alcance": {"nacional": {"score": 1.0, "palabras_clave": []},
                             "sectorial": {"score": 0.6, "palabras_clave": []},
                             "local": {"score": 0.3}},
        "novedad": {"nuevo": 1.0, "repeticion": 0.2}, "evidencia": {},
    }
    ruta = tmp_path / "reglas_invalidas.yaml"
    ruta.write_text(yaml.safe_dump(datos), encoding="utf-8")
    with pytest.raises(ValueError, match="rangos"):
        puntuar.cargar_reglas(ruta)


# --------------------------------------------------------------------------- componente_R

def test_componente_r_medio_nacional_y_tema_del_reto(reglas):
    assert puntuar.componente_R("economia", True, reglas) == 1.0


def test_componente_r_tema_del_reto_pero_medio_no_nacional(reglas):
    assert puntuar.componente_R("turismo", False, reglas) == 0.5


def test_componente_r_tema_otros_es_cero_aunque_el_medio_sea_nacional(reglas):
    assert puntuar.componente_R("otros", True, reglas) == 0.0


# --------------------------------------------------------------------------- componente_I

def test_componente_i_detecta_alcance_nacional(reglas):
    assert puntuar.componente_I("Gobierno nacional anuncia nuevo impuesto", reglas) == 1.0


def test_componente_i_detecta_alcance_sectorial(reglas):
    assert puntuar.componente_I("El turismo del sector crece en la provincia", reglas) == 0.6


def test_componente_i_por_defecto_es_local(reglas):
    assert puntuar.componente_I("Resultado del partido de anoche", reglas) == 0.3


# --------------------------------------------------------------------------- componente_U

def test_componente_u_menos_de_24h(reglas):
    ref = datetime(2026, 1, 10, 8, 0, 0)
    fecha_max = datetime(2026, 1, 10, 7, 0, 0)
    assert puntuar.componente_U(fecha_max, ref, reglas) == 1.0


def test_componente_u_entre_1_y_3_dias(reglas):
    ref = datetime(2026, 1, 10, 8, 0, 0)
    fecha_max = datetime(2026, 1, 8, 8, 0, 0)  # 48h
    assert puntuar.componente_U(fecha_max, ref, reglas) == 0.7


def test_componente_u_entre_3_y_7_dias(reglas):
    ref = datetime(2026, 1, 10, 8, 0, 0)
    fecha_max = datetime(2026, 1, 5, 8, 0, 0)  # 120h
    assert puntuar.componente_U(fecha_max, ref, reglas) == 0.4


def test_componente_u_mas_de_7_dias(reglas):
    ref = datetime(2026, 1, 10, 8, 0, 0)
    fecha_max = datetime(2025, 12, 1, 8, 0, 0)
    assert puntuar.componente_U(fecha_max, ref, reglas) == 0.1


# --------------------------------------------------------------------------- componente_N

def test_componente_n_evento_nuevo(reglas):
    assert puntuar.componente_N(False, reglas) == 1.0


def test_componente_n_repeticion_es_bajo(reglas):
    assert puntuar.componente_N(True, reglas) == 0.2


def test_la_repeticion_nunca_sube_el_puntaje_total(reglas):
    # Mismos R/I/U/E; solo cambia N según es_repeticion. El puntaje con repetición debe
    # ser estrictamente menor (nunca igual ni mayor).
    comunes = dict(R=1.0, I=1.0, U=1.0, E=1.0)
    puntaje_nuevo = puntuar.puntaje_total(**comunes, N=puntuar.componente_N(False, reglas), pesos=reglas["pesos"])
    puntaje_repetido = puntuar.puntaje_total(**comunes, N=puntuar.componente_N(True, reglas), pesos=reglas["pesos"])
    assert puntaje_repetido < puntaje_nuevo


# --------------------------------------------------------------------------- componente_E / estado_evidencia

def test_componente_e_corroboracion_fuente_primaria_y_dato_oficial_capa_en_1(reglas):
    e = puntuar.componente_E(
        corroboracion=2, es_fuente_primaria=True, hay_dato_oficial=True, reglas=reglas
    )
    assert e == 1.0


def test_componente_e_sin_nada_es_cero(reglas):
    e = puntuar.componente_E(
        corroboracion=1, es_fuente_primaria=False, hay_dato_oficial=False, reglas=reglas
    )
    assert e == 0.0


@pytest.mark.parametrize(
    "corroboracion,fuente_fuerte,esperado",
    [
        (1, False, "insuficiente"),
        (2, False, "parcial"),
        (1, True, "parcial"),
        (2, True, "suficiente"),
    ],
)
def test_estado_evidencia_matriz(corroboracion, fuente_fuerte, esperado):
    estado = puntuar.estado_evidencia(
        corroboracion=corroboracion, es_fuente_primaria=fuente_fuerte, hay_dato_oficial=False
    )
    assert estado == esperado


# --------------------------------------------------------------------------- helpers de grupo

def test_tema_mayoritario_toma_la_mayoria_simple():
    assert puntuar.tema_mayoritario(["turismo", "turismo", "otros"]) == "turismo"


def test_tema_mayoritario_desempata_alfabeticamente():
    assert puntuar.tema_mayoritario(["turismo", "economia"]) == "economia"


def test_es_medio_nacional_reconoce_un_dominio_de_la_lista(reglas):
    assert puntuar.es_medio_nacional("tvn-2.com; otromedio.com", reglas) is True
    assert puntuar.es_medio_nacional("otromedio.com", reglas) is False


def test_es_fuente_primaria_por_sufijo_de_dominio_oficial(reglas):
    assert puntuar.es_fuente_primaria("tvn-2.com; mire.gob.pa", reglas) is True
    assert puntuar.es_fuente_primaria("tvn-2.com", reglas) is False


def test_hay_indicador_vinculado_por_tema(reglas):
    disponibles = {"FP.CPI.TOTL.ZG", "SP.POP.TOTL"}
    assert puntuar.hay_indicador_vinculado("economia", disponibles, reglas) is True
    assert puntuar.hay_indicador_vinculado("turismo", disponibles, reglas) is False


def test_hay_evento_sismico_en_ventana():
    fecha_max = datetime(2026, 1, 9, 12, 0, 0)
    dentro = [datetime(2026, 1, 8, 0, 0, 0)]
    fuera = [datetime(2025, 1, 1, 0, 0, 0)]
    assert puntuar.hay_evento_sismico_en_ventana(fecha_max, dentro, ventana_dias=7) is True
    assert puntuar.hay_evento_sismico_en_ventana(fecha_max, fuera, ventana_dias=7) is False


# --------------------------------------------------------------------------- prioridad / orden

def test_prioridad_bajo_medio_alto(reglas):
    assert puntuar.prioridad(0.0, reglas["rangos"]) == "bajo"
    assert puntuar.prioridad(39.9, reglas["rangos"]) == "bajo"
    assert puntuar.prioridad(40.0, reglas["rangos"]) == "medio"
    assert puntuar.prioridad(69.9, reglas["rangos"]) == "medio"
    assert puntuar.prioridad(70.0, reglas["rangos"]) == "alto"
    assert puntuar.prioridad(100.0, reglas["rangos"]) == "alto"


def test_ordenar_filas_desempata_por_mayor_u_y_luego_grupo_id():
    filas = [
        {"grupo_id": "G-B", "puntaje": 50.0, "U": 0.4},
        {"grupo_id": "G-A", "puntaje": 50.0, "U": 0.7},
        {"grupo_id": "G-C", "puntaje": 90.0, "U": 0.1},
    ]
    orden = [f["grupo_id"] for f in puntuar.ordenar_filas(filas)]
    assert orden == ["G-C", "G-A", "G-B"]


# --------------------------------------------------------------------------- pipeline completo (fixtures CSV)

def _crear_motor_db(ruta: Path) -> None:
    grupos = _leer_csv("puntaje_grupos.csv")
    clasif = _leer_csv("puntaje_clasificacion.csv")
    con = duckdb.connect(str(ruta))
    try:
        con.execute("""
            CREATE TABLE grupos (
                grupo_id TEXT, n_noticias INTEGER, n_procedencias INTEGER, procedencias TEXT,
                fecha_min TIMESTAMP, fecha_max TIMESTAMP, titulo_representativo TEXT,
                corroboracion INTEGER, es_repeticion BOOLEAN
            )
        """)
        for g in grupos:
            con.execute(
                "INSERT INTO grupos VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    g["grupo_id"], int(g["n_noticias"]), int(g["n_procedencias"]), g["procedencias"],
                    g["fecha_min"], g["fecha_max"], g["titulo_representativo"],
                    int(g["corroboracion"]), g["es_repeticion"].lower() == "true",
                ],
            )
        con.execute("CREATE TABLE grupo_noticias (grupo_id TEXT, id_noticia TEXT, procedencia TEXT, similitud_al_centroide DOUBLE)")
        con.execute("CREATE TABLE clasificacion (id_noticia TEXT, metodo TEXT, tema TEXT, score DOUBLE, segundo_tema TEXT, margen DOUBLE, modelo TEXT, contraste TEXT)")
        for c in clasif:
            con.execute(
                "INSERT INTO grupo_noticias VALUES (?, ?, ?, ?)",
                [c["grupo_id"], c["id_noticia"], "desconocido", 1.0],
            )
            con.execute(
                "INSERT INTO clasificacion VALUES (?, 'embeddings', ?, 0.5, NULL, 0.1, 'test', NULL)",
                [c["id_noticia"], c["tema"]],
            )
    finally:
        con.close()


def _crear_senales_db(ruta: Path) -> None:
    indicadores = _leer_csv("puntaje_indicadores.csv")
    eventos = _leer_csv("puntaje_eventos.csv")
    con = duckdb.connect(str(ruta))
    try:
        con.execute("CREATE TABLE indicadores (pais_iso3 TEXT, indicador_id TEXT)")
        for i in indicadores:
            con.execute("INSERT INTO indicadores VALUES (?, ?)", [i["pais_iso3"], i["indicador_id"]])
        con.execute("CREATE TABLE eventos (time TIMESTAMP)")
        for e in eventos:
            con.execute("INSERT INTO eventos VALUES (?)", [e["time"]])
    finally:
        con.close()


@pytest.fixture()
def dbs(tmp_path):
    db_path = tmp_path / "senales.duckdb"
    out_path = tmp_path / "motor.duckdb"
    _crear_senales_db(db_path)
    _crear_motor_db(out_path)
    return db_path, out_path


def _filas_puntaje(out_path: Path) -> dict:
    con = duckdb.connect(str(out_path), read_only=True)
    try:
        filas = con.execute(
            "SELECT grupo_id, tema, R, I, U, N, E, puntaje, prioridad, estado_evidencia, version_reglas, motivos "
            "FROM puntaje"
        ).fetchall()
    finally:
        con.close()
    columnas = ["grupo_id", "tema", "R", "I", "U", "N", "E", "puntaje", "prioridad", "estado_evidencia", "version_reglas", "motivos"]
    return {f[0]: dict(zip(columnas, f)) for f in filas}


def test_pipeline_calcula_los_cuatro_grupos_del_fixture(dbs):
    db_path, out_path = dbs
    codigo = puntuar.main(["--db", str(db_path), "--out", str(out_path)])
    assert codigo == 0

    filas = _filas_puntaje(out_path)
    assert set(filas) == {"G-ECO1", "G-TUR1", "G-OTR1", "G-NAT1"}

    eco = filas["G-ECO1"]
    assert eco["tema"] == "economia"
    assert (eco["R"], eco["I"], eco["U"], eco["N"], eco["E"]) == (1.0, 1.0, 1.0, 1.0, 1.0)
    assert eco["puntaje"] == 100.0
    assert eco["prioridad"] == "alto"
    assert eco["estado_evidencia"] == "suficiente"
    assert eco["version_reglas"] == "v0.1"
    assert eco["motivos"]  # explicación no vacía

    tur = filas["G-TUR1"]
    assert tur["tema"] == "turismo"  # mayoría sobre "otros" (2 vs 1)
    assert (tur["R"], tur["I"], tur["U"], tur["N"], tur["E"]) == (0.5, 0.6, 0.4, 0.2, 0.0)
    assert tur["puntaje"] == 41.0
    assert tur["prioridad"] == "medio"
    assert tur["estado_evidencia"] == "insuficiente"

    otr = filas["G-OTR1"]
    assert otr["tema"] == "otros"
    assert otr["R"] == 0.0
    assert otr["puntaje"] == 42.5
    assert otr["prioridad"] == "medio"

    nat = filas["G-NAT1"]
    assert nat["tema"] == "eventos_naturales"
    assert (nat["R"], nat["I"], nat["U"], nat["N"], nat["E"]) == (1.0, 0.3, 1.0, 1.0, 0.4)
    assert nat["puntaje"] == 76.5
    assert nat["prioridad"] == "alto"
    assert nat["estado_evidencia"] == "parcial"  # dato oficial (USGS) sin corroboracion >= 2


def test_pipeline_es_idempotente_sin_forzar(dbs, capsys):
    db_path, out_path = dbs
    assert puntuar.main(["--db", str(db_path), "--out", str(out_path)]) == 0
    filas_1 = _filas_puntaje(out_path)

    capsys.readouterr()
    assert puntuar.main(["--db", str(db_path), "--out", str(out_path)]) == 0
    salida = capsys.readouterr().out
    assert "sin cambios" in salida

    filas_2 = _filas_puntaje(out_path)
    assert filas_1 == filas_2


def test_pipeline_es_reproducible_con_fecha_ref_fija(dbs):
    db_path, out_path = dbs
    assert puntuar.main([
        "--db", str(db_path), "--out", str(out_path), "--fecha-ref", "2026-01-10T08:00:00",
    ]) == 0
    primera = _filas_puntaje(out_path)["G-TUR1"]["puntaje"]

    out_path_2 = out_path.parent / "motor2.duckdb"
    _crear_motor_db(out_path_2)
    assert puntuar.main([
        "--db", str(db_path), "--out", str(out_path_2), "--fecha-ref", "2026-01-10T08:00:00",
    ]) == 0
    segunda = _filas_puntaje(out_path_2)["G-TUR1"]["puntaje"]

    assert primera == segunda == 41.0
