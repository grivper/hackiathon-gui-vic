from __future__ import annotations

from datetime import date, datetime

import duckdb
import pytest

from app.data import ScoreUnavailableError, fetch_inbox_groups, open_inbox_repository


def _create_databases(tmp_path, *, with_scores=True):
    motor_path = tmp_path / "motor.duckdb"
    signals_path = tmp_path / "senales.duckdb"

    motor = duckdb.connect(str(motor_path))
    try:
        motor.execute("""
            CREATE TABLE grupos (
                grupo_id TEXT,
                n_noticias INTEGER,
                n_procedencias INTEGER,
                procedencias TEXT,
                fecha_min TIMESTAMP,
                fecha_max TIMESTAMP,
                titulo_representativo TEXT,
                corroboracion INTEGER,
                es_repeticion BOOLEAN
            )
        """)
        motor.execute("""
            CREATE TABLE grupo_noticias (
                grupo_id TEXT,
                id_noticia TEXT,
                procedencia TEXT,
                similitud_al_centroide DOUBLE
            )
        """)
        motor.execute("""
            CREATE TABLE clasificacion (
                id_noticia TEXT,
                metodo TEXT,
                tema TEXT,
                score DOUBLE,
                segundo_tema TEXT,
                margen DOUBLE,
                modelo TEXT,
                contraste TEXT
            )
        """)
        groups = [
            ("G-NUEVO", 5, 1, "tvn", datetime(2026, 1, 5), datetime(2026, 1, 5, 12), "Titular nuevo", 1, True),
            ("G-FUENTES", 2, 3, "tvn,efe,ap", datetime(2026, 1, 4), datetime(2026, 1, 4, 12), "Titular con fuentes", 3, False),
            ("G-ALFA", 1, 2, "tvn,efe", datetime(2026, 1, 3), datetime(2026, 1, 3, 12), "Titular alfa", 2, False),
            ("G-BETA", 1, 2, "tvn,ap", datetime(2026, 1, 3), datetime(2026, 1, 3, 12), "Titular beta", 2, False),
            ("G-OTROS", 3, 4, "tvn,efe,ap,afp", datetime(2026, 1, 6), datetime(2026, 1, 6, 12), "Titular otros", 4, False),
        ]
        motor.executemany("INSERT INTO grupos VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", groups)
        classifications = []
        for group_id, topics in {
            "G-NUEVO": ["economia", "economia", "otros"],
            "G-FUENTES": ["salud"],
            "G-ALFA": ["educacion"],
            "G-BETA": ["educacion"],
            "G-OTROS": ["otros", "otros", "economia"],
        }.items():
            for index, topic in enumerate(topics):
                news_id = f"{group_id}-{index}"
                motor.execute(
                    "INSERT INTO grupo_noticias VALUES (?, ?, ?, ?)",
                    [group_id, news_id, "medio", 0.9],
                )
                classifications.append((news_id, "embeddings", topic, 0.8, None, None, "modelo", None))
        motor.executemany("INSERT INTO clasificacion VALUES (?, ?, ?, ?, ?, ?, ?, ?)", classifications)
        if with_scores:
            motor.execute("""
                CREATE TABLE puntaje (
                    grupo_id TEXT, tema TEXT, R DOUBLE, I DOUBLE, U DOUBLE, N DOUBLE, E DOUBLE,
                    puntaje DOUBLE, prioridad TEXT, estado_evidencia TEXT,
                    version_reglas TEXT, motivos TEXT
                )
            """)
            scores = [
                ("G-NUEVO", "economia", 1.0, 0.8, 0.7, 0.1, 0.2, 85.0, "alto", "insuficiente", "v0.3", "requiere contraste"),
                ("G-FUENTES", "salud", 1.0, 0.5, 0.2, 1.0, 0.8, 80.0, "alto", "suficiente", "v0.3", "fuentes independientes"),
                ("G-ALFA", "educacion", 0.5, 0.5, 0.8, 1.0, 0.5, 70.0, "medio", "parcial", "v0.3", "alcance sectorial"),
                ("G-BETA", "educacion", 0.5, 0.5, 0.8, 1.0, 0.5, 70.0, "medio", "parcial", "v0.3", "alcance sectorial"),
                ("G-OTROS", "otros", 0.0, 0.0, 1.0, 1.0, 0.0, 95.0, "alto", "suficiente", "v0.3", "excluido"),
            ]
            motor.executemany("INSERT INTO puntaje VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", scores)
    finally:
        motor.close()

    signals = duckdb.connect(str(signals_path))
    signals.close()
    return motor_path, signals_path


def test_fetch_inbox_groups_returns_score_metadata_and_exact_score_order(tmp_path):
    motor_path, signals_path = _create_databases(tmp_path)

    rows = fetch_inbox_groups(motor_path, signals_path)

    assert [row.grupo_id for row in rows] == ["G-NUEVO", "G-FUENTES", "G-ALFA", "G-BETA"]
    assert [row.tema for row in rows] == ["economia", "salud", "educacion", "educacion"]
    assert rows[0].puntaje == 85.0
    assert rows[0].U == 0.7
    assert rows[0].prioridad == "alto"
    assert rows[0].estado_evidencia == "insuficiente"
    assert rows[0].version_reglas == "v0.3"
    assert rows[0].motivos == "requiere contraste"
    assert (rows[0].R, rows[0].I, rows[0].N, rows[0].E) == (1.0, 0.8, 0.1, 0.2)
    assert rows[0].n_noticias == 5
    assert rows[0].n_procedencias == 1
    assert rows[0].corroboracion == 1
    assert rows[0].es_repeticion is True


def test_fetch_inbox_groups_filters_dates_topic_and_limit_inclusively(tmp_path):
    motor_path, signals_path = _create_databases(tmp_path)

    assert [row.grupo_id for row in fetch_inbox_groups(motor_path, signals_path, topic="educacion")] == ["G-ALFA", "G-BETA"]
    assert [row.grupo_id for row in fetch_inbox_groups(motor_path, signals_path, start_date=date(2026, 1, 4))] == ["G-NUEVO", "G-FUENTES"]
    assert [row.grupo_id for row in fetch_inbox_groups(motor_path, signals_path, end_date=date(2026, 1, 4))] == ["G-FUENTES", "G-ALFA", "G-BETA"]
    assert [row.grupo_id for row in fetch_inbox_groups(motor_path, signals_path, limit=2)] == ["G-NUEVO", "G-FUENTES"]


def test_fetch_inbox_groups_requires_the_scoring_table(tmp_path):
    motor_path, signals_path = _create_databases(tmp_path, with_scores=False)

    with pytest.raises(ScoreUnavailableError, match="Ejecute el motor de puntaje"):
        fetch_inbox_groups(motor_path, signals_path)


def test_open_inbox_repository_keeps_motor_database_read_only(tmp_path):
    motor_path, signals_path = _create_databases(tmp_path)

    with (
        open_inbox_repository(motor_path, signals_path) as connection,
        pytest.raises(duckdb.InvalidInputException),
    ):
        connection.execute("INSERT INTO grupos VALUES ('G-NUEVO', 1, 1, '', NOW(), NOW(), '', 1, FALSE)")
