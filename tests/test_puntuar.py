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
    assert reglas["version"] == "v0.3"
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

def test_componente_e_corroboracion_y_fuente_primaria_suman_sin_dato_oficial(reglas):
    # v0.2: el contexto oficial de nivel-tema (Banco Mundial / USGS) ya no suma a E.
    # Con corroboracion=2 (0.2 por la 2da procedencia) + fuente primaria (0.4) da 0.6,
    # no 1.0: el tope real de 1.0 solo se demuestra con reglas de prueba (ver el test
    # siguiente), porque los pesos reales (0.4 + 0.4) nunca llegan a saturarlo.
    e = puntuar.componente_E(corroboracion=2, es_fuente_primaria=True, reglas=reglas)
    assert e == pytest.approx(0.6)


def test_componente_e_se_satura_en_uno_con_pesos_altos():
    reglas_prueba = {
        "evidencia": {
            "peso_por_procedencia_adicional": 0.3,
            "tope_procedencias": 0.9,
            "peso_fuente_primaria": 0.6,
        }
    }
    e = puntuar.componente_E(corroboracion=5, es_fuente_primaria=True, reglas=reglas_prueba)
    assert e == 1.0


def test_componente_e_sin_nada_es_cero(reglas):
    e = puntuar.componente_E(corroboracion=1, es_fuente_primaria=False, reglas=reglas)
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
    estado = puntuar.estado_evidencia(corroboracion=corroboracion, es_fuente_primaria=fuente_fuerte)
    assert estado == esperado


def test_estado_evidencia_ignora_el_contexto_oficial_de_nivel_tema(reglas):
    # Un grupo de eventos_naturales con un sismo USGS en ventana pero sin corroboracion
    # ni fuente primaria sigue siendo insuficiente: el dato oficial es solo contexto.
    assert puntuar.estado_evidencia(corroboracion=1, es_fuente_primaria=False) == "insuficiente"


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


def test_indicadores_vinculados_solo_para_economia(reglas):
    disponibles = {"FP.CPI.TOTL.ZG", "SP.POP.TOTL"}
    assert puntuar.indicadores_vinculados("economia", disponibles, reglas) == ["FP.CPI.TOTL.ZG"]
    # servicios_publicos y logistica_canal ya no tienen mapeo (v0.2): sin sustento
    # tem\u00e1tico claro, no se fuerza la relaci\u00f3n.
    assert puntuar.indicadores_vinculados("turismo", disponibles, reglas) == []
    assert puntuar.indicadores_vinculados("servicios_publicos", disponibles, reglas) == []
    assert puntuar.indicadores_vinculados("logistica_canal", disponibles, reglas) == []


def test_contar_eventos_en_ventana():
    fecha_max = datetime(2026, 1, 9, 12, 0, 0)
    dentro = [datetime(2026, 1, 8, 0, 0, 0)]
    fuera = [datetime(2025, 1, 1, 0, 0, 0)]
    assert puntuar.contar_eventos_en_ventana(fecha_max, dentro, ventana_dias=7) == 1
    assert puntuar.contar_eventos_en_ventana(fecha_max, fuera, ventana_dias=7) == 0
    assert puntuar.contar_eventos_en_ventana(fecha_max, dentro + fuera, ventana_dias=7) == 1


def test_contexto_oficial_de_economia_lista_indicadores(reglas):
    disponibles = {"FP.CPI.TOTL.ZG", "NY.GDP.MKTP.KD.ZG"}
    texto = puntuar.contexto_oficial_de("economia", datetime(2026, 1, 1), disponibles, [], reglas)
    assert texto == "FP.CPI.TOTL.ZG, NY.GDP.MKTP.KD.ZG"


def test_contexto_oficial_de_eventos_naturales_cuenta_sismos_en_ventana(reglas):
    fecha_max = datetime(2026, 1, 9, 12, 0, 0)
    eventos = [datetime(2026, 1, 8, 0, 0, 0)]
    texto = puntuar.contexto_oficial_de("eventos_naturales", fecha_max, set(), eventos, reglas)
    assert "1 evento" in texto
    assert "USGS" in texto


def test_contexto_oficial_de_vacio_sin_eventos_ni_tema_relevante(reglas):
    assert puntuar.contexto_oficial_de("eventos_naturales", datetime(2026, 1, 9), set(), [], reglas) == ""
    assert puntuar.contexto_oficial_de("turismo", datetime(2026, 1, 9), {"FP.CPI.X"}, [], reglas) == ""


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
        con.execute("CREATE TABLE eventos (id TEXT, time TIMESTAMP, magnitude DOUBLE, place TEXT)")
        for i, e in enumerate(eventos):
            con.execute("INSERT INTO eventos VALUES (?, ?, ?, ?)", [f"ev{i}", e["time"], 4.0, "lugar de prueba"])
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
            "SELECT grupo_id, tema, R, I, U, N, E, puntaje, prioridad, estado_evidencia, version_reglas, motivos, "
            "contexto_oficial FROM puntaje"
        ).fetchall()
    finally:
        con.close()
    columnas = ["grupo_id", "tema", "R", "I", "U", "N", "E", "puntaje", "prioridad", "estado_evidencia", "version_reglas", "motivos", "contexto_oficial"]
    return {f[0]: dict(zip(columnas, f)) for f in filas}


def test_pipeline_calcula_los_cuatro_grupos_del_fixture(dbs):
    db_path, out_path = dbs
    codigo = puntuar.main(["--db", str(db_path), "--out", str(out_path)])
    assert codigo == 0

    filas = _filas_puntaje(out_path)
    assert set(filas) == {"G-ECO1", "G-TUR1", "G-OTR1", "G-NAT1"}

    eco = filas["G-ECO1"]
    assert eco["tema"] == "economia"
    # v0.2: E ya no suma el dato oficial (Banco Mundial). corroboracion=2 (0.2) +
    # fuente primaria (0.4) = 0.6, no 1.0.
    assert (eco["R"], eco["I"], eco["U"], eco["N"], eco["E"]) == pytest.approx((1.0, 1.0, 1.0, 1.0, 0.6))
    assert eco["puntaje"] == 96.0
    assert eco["prioridad"] == "alto"
    assert eco["estado_evidencia"] == "suficiente"
    assert eco["version_reglas"] == "v0.3"
    assert eco["motivos"]  # explicación no vacía
    assert eco["contexto_oficial"] == "FP.CPI.TOTL.ZG, NY.GDP.MKTP.KD.ZG"

    tur = filas["G-TUR1"]
    assert tur["tema"] == "turismo"  # mayoría sobre "otros" (2 vs 1)
    assert (tur["R"], tur["I"], tur["U"], tur["N"], tur["E"]) == (0.5, 0.6, 0.4, 0.2, 0.0)
    assert tur["puntaje"] == 41.0
    assert tur["prioridad"] == "medio"
    assert tur["estado_evidencia"] == "insuficiente"
    assert tur["contexto_oficial"] == ""

    otr = filas["G-OTR1"]
    assert otr["tema"] == "otros"
    assert otr["R"] == 0.0
    assert otr["puntaje"] == 42.5
    assert otr["prioridad"] == "medio"
    assert otr["contexto_oficial"] == ""

    nat = filas["G-NAT1"]
    assert nat["tema"] == "eventos_naturales"
    # v0.2: el sismo USGS en ventana ya no suma a E ni cambia estado_evidencia; sigue
    # siendo contexto informativo en `contexto_oficial`.
    assert (nat["R"], nat["I"], nat["U"], nat["N"], nat["E"]) == (1.0, 0.3, 1.0, 1.0, 0.0)
    assert nat["puntaje"] == 72.5
    assert nat["prioridad"] == "alto"
    assert nat["estado_evidencia"] == "insuficiente"  # sin corroboracion>=2 ni fuente primaria
    assert "1 evento" in nat["contexto_oficial"]
    assert "USGS" in nat["contexto_oficial"]


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


# --------------------------------------------------------------------------- vínculo USGS (v0.3)

def _evento(id_="ev1", hora=datetime(2026, 8, 28, 20, 0), magnitud=4.6, lugar="10 km S of San Miguel, Panama"):
    return {"id": id_, "time": hora, "magnitude": magnitud, "place": lugar}


TITULO_OK = "Sismo de magnitud 4.6 se registró cerca de San Miguel"
FECHA_OK = datetime(2026, 8, 29, 7, 0)  # 11 h después del evento


def test_vinculo_usgs_verificado_con_todas_las_condiciones(reglas):
    e = puntuar.evento_usgs_verificado(TITULO_OK, FECHA_OK, [_evento()], reglas)
    assert e is not None and e["id"] == "ev1"


def test_vinculo_usgs_acepta_coma_decimal_y_grados(reglas):
    titulo = "Temblor de 4,5 grados sacude San Miguel"  # 4.5 vs 4.6: dentro de 0.2
    assert puntuar.evento_usgs_verificado(titulo, FECHA_OK, [_evento()], reglas) is not None


@pytest.mark.parametrize("titulo,fecha,evento", [
    ("Gran desfile en San Miguel", FECHA_OK, _evento()),  # sin palabra clave
    ("Sismo se registró cerca de San Miguel", FECHA_OK, _evento()),  # sin magnitud
    ("Sismo de magnitud 5.0 cerca de San Miguel", FECHA_OK, _evento()),  # magnitud lejos
    (TITULO_OK, datetime(2026, 9, 2, 7, 0), _evento()),  # más de 48 h después
    (TITULO_OK, datetime(2026, 8, 28, 7, 0), _evento()),  # 13 h antes del evento
    ("Sismo de magnitud 4.6 en Chiriquí", FECHA_OK, _evento()),  # lugar distinto
    ("Sismo de magnitud 4.6 en Panamá", FECHA_OK, _evento()),  # solo lugar genérico
])
def test_vinculo_usgs_se_rechaza_si_falla_una_condicion(reglas, titulo, fecha, evento):
    assert puntuar.evento_usgs_verificado(titulo, fecha, [evento], reglas) is None


def test_vinculo_usgs_limites_de_ventana(reglas):
    ev = _evento(hora=datetime(2026, 8, 28, 20, 0))
    assert puntuar.evento_usgs_verificado(TITULO_OK, datetime(2026, 8, 28, 8, 0), [ev], reglas) is not None  # -12 h
    assert puntuar.evento_usgs_verificado(TITULO_OK, datetime(2026, 8, 30, 20, 0), [ev], reglas) is not None  # +48 h


def test_vinculo_usgs_ambiguo_no_se_fuerza(reglas):
    eventos = [_evento("ev1"), _evento("ev2", hora=datetime(2026, 8, 28, 22, 0), magnitud=4.7)]
    assert puntuar.evento_usgs_verificado(TITULO_OK, FECHA_OK, eventos, reglas) is None


def test_vinculo_usgs_ignora_acentos(reglas):
    ev = _evento(lugar="5 km N of Pedasí, Panama")
    assert puntuar.evento_usgs_verificado("Sismo de magnitud 4.6 sacude Pedasi", FECHA_OK, [ev], reglas) is not None


def test_calcular_filas_vinculo_usgs_cuenta_como_fuente_primaria(reglas):
    g = {
        "grupo_id": "G-SIS", "tema": "eventos_naturales", "corroboracion": 1, "es_repeticion": False,
        "procedencias": "tvn-pa.com", "fecha_max": FECHA_OK, "titulo_representativo": TITULO_OK,
    }
    sin = puntuar.calcular_filas([g], reglas, FECHA_OK, set(), [])[0]
    con = puntuar.calcular_filas([g], reglas, FECHA_OK, set(), [_evento()])[0]
    assert sin["evento_usgs_id"] is None and sin["estado_evidencia"] == "insuficiente"
    assert con["evento_usgs_id"] == "ev1"
    assert con["estado_evidencia"] == "parcial"
    assert con["E"] == pytest.approx(sin["E"] + reglas["evidencia"]["peso_fuente_primaria"])
    assert "ev1" in con["motivos"]
